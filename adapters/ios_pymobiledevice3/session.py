# SPDX-License-Identifier: AGPL-3.0-only
"""Single-event-loop lifecycle. Clear transmission never certifies restoration."""
from __future__ import annotations
import asyncio
import time
import uuid
from typing import Protocol
from .protocol import Fault, Request, point

class Port(Protocol):
    async def connect(self) -> None: ...
    async def set(self, latitude: float, longitude: float) -> None: ...
    async def clear(self) -> None: ...
    async def close(self) -> None: ...

class RecoveryRecord(Protocol):
    def pending(self) -> bool: ...
    def write(self, pending: bool) -> None: ...

class Session:
    def __init__(self, port: Port, journal: RecoveryRecord, *, clock=time.monotonic,
                 timeout: float = 10, lease_seconds: float = 60, max_duration: float = 3600):
        if not 0 < timeout <= 30 or not 0 < lease_seconds <= 300 or not 0 < max_duration <= 3600:
            raise ValueError("invalid limits")
        self.port, self.journal, self.clock = port, journal, clock
        self.timeout, self.lease_seconds, self.max_duration = timeout, lease_seconds, max_duration
        self.state = "RECOVERY_REQUIRED" if journal.pending() else "IDLE"
        self.connected = False
        self.session_id: str | None = None
        self.last_id = 0
        self.batches = 0
        self.target: tuple[float, float] | None = None
        self.lease_deadline = self.hard_deadline = self.next_tick = 0.0
        self.error: str | None = None
        self.recovery_evidence = "none"
        self.exit_requested = False

    def status(self) -> dict:
        return {"state": self.state, "session": self.session_id, "connected": self.connected,
                "submitted_batches": self.batches, "cleanup": "sent_unconfirmed" if self.state == "CLEAR_SENT" else "unknown",
                "system_observation": "unavailable", "wechat": "unverified",
                "recovery_evidence": self.recovery_evidence, "error": self.error}

    async def bounded(self, awaitable):
        return await asyncio.wait_for(awaitable, timeout=self.timeout)

    async def close_transport(self) -> None:
        try:
            await self.bounded(self.port.close())
        except Exception:
            self.error = "transport_close_failed"
        self.connected = False

    async def stop(self) -> None:
        self.target = None
        if self.state == "CLEAR_SENT":
            return
        if not self.journal.pending():
            self.state = "READY" if self.connected else "IDLE"
            return
        if not self.connected:
            self.state = "UNKNOWN"
            self.error = "reconnect_to_clear"
            return
        try:
            await self.bounded(self.port.clear())
            # Retain recovery record until independent observation is explicitly confirmed.
            self.state = "CLEAR_SENT"
            self.error = None
        except Exception:
            self.state = "UNKNOWN"
            self.error = "clear_failed"
            await self.close_transport()

    async def connect(self) -> None:
        try:
            await self.bounded(self.port.connect())
        except Exception as exc:
            self.state = "RECOVERY_REQUIRED" if self.journal.pending() else "IDLE"
            self.error = exc.code if isinstance(exc, Fault) else "connect_failed"
            await self.close_transport()
            raise Fault(self.error) from None
        self.connected = True
        self.state = "RECOVERY_REQUIRED" if self.journal.pending() else "READY"

    async def submit(self) -> None:
        if self.target is None or not self.connected:
            raise Fault("not_running")
        try:
            await self.bounded(self.port.set(*self.target))
            self.batches += 1
        except Exception:
            # A timeout may occur after device mutation. Never retry injection automatically.
            self.error = "submission_failed"
            self.state = "UNKNOWN"
            self.target = None
            await self.stop()
            if self.error is None:
                self.error = "submission_failed"
            raise Fault("submission_failed") from None

    async def command(self, request: Request) -> dict:
        if request.id <= self.last_id:
            raise Fault("replayed_request")
        self.last_id = request.id
        op = request.op
        if op not in {"status", "prepare", "quit"}:
            if self.session_id is None or request.session != self.session_id:
                raise Fault("stale_session")
        elif request.session is not None and request.session != self.session_id:
            raise Fault("stale_session")
        if op == "prepare":
            if self.connected or self.session_id is not None:
                raise Fault("already_prepared")
            await self.connect()
            self.session_id = uuid.uuid4().hex
        elif op == "set":
            if self.state not in {"READY", "RUNNING"} or not self.connected:
                raise Fault("cleanup_or_prepare_required")
            location = point(request.params)
            # Durable intent precedes the first write and survives process death.
            if not self.journal.pending():
                try:
                    self.journal.write(True)
                except Exception:
                    self.state = "RECOVERY_REQUIRED"
                    raise Fault("recovery_record_write_failed") from None
            was_running = self.state == "RUNNING"
            self.target = location
            self.state = "RUNNING"
            self.recovery_evidence = "none"
            if not was_running:
                self.hard_deadline = self.clock() + self.max_duration
            await self.submit()
            self.next_tick = self.clock() + 1
        elif op == "hold":
            if self.state != "RUNNING":
                raise Fault("not_running")
            self.state = "HOLDING"
        elif op == "resume":
            if self.state != "HOLDING":
                raise Fault("not_holding")
            self.state = "RUNNING"
        elif op == "stop":
            await self.stop()
        elif op == "recover":
            if self.state not in {"RECOVERY_REQUIRED", "UNKNOWN", "CLEAR_SENT"}:
                raise Fault("recovery_not_needed")
            await self.close_transport()
            await self.connect()
            await self.stop()
        elif op == "verify_recovery":
            if self.state != "CLEAR_SENT":
                raise Fault("clear_required_first")
            try:
                self.journal.write(False)
            except Exception:
                raise Fault("recovery_record_write_failed") from None
            self.state = "READY" if self.connected else "IDLE"
            self.error = None
            self.recovery_evidence = "user_confirmation_only"
        elif op == "quit":
            self.exit_requested = True
            await self.shutdown()
        if request.session == self.session_id and self.session_id is not None:
            self.lease_deadline = self.clock() + self.lease_seconds
        return self.status()

    async def tick(self) -> bool:
        if self.state not in {"RUNNING", "HOLDING"}:
            return False
        now = self.clock()
        if now >= self.lease_deadline or now >= self.hard_deadline:
            reason = "client_lease_expired" if now >= self.lease_deadline else "session_limit_reached"
            await self.stop()
            self.error = reason
            return True
        if now >= self.next_tick:
            try:
                await self.submit()
            except Fault:
                pass
            self.next_tick = self.clock() + 1
            return True
        return False

    async def shutdown(self) -> None:
        try:
            await self.stop()
        except Exception:
            self.state, self.error = "UNKNOWN", "cleanup_unknown"
        finally:
            await self.close_transport()

# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic transports only. None of these tests certifies iPhone behavior."""
import asyncio
import contextlib
import io
import json
from pathlib import Path
import queue
import tempfile
import threading
import unittest
from unittest.mock import patch

from adapters.ios_pymobiledevice3.backend import endpoint, read_identity, Pmd3Backend
from adapters.ios_pymobiledevice3.protocol import decode, Fault, MAX_LINE
from adapters.ios_pymobiledevice3.session import Session
from adapters.ios_pymobiledevice3.storage import Journal
from adapters.ios_pymobiledevice3.__main__ import read_lines, serve


def request(i, op, session=None, **params):
    return decode(json.dumps(dict(v=1, id=i, session=session, op=op, params=params)).encode())

class MemoryJournal:
    def __init__(self): self.dirty = False; self.fail = False
    def pending(self): return self.dirty
    def write(self, pending):
        if self.fail: raise OSError("PRIVATE-JOURNAL-PATH")
        self.dirty = pending

class FakePort:
    def __init__(self, journal):
        self.journal = journal; self.events = []; self.fail_set = self.fail_clear = self.fail_connect = False
        self.hang = False; self.set_inflight = False
    async def connect(self):
        self.events.append("connect")
        if self.fail_connect: raise OSError("PRIVATE-DEVICE-ID")
    async def set(self, lat, lon):
        assert self.journal.pending(), "write intent before mutation"
        self.events.append("set")
        self.set_inflight = True
        try:
            if self.hang: await asyncio.sleep(100)
            if self.fail_set: raise OSError("PRIVATE-COORDINATES")
        finally: self.set_inflight = False
    async def clear(self):
        assert not self.set_inflight, "serialize cancellation and cleanup"
        self.events.append("clear")
        if self.fail_clear: raise OSError("PRIVATE-DEVICE-ID")
    async def close(self): self.events.append("close")

class ProtocolTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(request(1, "status").op, "status")
    def test_duplicate_key(self):
        with self.assertRaises(Fault): decode(b'{"v":1,"v":1}')
    def test_nonfinite_and_overflow(self):
        for value in ("NaN", "Infinity", "1e999"):
            raw = ('{"v":1,"id":1,"session":null,"op":"set","params":{"latitude":'+value+',"longitude":0}}').encode()
            with self.subTest(value=value), self.assertRaises(Fault): decode(raw)
    def test_bool_is_not_number(self):
        with self.assertRaises(Fault): request(1, "set", latitude=True, longitude=0)
    def test_bounds(self):
        request(1, "set", latitude=-90, longitude=180)
        for lat, lon in ((91,0), (0,-181)):
            with self.assertRaises(Fault): request(1, "set", latitude=lat, longitude=lon)
    def test_unknown_op(self):
        with self.assertRaises(Fault): request(1, "shell")
    def test_extra_fields(self):
        with self.assertRaises(Fault): request(1, "status", private="secret")
    def test_ids(self):
        for i in (True, 0, -1, 2**53, 1.5):
            with self.assertRaises(Fault): request(i, "status")
    def test_invalid_session(self):
        with self.assertRaises(Fault): request(1, "status", "not-a-token")
    def test_consent(self):
        for val in (False, 1, "true"):
            with self.assertRaises(Fault): request(1, "prepare", consent=val)
    def test_verification_requires_explicit_bool(self):
        with self.assertRaises(Fault): request(1, "verify_recovery", independently_checked=1)
    def test_line_limit(self):
        with self.assertRaises(Fault): decode(b" "*(MAX_LINE+1))
    def test_encoding_and_shape(self):
        for raw in (b"\xff", b"[]", b"null", b"{}"):
            with self.assertRaises(Fault): decode(raw)
    def test_reader_stops_at_oversized_line(self):
        q = queue.Queue(); read_lines(io.BytesIO(b"x"*(MAX_LINE+1)+b"\n{}\n"), q)
        self.assertIsInstance(q.get(), Fault); self.assertTrue(q.empty())
    def test_reader_requires_newline(self):
        q = queue.Queue(); read_lines(io.BytesIO(b"{}"), q)
        self.assertEqual(q.get().code, "incomplete_line")
    def test_reader_eof(self):
        q = queue.Queue(); read_lines(io.BytesIO(b"{}\n"), q)
        self.assertEqual(q.get(), b"{}\n"); self.assertIsNone(q.get())

class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    def rig(self, dirty=False):
        self.j = MemoryJournal(); self.j.dirty = dirty; self.p = FakePort(self.j); self.time = 100.
        self.s = Session(self.p, self.j, clock=lambda:self.time, timeout=.02, lease_seconds=60)
        self.i = 0
    async def send(self, op, **params):
        self.i += 1
        return await self.s.command(request(self.i, op, self.s.session_id, **params))
    async def start(self):
        await self.send("prepare", consent=True)
        await self.send("set", latitude=1, longitude=2)
    async def test_prepared_is_not_position_pass(self):
        self.rig(); out = await self.send("prepare", consent=True)
        self.assertEqual(out["state"], "READY"); self.assertEqual(out["wechat"], "unverified")
        self.assertNotIn("set", self.p.events)
    async def test_one_connection_multiple_sets(self):
        self.rig(); await self.start(); await self.send("set", latitude=2, longitude=3)
        self.assertEqual(self.p.events, ["connect", "set", "set"])
        self.assertTrue(self.j.dirty)
    async def test_set_requires_prepare(self):
        self.rig()
        with self.assertRaises(Fault): await self.send("set", latitude=1, longitude=2)
        self.assertEqual(self.p.events, [])
    async def test_old_session_rejected(self):
        self.rig(); await self.start()
        with self.assertRaises(Fault): await self.s.command(request(3, "stop", "f"*32))
        self.assertNotIn("clear", self.p.events)
    async def test_replay_rejected(self):
        self.rig(); await self.start()
        with self.assertRaises(Fault): await self.s.command(request(2, "stop", self.s.session_id))
    async def test_clear_only_sent_and_record_retained(self):
        self.rig(); await self.start(); out = await self.send("stop")
        self.assertEqual(out["state"], "CLEAR_SENT"); self.assertEqual(out["cleanup"], "sent_unconfirmed")
        self.assertTrue(self.j.dirty); self.assertEqual(out["recovery_evidence"], "none")
    async def test_no_new_set_before_manual_observation(self):
        self.rig(); await self.start(); await self.send("stop")
        with self.assertRaises(Fault): await self.send("set", latitude=1, longitude=2)
    async def test_manual_confirmation_not_hardware_proof(self):
        self.rig(); await self.start(); await self.send("stop")
        out=await self.send("verify_recovery", independently_checked=True)
        self.assertFalse(self.j.dirty); self.assertEqual(out["recovery_evidence"], "user_confirmation_only")
        self.assertEqual(out["system_observation"], "unavailable")
    async def test_cannot_confirm_before_clear(self):
        self.rig(); await self.start()
        with self.assertRaises(Fault): await self.send("verify_recovery", independently_checked=True)
        self.assertTrue(self.j.dirty)
    async def test_pending_restart_blocks_start(self):
        self.rig(True); await self.send("prepare", consent=True)
        with self.assertRaises(Fault): await self.send("set", latitude=1, longitude=2)
        await self.send("recover"); self.assertEqual(self.s.state, "CLEAR_SENT")
        self.assertNotIn("set", self.p.events)
    async def test_journal_failure_prevents_mutation(self):
        self.rig(); await self.send("prepare", consent=True); self.j.fail=True
        with self.assertRaises(Fault): await self.send("set", latitude=1, longitude=2)
        self.assertNotIn("set", self.p.events)
    async def test_verify_journal_failure_stays_pending(self):
        self.rig(); await self.start(); await self.send("stop"); self.j.fail=True
        with self.assertRaises(Fault): await self.send("verify_recovery", independently_checked=True)
        self.assertEqual(self.s.state, "CLEAR_SENT"); self.assertTrue(self.j.dirty)
    async def test_set_failure_attempts_clear(self):
        self.rig(); await self.send("prepare", consent=True); self.p.fail_set=True
        with self.assertRaises(Fault): await self.send("set", latitude=1, longitude=2)
        self.assertIn("clear", self.p.events); self.assertTrue(self.j.dirty)
        self.assertEqual(self.s.batches, 0)
    async def test_timeout_serialized_before_clear(self):
        self.rig(); await self.send("prepare", consent=True); self.p.hang=True
        with self.assertRaises(Fault): await self.send("set", latitude=1, longitude=2)
        self.assertEqual(self.p.events[-2:], ["set", "clear"]); self.assertTrue(self.j.dirty)
    async def test_clear_failure_is_unknown(self):
        self.rig(); await self.start(); self.p.fail_clear=True; await self.send("stop")
        self.assertEqual(self.s.state, "UNKNOWN"); self.assertFalse(self.s.connected)
        self.assertTrue(self.j.dirty)
    async def test_recover_after_disconnect_never_resumes(self):
        self.rig(); await self.start(); self.p.fail_clear=True; await self.send("stop")
        self.p.fail_clear=False; await self.send("recover")
        self.assertEqual(self.s.state, "CLEAR_SENT"); self.assertEqual(self.p.events.count("set"), 1)
    async def test_hold_keeps_point(self):
        self.rig(); await self.start(); await self.send("hold"); self.time+=2; await self.s.tick()
        self.assertEqual(self.s.state, "HOLDING"); self.assertEqual(self.s.batches, 2)
        await self.send("resume"); self.assertEqual(self.s.state, "RUNNING")
    async def test_lease_timeout_stops(self):
        self.rig(); await self.start(); self.time+=61; await self.s.tick()
        self.assertEqual(self.s.state, "CLEAR_SENT"); self.assertEqual(self.s.error, "client_lease_expired")
    async def test_status_renews_only_bound_session(self):
        self.rig(); await self.start(); deadline=self.s.lease_deadline; self.time+=30
        await self.s.command(request(3, "status"))
        self.assertEqual(self.s.lease_deadline, deadline)
        await self.s.command(request(4, "status", self.s.session_id))
        self.assertGreater(self.s.lease_deadline, deadline)
    async def test_hard_limit_cannot_be_extended_by_sets(self):
        self.rig(); await self.start(); self.time+=3590; await self.send("set", latitude=3, longitude=4)
        self.time+=11; await self.s.tick()
        self.assertEqual(self.s.error,"session_limit_reached")
    async def test_idle_shutdown_does_not_clear_unrelated_location(self):
        self.rig(); await self.send("prepare", consent=True); await self.s.shutdown()
        self.assertNotIn("clear", self.p.events)
    async def test_eof_cleans_and_keeps_unconfirmed_record(self):
        self.rig(); await self.start(); q=queue.Queue(); q.put(None)
        out=io.StringIO()
        with contextlib.redirect_stdout(out): await serve(self.s, q, threading.Event())
        self.assertIn("clear", self.p.events); self.assertIn("close", self.p.events); self.assertTrue(self.j.dirty)
        self.assertNotIn("latitude", out.getvalue())
    async def test_oversize_while_running_cleans(self):
        self.rig(); await self.start(); q=queue.Queue(); q.put(Fault("line_too_large"))
        with contextlib.redirect_stdout(io.StringIO()): code=await serve(self.s,q,threading.Event())
        self.assertEqual(code,2); self.assertIn("clear", self.p.events)
    async def test_connect_exception_is_redacted(self):
        self.rig(); self.p.fail_connect=True
        with self.assertRaises(Fault) as c: await self.send("prepare", consent=True)
        self.assertNotIn("PRIVATE", str(c.exception)); self.assertIn("close", self.p.events)
    async def test_quit_runs_clear_once(self):
        self.rig(); await self.start(); await self.send("quit"); await self.s.shutdown()
        self.assertEqual(self.p.events.count("clear"),1); self.assertTrue(self.s.exit_requested)

class LocalStorageTests(unittest.TestCase):
    def test_roundtrip_no_identity_or_coordinate_storage(self):
        with tempfile.TemporaryDirectory() as d:
            j=Journal(Path(d)/"private", "TEST-DEVICE-0000"); j.acquire()
            try:
                self.assertFalse(j.pending()); j.write(True); self.assertTrue(j.pending())
                self.assertNotIn("TEST-DEVICE",j.path.name); self.assertNotIn("latitude",j.path.read_text())
                j.write(False); self.assertFalse(j.pending())
            finally: j.release()
    def test_lock_excludes_second_helper(self):
        with tempfile.TemporaryDirectory() as d:
            a=Journal(Path(d)/"private","TEST-DEVICE-0000"); b=Journal(Path(d)/"private","TEST-DEVICE-0000")
            a.acquire()
            try:
                with self.assertRaises(Fault): b.acquire()
            finally: a.release()
            b.acquire(); b.release()
    def test_corrupt_record_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            j=Journal(Path(d)/"private","TEST-DEVICE-0000")
            for raw in ("{}", "{bad", '{"v":true,"needs_verification":false}', "x"*513):
                j.path.write_text(raw)
                with self.assertRaises(Fault): j.pending()
    def test_write_requires_lock(self):
        with tempfile.TemporaryDirectory() as d:
            j=Journal(Path(d)/"private","TEST-DEVICE-0000")
            with self.assertRaises(Fault): j.write(True)
    def test_identity_file_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"identity"; p.write_text("TEST-DEVICE-0000\n")
            self.assertEqual(read_identity(p),"TEST-DEVICE-0000")
            p.write_text("x"*257)
            with self.assertRaises(Fault): read_identity(p)
    def test_endpoint_validation(self):
        self.assertEqual(endpoint("127.0.0.1", 58783),("127.0.0.1",58783))
        endpoint("fd00::1",58783)
        for host,port in (("example.com",1),("8.8.8.8",1),("0.0.0.0",1),("127.0.0.1",0),("127.0.0.1",True)):
            with self.assertRaises(Fault): endpoint(host,port)
    def test_version_gate(self):
        from adapters.ios_pymobiledevice3.backend import dependency_check
        with patch('adapters.ios_pymobiledevice3.backend.version',return_value="0.0"):
            with self.assertRaises(Fault): dependency_check()

if __name__ == "__main__": unittest.main()

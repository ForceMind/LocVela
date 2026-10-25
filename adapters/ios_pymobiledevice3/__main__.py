# SPDX-License-Identifier: AGPL-3.0-only
"""Local JSONL development helper; no listening port and no simulation fallback."""
from __future__ import annotations
import argparse
import asyncio
import json
import logging
from pathlib import Path
import queue
import signal
import sys
import threading
from . import VERSION, PMD3_VERSION
from .backend import Pmd3Backend, endpoint, read_identity
from .protocol import Fault, MAX_LINE, decode
from .session import Session
from .storage import Journal


def read_lines(stream, output: queue.Queue) -> None:
    """Bounded daemon reader; truncated/oversized lines end the stream, not resume mid-command."""
    try:
        while True:
            line = stream.readline(MAX_LINE + 1)
            if not line:
                output.put(None)
                return
            if len(line) > MAX_LINE or not line.endswith(b"\n"):
                output.put(Fault("line_too_large" if len(line) > MAX_LINE else "incomplete_line"))
                return
            output.put(line)
    except Exception:
        output.put(Fault("input_failed"))


def emit(message: dict) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=True, allow_nan=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


async def serve(session: Session, incoming: queue.Queue, interrupted: threading.Event) -> int:
    emit({"v": 1, "event": "ready", "helper_version": VERSION, "backend_version": PMD3_VERSION,
          "device_connected": False, "hardware_validation": "not_performed", **session.status()})
    exit_code = 0
    try:
        while not interrupted.is_set() and not session.exit_requested:
            try:
                raw = incoming.get_nowait()
            except queue.Empty:
                raw = b""
            if raw is None:
                break
            if isinstance(raw, Fault):
                emit({"v": 1, "id": None, "ok": False, "error": raw.code})
                exit_code = 2
                break
            if raw:
                request = None
                try:
                    request = decode(raw)
                    result = await session.command(request)
                    emit({"v": 1, "id": request.id, "ok": True, **result})
                except Fault as error:
                    emit({"v": 1, "id": request.id if request else None, "ok": False,
                          "error": error.code, "status": session.status()})
                except Exception:
                    # Fail closed for unexpected journal/transport errors; never leak exception repr.
                    await session.shutdown()
                    emit({"v": 1, "id": request.id if request else None, "ok": False,
                          "error": "internal_failure", "status": session.status()})
                    exit_code = 3
                    break
            if await session.tick():
                emit({"v": 1, "event": "state", **session.status()})
            await asyncio.sleep(0.05)
    except (BrokenPipeError, OSError):
        exit_code = 3
    finally:
        await session.shutdown()
        try:
            emit({"v": 1, "event": "closed", **session.status()})
        except (BrokenPipeError, OSError):
            pass
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rsd-host", help="Explicit local/tunnel IP; no hostname lookup")
    parser.add_argument("--rsd-port", type=int)
    parser.add_argument("--device-id-file", required=True, type=Path, help="Local text containing the intended UDID; never printed")
    parser.add_argument("--expected-ios", default="18.4.1")
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".locvela" / "ios-state")
    parser.add_argument("--lease-seconds", type=int, choices=range(5, 301), metavar="5..300", default=60)
    args = parser.parse_args()
    journal = None
    try:
        identity = read_identity(args.device_id_file)
        if (args.rsd_host is None) != (args.rsd_port is None):
            raise Fault("both_rsd_options_required")
        address = None if args.rsd_host is None else endpoint(args.rsd_host, args.rsd_port)
        port = Pmd3Backend(address, identity, args.expected_ios)
        journal = Journal(args.state_dir, identity)
        journal.acquire()
        session = Session(port, journal, lease_seconds=args.lease_seconds)
        incoming: queue.Queue = queue.Queue(maxsize=16)
        interrupted = threading.Event()
        for signum in (signal.SIGINT, signal.SIGTERM):
            signal.signal(signum, lambda *_: interrupted.set())
        # Upstream exception logs can contain device identifiers. The helper emits public codes only.
        logging.disable(logging.CRITICAL)
        reader = threading.Thread(target=read_lines, args=(sys.stdin.buffer, incoming), daemon=True)
        reader.start()
        return asyncio.run(serve(session, incoming, interrupted))
    except Fault as error:
        print("LocVela iOS: " + error.code, file=sys.stderr)
        return 2
    except Exception:
        print("LocVela iOS: startup_failed", file=sys.stderr)
        return 3
    finally:
        if journal is not None:
            journal.release()


if __name__ == "__main__":
    raise SystemExit(main())

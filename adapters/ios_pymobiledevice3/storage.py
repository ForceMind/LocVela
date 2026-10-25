# SPDX-License-Identifier: AGPL-3.0-only
"""Local single-writer lock and durable recovery intent. Never stores coordinates."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from .protocol import Fault, _object

class Journal:
    def __init__(self, directory: Path, device_id: str):
        if directory.is_symlink():
            raise Fault("unsafe_state_directory")
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name != "nt" and stat.S_IMODE(directory.stat().st_mode) & 0o077:
            raise Fault("unsafe_state_directory")
        digest = hashlib.sha256(device_id.encode("ascii")).hexdigest()
        self.path = directory / (digest + ".json")
        self.lock_path = directory / (digest + ".lock")
        self._lock = None

    def acquire(self) -> None:
        if self._lock is not None:
            raise Fault("already_locked")
        if self.lock_path.is_symlink():
            raise Fault("unsafe_state_directory")
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        stream = os.fdopen(fd, "r+b", buffering=0)
        try:
            if os.fstat(fd).st_size == 0:
                stream.write(b"0")
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.close()
            raise Fault("another_helper_running") from None
        self._lock = stream

    def release(self) -> None:
        if self._lock is not None:
            self._lock.close()
            self._lock = None

    def pending(self) -> bool:
        if self.path.is_symlink():
            raise Fault("invalid_recovery_record")
        try:
            with self.path.open("rb") as stream:
                raw = stream.read(513)
        except FileNotFoundError:
            return False
        if len(raw) > 512:
            raise Fault("invalid_recovery_record")
        try:
            data = json.loads(raw, object_pairs_hook=_object)
            if (type(data) is not dict or set(data) != {"v", "needs_verification"}
                    or type(data["v"]) is not int or data["v"] != 1
                    or type(data["needs_verification"]) is not bool):
                raise ValueError()
        except (ValueError, UnicodeError):
            raise Fault("invalid_recovery_record") from None
        return data["needs_verification"]

    def write(self, pending: bool) -> None:
        if type(pending) is not bool or self._lock is None:
            raise Fault("journal_not_locked")
        fd, name = tempfile.mkstemp(dir=self.path.parent, prefix=".locvela-", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(json.dumps({"v": 1, "needs_verification": pending}).encode("ascii"))
                out.flush()
                os.fsync(out.fileno())
            os.replace(name, self.path)
            if os.name != "nt":
                directory_fd = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        finally:
            Path(name).unlink(missing_ok=True)

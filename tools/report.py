"""Strict, dependency-free validation of redacted compatibility evidence (v1)."""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

MAX_BYTES = 64 * 1024
FEATURES = frozenset({"wechat.send_location", "wechat.realtime_location", "wechat.moments",
    "wechat.miniapp_single", "wechat.miniapp_watch", "wechat.choose_location",
    "wechat.web_geolocation", "wechat.nearby"})
RESULTS = frozenset({"unverified", "passed", "partial", "failed", "blocked", "not_applicable"})

class ReportError(ValueError):
    pass

def _keys(obj: Any, expected: set[str], name: str) -> None:
    if not isinstance(obj, dict) or set(obj) != expected:
        raise ReportError(f"{name}: missing or unexpected fields")

def _text(value: Any, name: str, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise ReportError(f"{name}: expected nonempty text (max 256 characters)")

def validate(report: Any, *, expected_wechat_version: str | None = None) -> None:
    _keys(report, {"schema_version", "device", "software", "feature", "result", "evidence",
        "cleanup", "tested_at", "notes"}, "report")
    if type(report["schema_version"]) is not int or report["schema_version"] != 1:
        raise ReportError("unsupported schema version")
    device = report["device"]
    _keys(device, {"alias", "model", "os", "os_build"}, "device")
    for key in ("alias", "model", "os"):
        _text(device[key], key)
    if device["os"] not in {"Android", "iOS"}:
        raise ReportError("unknown operating system")
    _text(device["os_build"], "os_build", nullable=True)
    software = report["software"]
    _keys(software, {"locvela_version", "backend_version", "wechat_version", "install_channel"}, "software")
    for key, value in software.items():
        _text(value, key, nullable=True)
    if not isinstance(report["feature"], str) or report["feature"] not in FEATURES:
        raise ReportError("unknown feature")
    result = report["result"]
    if not isinstance(result, str) or result not in RESULTS:
        raise ReportError("unknown result")
    evidence = report["evidence"]
    _keys(evidence, {"submitted", "system_observed", "target_observed", "reference"}, "evidence")
    flags = [evidence[key] for key in ("submitted", "system_observed", "target_observed")]
    if any(type(flag) is not bool for flag in flags):
        raise ReportError("evidence flags must be booleans")
    if (flags[1] and not flags[0]) or (flags[2] and not flags[1]):
        raise ReportError("evidence levels cannot be skipped")
    ref = evidence["reference"]
    if ref is not None and (not isinstance(ref, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", ref)):
        raise ReportError("reference must be an opaque local evidence ID, not a URL or path")
    cleanup = report["cleanup"]
    if not isinstance(cleanup, str) or cleanup not in {"not_run", "confirmed", "unknown", "failed"}:
        raise ReportError("unknown cleanup state")
    _text(report["notes"], "notes")
    tested_at = report["tested_at"]
    if tested_at is not None:
        _text(tested_at, "tested_at")
        try:
            stamp = datetime.fromisoformat(tested_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ReportError("invalid tested_at") from exc
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ReportError("tested_at must include a timezone")
    if result == "unverified":
        if any(flags) or ref is not None or tested_at is not None or cleanup != "not_run":
            raise ReportError("unverified record cannot contain claimed test evidence")
    else:
        if tested_at is None:
            raise ReportError("attempted or classified records require tested_at")
    if result in {"passed", "partial", "failed"}:
        if device["os_build"] is None or any(value is None for value in software.values()) or ref is None:
            raise ReportError("tested results require complete version scope and evidence reference")
    if result == "passed" and (not all(flags) or cleanup != "confirmed"):
        raise ReportError("pass requires backend, system, target and cleanup evidence")
    if expected_wechat_version is not None and result != "unverified":
        if software["wechat_version"] != expected_wechat_version:
            raise ReportError("stale result: WeChat version differs")

def _reject_constant(value: str) -> None:
    raise ReportError(f"non-finite JSON constant: {value}")

def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReportError("duplicate JSON key")
        result[key] = value
    return result

def load(path: Path) -> Any:
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ReportError("report exceeds 64 KiB")
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=_reject_constant, object_pairs_hook=_unique)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ReportError("invalid JSON document") from exc

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--wechat-version", default=None)
    args = parser.parse_args()
    failed = False
    for path in args.paths:
        try:
            report = load(path)
            validate(report, expected_wechat_version=args.wechat_version)
            print(f"VALID {path.name}: {report['result']} (format/evidence checks only)")
        except (OSError, ReportError) as exc:
            print(f"INVALID {path.name}: {exc}")
            failed = True
    return int(failed)

if __name__ == "__main__":
    raise SystemExit(main())

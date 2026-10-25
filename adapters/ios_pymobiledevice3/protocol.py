# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded stdio protocol. User text, coordinates and device IDs are never echoed."""
from __future__ import annotations
from dataclasses import dataclass
import json
import math
import re
from typing import Any

MAX_LINE = 64 * 1024
MAX_ID = 2**53 - 1
OPS = {"status", "prepare", "set", "hold", "resume", "stop", "recover", "verify_recovery", "quit"}

class Fault(Exception):
    """Only constant, public diagnostic codes may cross the stdio boundary."""
    def __init__(self, code: str):
        if not re.fullmatch(r"[a-z_]{1,60}", code):
            raise ValueError("invalid diagnostic code")
        self.code = code
        super().__init__(code)

@dataclass(frozen=True)
class Request:
    id: int
    session: str | None
    op: str
    params: dict[str, Any]

def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Fault("duplicate_key")
        result[key] = value
    return result

def _constant(_: str) -> None:
    raise Fault("nonfinite_number")

def fields(obj: Any, names: set[str]) -> None:
    if type(obj) is not dict or set(obj) != names:
        raise Fault("invalid_fields")

def point(params: dict[str, Any]) -> tuple[float, float]:
    fields(params, {"latitude", "longitude"})
    out = []
    for name, bound in (("latitude", 90), ("longitude", 180)):
        value = params[name]
        if type(value) not in (float, int):
            raise Fault("invalid_coordinate")
        try:
            number = float(value)
        except (ValueError, OverflowError):
            raise Fault("invalid_coordinate") from None
        if not math.isfinite(number) or not -bound <= number <= bound:
            raise Fault("invalid_coordinate")
        out.append(number)
    return out[0], out[1]

def decode(raw: bytes) -> Request:
    if len(raw) > MAX_LINE:
        raise Fault("line_too_large")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_object, parse_constant=_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise Fault("invalid_json") from None
    fields(data, {"v", "id", "session", "op", "params"})
    if type(data["v"]) is not int or data["v"] != 1:
        raise Fault("protocol_version")
    if type(data["id"]) is not int or not 1 <= data["id"] <= MAX_ID:
        raise Fault("invalid_request_id")
    token = data["session"]
    if token is not None and (type(token) is not str or not re.fullmatch(r"[a-f0-9]{32}", token)):
        raise Fault("invalid_session")
    op = data["op"]
    if type(op) is not str or op not in OPS:
        raise Fault("unknown_operation")
    params = data["params"]
    if op == "set":
        point(params)
    elif op == "prepare":
        fields(params, {"consent"})
        if params["consent"] is not True:
            raise Fault("consent_required")
    elif op == "verify_recovery":
        fields(params, {"independently_checked"})
        if params["independently_checked"] is not True:
            raise Fault("independent_check_required")
    else:
        fields(params, set())
    return Request(data["id"], token, op, params)

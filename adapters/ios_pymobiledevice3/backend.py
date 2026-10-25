# SPDX-License-Identifier: AGPL-3.0-only
"""Real RSD/DVT adapter; no shell, auto-pairing, firmware changes or fake fallback."""
from __future__ import annotations
from contextlib import AsyncExitStack
from importlib.metadata import PackageNotFoundError, version
import ipaddress
from pathlib import Path
import re
from . import PMD3_VERSION
from .protocol import Fault


def dependency_check() -> None:
    try:
        found = version("pymobiledevice3")
    except PackageNotFoundError:
        raise Fault("dependency_missing") from None
    if found != PMD3_VERSION:
        raise Fault("dependency_version_mismatch")


def endpoint(host: str, port: int) -> tuple[str, int]:
    # Explicit local/tunnel address only. No DNS or arbitrary public endpoint.
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise Fault("invalid_endpoint") from None
    if not (address.is_private or address.is_link_local or address.is_loopback):
        raise Fault("endpoint_not_local")
    if address.is_multicast or address.is_unspecified or type(port) is not int or not 1 <= port <= 65535:
        raise Fault("invalid_endpoint")
    if "%" in host and not re.fullmatch(r"[A-Za-z0-9_.-]{1,32}", host.split("%", 1)[1]):
        raise Fault("invalid_endpoint")
    return host, port


def read_identity(path: Path) -> str:
    if path.is_symlink():
        raise Fault("invalid_identity_file")
    try:
        with path.open("rb") as stream:
            raw = stream.read(257)
        value = raw.decode("ascii").strip()
    except (OSError, UnicodeError):
        raise Fault("invalid_identity_file") from None
    if len(raw) > 256 or not re.fullmatch(r"[A-Za-z0-9-]{8,128}", value):
        raise Fault("invalid_identity_file")
    return value


class Pmd3Backend:
    clear_has_reply = False

    def __init__(self, address: tuple[str, int] | None, expected_id: str, expected_ios: str = "18.4.1"):
        self.address = endpoint(*address) if address is not None else None
        self.expected_id = expected_id
        if not re.fullmatch(r"\d{1,2}(?:\.\d{1,3}){1,2}", expected_ios):
            raise Fault("invalid_expected_ios")
        self.expected_ios = expected_ios
        self.stack: AsyncExitStack | None = None
        self.simulation = None

    async def connect(self) -> None:
        dependency_check()
        # Import lazily: documentation/protocol tests do not need device dependencies.
        from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
        from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
        from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
        if self.stack is not None:
            raise Fault("already_connected")
        stack = AsyncExitStack()
        self.stack = stack  # Assigned before awaits so timeout/failure can close partial setup.
        if self.address is None:
            from pymobiledevice3.remote.userspace_tunnel import UserspaceRsdTunnel
            # Explicit device, no first-device fallback and no native/kernel fallback.
            tunnel = UserspaceRsdTunnel(serial=self.expected_id, autopair=False)
            stack.push_async_callback(tunnel.aclose)
            rsd = await tunnel.aopen()
        else:
            rsd = RemoteServiceDiscoveryService(self.address)
            stack.push_async_callback(rsd.close)
            await rsd.connect()
        if rsd.udid != self.expected_id:
            raise Fault("wrong_device")
        if rsd.product_version != self.expected_ios:
            raise Fault("unexpected_ios_version")
        if not await rsd.get_developer_mode_status():
            raise Fault("developer_mode_required")
        # Keep successfully entered DVT/channel contexts in the shared cleanup stack.
        dvt = DvtProvider(rsd)
        await stack.enter_async_context(dvt)
        self.simulation = await stack.enter_async_context(LocationSimulation(dvt))

    async def set(self, latitude: float, longitude: float) -> None:
        if self.simulation is None:
            raise Fault("not_connected")
        await self.simulation.set(latitude, longitude)

    async def clear(self) -> None:
        if self.simulation is None:
            raise Fault("not_connected")
        # Upstream selector is expects_reply=False. This is SEND ONLY, not an ACK.
        await self.simulation.clear()

    async def close(self) -> None:
        stack, self.stack = self.stack, None
        self.simulation = None
        if stack is not None:
            await stack.aclose()

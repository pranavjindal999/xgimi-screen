"""ADB client for the XGIMI screen command."""

from __future__ import annotations

import asyncio
import logging
import os

from adb_shell.adb_device_async import AdbDeviceTcpAsync
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.exceptions import AdbTimeoutError, DeviceAuthError, TcpTimeoutException

from .const import CMD_OFF, CMD_ON, CMD_STATE
from .parser import screen_is_on

_LOGGER = logging.getLogger(__name__)

_UNREACHABLE = (
    AdbTimeoutError,
    TcpTimeoutException,
    TimeoutError,
    OSError,
    ConnectionError,
)


class XgimiAuthRejected(Exception):
    """The projector has not accepted this debugging key."""


class XgimiUnreachable(Exception):
    """The projector did not answer."""


class XgimiNotSupported(Exception):
    """The device did not return a screen state."""


class XgimiClient:
    """Keep one network debugging connection and run screen commands on it."""

    def __init__(self, host: str, port: int, key_path: str) -> None:
        """Store the connection target. The key file is created on first use."""
        self.host = host
        self.port = port
        self.key_path = key_path
        self._device: AdbDeviceTcpAsync | None = None
        self._lock = asyncio.Lock()

    async def async_close(self) -> None:
        """Close the debugging connection."""
        async with self._lock:
            await self._close_locked()

    async def async_probe(self) -> dict[str, str]:
        """Connect and read the identity used for the Home Assistant device."""
        raw = await self._shell(
            "getprop ro.serialno; getprop ro.product.model; "
            "getprop ro.product.manufacturer; settings get global device_name"
        )
        lines = [line.strip() for line in raw.splitlines()]
        while len(lines) < 4:
            lines.append("")
        serial, model, manufacturer, device_name = lines[:4]
        if not serial or serial == "null":
            raise XgimiNotSupported(raw)
        if device_name in ("", "null"):
            device_name = "XGIMI Projector"
        try:
            screen_is_on(await self._shell(CMD_STATE))
        except ValueError as err:
            raise XgimiNotSupported(str(err)) from err
        return {
            "serial": serial,
            "model": model or "XGIMI",
            "manufacturer": manufacturer or "XGIMI",
            "device_name": device_name,
        }

    async def async_screen_is_on(self) -> bool:
        """Read the current image state from the projector."""
        return screen_is_on(await self._shell(CMD_STATE))

    async def async_set_screen(self, turn_on: bool) -> None:
        """Turn the image on or off. The projector itself keeps running."""
        await self._shell(CMD_ON if turn_on else CMD_OFF)

    async def _shell(self, command: str) -> str:
        async with self._lock:
            await self._ensure_locked()
            assert self._device is not None
            try:
                return await self._device.shell(command, read_timeout_s=10, timeout_s=10)
            except _UNREACHABLE:
                await self._close_locked()
                await self._ensure_locked()
                assert self._device is not None
                return await self._device.shell(command, read_timeout_s=10, timeout_s=10)

    async def _ensure_locked(self) -> None:
        if self._device is not None and self._device.available:
            return
        await self._close_locked()
        signer = await asyncio.get_running_loop().run_in_executor(None, self._load_signer)
        device = AdbDeviceTcpAsync(
            self.host, self.port, default_transport_timeout_s=9.0
        )
        try:
            connected = await device.connect(rsa_keys=[signer], auth_timeout_s=8.0)
        except DeviceAuthError as err:
            await _safe_close(device)
            raise XgimiAuthRejected from err
        except _UNREACHABLE as err:
            await _safe_close(device)
            raise XgimiUnreachable(str(err)) from err
        if not connected:
            await _safe_close(device)
            raise XgimiAuthRejected
        self._device = device

    def _load_signer(self) -> PythonRSASigner:
        directory = os.path.dirname(self.key_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(self.key_path):
            keygen(self.key_path)
        return PythonRSASigner.FromRSAKeyPath(self.key_path)

    async def _close_locked(self) -> None:
        device = self._device
        self._device = None
        if device is not None:
            await _safe_close(device)


async def _safe_close(device: AdbDeviceTcpAsync) -> None:
    try:
        await device.close()
    except Exception:
        _LOGGER.debug("Closing the projector connection failed", exc_info=True)

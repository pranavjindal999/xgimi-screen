"""ADB client for the XGIMI projector commands."""

from __future__ import annotations

import asyncio
import logging
import os
import socket

from adb_shell.adb_device_async import AdbDeviceTcpAsync
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.exceptions import AdbTimeoutError, DeviceAuthError, TcpTimeoutException

from .const import (
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    BRIGHTNESS_SETTING,
    CMD_BOOST_OFF,
    CMD_BOOST_ON,
    CMD_OFF,
    CMD_ON,
    CMD_READ_ALL,
    CMD_SLEEP,
    CMD_WAKE_KEY,
    CMD_WIFI_MAC,
    VOLUME_STREAM,
    _DISPLAY,
)
from .parser import ProjectorState, parse_state, parse_wifi_mac
from .wol import magic_packet

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
    """Keep one network debugging connection and run projector commands on it."""

    def __init__(
        self, host: str, port: int, key_path: str, wifi_mac: str | None = None
    ) -> None:
        """Store the connection target. The key file is created on first use."""
        self.host = host
        self.port = port
        self.key_path = key_path
        self.wifi_mac = wifi_mac
        self._mac_checked = wifi_mac is not None
        self.volume_max = 100
        # True after standby, including when the projector no longer answers.
        self.standing_by = False
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
            state = await self.async_state()
        except ValueError as err:
            raise XgimiNotSupported(str(err)) from err
        info = {
            "serial": serial,
            "model": model or "XGIMI",
            "manufacturer": manufacturer or "XGIMI",
            "device_name": device_name,
        }
        if self.wifi_mac:
            info["wifi_mac"] = self.wifi_mac
        if not state.power_on:
            self.standing_by = True
        return info

    async def async_state(self) -> ProjectorState:
        """Read screen, picture, volume, and standby from the projector."""
        state = parse_state(await self._shell(CMD_READ_ALL))
        self.volume_max = state.volume_max
        if not self._mac_checked:
            self._mac_checked = True
            self.wifi_mac = parse_wifi_mac(await self._shell(CMD_WIFI_MAC))
        return state

    async def async_set_screen(self, turn_on: bool) -> None:
        """Turn the image on or off. The projector itself keeps running."""
        await self._shell(CMD_ON if turn_on else CMD_OFF)

    async def async_set_brightness(self, level: int) -> None:
        """Set the 1–10 brightness slider and the picture-menu setting."""
        if level < BRIGHTNESS_MIN or level > BRIGHTNESS_MAX:
            raise ValueError(f"Brightness must be {BRIGHTNESS_MIN}–{BRIGHTNESS_MAX}")
        await self._shell(
            f"{_DISPLAY} 6 i32 {level}; "
            f"settings put global {BRIGHTNESS_SETTING} {level}"
        )

    async def async_set_luminance_boost(self, enabled: bool) -> None:
        """Turn luminance boost on (above level 10) or off."""
        await self._shell(CMD_BOOST_ON if enabled else CMD_BOOST_OFF)

    async def async_set_volume(self, level: int) -> None:
        """Set the music volume by the same key events as the remote rocker.

        Asking AudioService to set the level directly is ignored on this
        projector. The volume keys are not.
        """
        if level < 0 or level > self.volume_max:
            raise ValueError(f"Volume must be 0–{self.volume_max}")
        command = (
            "current=$(cmd media_session volume --stream "
            f"{VOLUME_STREAM} --get | grep -o 'volume is [0-9][0-9]*' | "
            "grep -o '[0-9][0-9]*' | tail -n 1); "
            f"target={level}; "
            'if [ -z "$current" ]; then echo volume-unread; exit 1; fi; '
            'delta=$((target - current)); '
            'if [ "$delta" -eq 0 ]; then exit 0; fi; '
            'if [ "$delta" -gt 0 ]; then key=KEYCODE_VOLUME_UP; '
            "else key=KEYCODE_VOLUME_DOWN; delta=$((-delta)); fi; "
            'keys=""; i=0; '
            'while [ "$i" -lt "$delta" ]; do keys="$keys $key"; i=$((i+1)); done; '
            "input keyevent $keys"
        )
        reply = await self._shell(command, timeout_s=45, retry=False)
        if "volume-unread" in reply:
            raise ValueError("Could not read the projector volume")

    async def async_set_power(self, turn_on: bool) -> None:
        """Enter or leave standby. This does not shut the projector down."""
        if not turn_on:
            self.standing_by = True
            try:
                await self._shell(CMD_SLEEP)
            except XgimiUnreachable:
                return
            return
        self.standing_by = False
        await self._send_wake_packet()
        for _ in range(20):
            try:
                await self._shell(CMD_WAKE_KEY)
                if (await self.async_state()).power_on:
                    return
            except XgimiUnreachable:
                await self._send_wake_packet()
            await asyncio.sleep(1)
        raise XgimiUnreachable("Projector did not leave standby")

    async def _send_wake_packet(self) -> None:
        mac = self.wifi_mac
        if not mac:
            return
        packet = magic_packet(mac)
        targets = [("255.255.255.255", 9), ("255.255.255.255", 7)]
        parts = self.host.split(".")
        if len(parts) == 4 and all(part.isdigit() for part in parts):
            targets.append((".".join([*parts[:3], "255"]), 9))
            targets.append((self.host, 9))
        await asyncio.get_running_loop().run_in_executor(
            None, _send_broadcast, packet, targets
        )

    async def _shell(
        self, command: str, timeout_s: float = 10, retry: bool = True
    ) -> str:
        async with self._lock:
            await self._ensure_locked()
            assert self._device is not None
            try:
                return await self._device.shell(
                    command, read_timeout_s=timeout_s, timeout_s=timeout_s
                )
            except _UNREACHABLE:
                if not retry:
                    raise
                await self._close_locked()
                await self._ensure_locked()
                assert self._device is not None
                return await self._device.shell(
                    command, read_timeout_s=timeout_s, timeout_s=timeout_s
                )

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


def _send_broadcast(packet: bytes, targets: list[tuple[str, int]]) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for target in targets:
            try:
                sock.sendto(packet, target)
            except OSError:
                continue
    finally:
        sock.close()


async def _safe_close(device: AdbDeviceTcpAsync) -> None:
    try:
        await device.close()
    except Exception:
        _LOGGER.debug("Closing the projector connection failed", exc_info=True)

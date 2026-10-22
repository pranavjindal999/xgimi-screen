"""Parse projector replies for screen, picture, volume, and standby."""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEX = set("0123456789abcdefABCDEF")
_BRIGHTNESS_MIN = 1
_BRIGHTNESS_MAX = 10
_VOLUME = re.compile(r"volume is (\d+) in range \[(\d+)\.\.(\d+)\]")
_WAKE = re.compile(r"mWakefulness=([A-Za-z]+)")
_SLEEP_REASON = re.compile(r"mLastSleepReason=([A-Za-z0-9_]+)")
_MAC = re.compile(r"MAC: ([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})")
_ASLEEP = {"Asleep", "Dozing", "GoingToSleep", "Sleeping"}


@dataclass(frozen=True)
class ProjectorState:
    """Values read together from the projector."""

    screen_on: bool
    brightness: int
    luminance_boost: bool
    volume: int
    volume_max: int
    power_on: bool


def screen_is_on(response: str) -> bool:
    """Return whether the image is showing.

    A successful reply looks like ``Parcel(00000000 00000001 ...)``.
    The first word is the call status. The second word is the screen state.
    """
    return parcel_values(response)[0] == 1


def parse_state(response: str) -> ProjectorState:
    """Read screen, brightness, boost, volume, and standby from one shell reply."""
    values = parcel_values(response)
    if len(values) != 3:
        raise ValueError(f"Expected three projector replies, got {len(values)}")
    screen, level, boost = values
    if level < _BRIGHTNESS_MIN or level > _BRIGHTNESS_MAX:
        raise ValueError(f"Unexpected brightness level: {level}")
    if boost not in (0, 1):
        raise ValueError(f"Unexpected luminance boost state: {boost}")
    volume, volume_max = parse_volume(response)
    return ProjectorState(
        screen_on=screen == 1,
        brightness=level,
        luminance_boost=boost == 1,
        volume=volume,
        volume_max=volume_max,
        power_on=parse_power_on(response),
    )


def parse_volume(response: str) -> tuple[int, int]:
    """Return the music-stream level and its maximum."""
    match = _VOLUME.search(response)
    if match is None:
        raise ValueError(f"Unexpected volume reply: {response!r}")
    volume, low, high = (int(group) for group in match.groups())
    if high < low or volume < low or volume > high:
        raise ValueError(f"Unexpected volume reply: {response!r}")
    return volume, high


def parse_power_on(response: str) -> bool:
    """Return whether the projector is out of standby.

    Awake means on. Asleep is standby. Dreaming after the power button is the
    standby path. Any other dream, such as the screensaver, stays on.
    """
    wake = _WAKE.search(response)
    if wake is None:
        raise ValueError(f"Unexpected power reply: {response!r}")
    state = wake.group(1)
    reason_match = _SLEEP_REASON.search(response)
    reason = reason_match.group(1) if reason_match else ""
    if state == "Awake":
        return True
    if state == "Dreaming":
        return reason != "power_button"
    if state in _ASLEEP:
        return False
    raise ValueError(f"Unexpected wakefulness: {state}")


def parse_wifi_mac(response: str) -> str | None:
    """Return the Wi-Fi MAC from ``cmd wifi status``, if it is present."""
    match = _MAC.search(response)
    if match is None:
        return None
    return match.group(1).lower()


def parcel_values(response: str) -> list[int]:
    """Return the second word of each binder parcel in a service-call reply."""
    if "Parcel" not in response:
        raise ValueError(f"Unexpected projector reply: {response!r}")
    values: list[int] = []
    for chunk in response.split("Parcel")[1:]:
        words = [
            token
            for token in chunk.replace("(", " ").replace(")", " ").split()
            if len(token) == 8 and all(char in _HEX for char in token)
        ]
        if len(words) < 2:
            raise ValueError(f"Unexpected projector reply: {response!r}")
        values.append(int(words[1], 16))
    if not values:
        raise ValueError(f"Unexpected projector reply: {response!r}")
    return values

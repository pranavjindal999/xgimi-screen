"""Parse projector replies for screen, brightness, and luminance boost."""

from __future__ import annotations

from dataclasses import dataclass

_HEX = set("0123456789abcdefABCDEF")
_BRIGHTNESS_MIN = 1
_BRIGHTNESS_MAX = 10


@dataclass(frozen=True)
class ProjectorState:
    """Values read together from the projector."""

    screen_on: bool
    brightness: int
    luminance_boost: bool


def screen_is_on(response: str) -> bool:
    """Return whether the image is showing.

    A successful reply looks like ``Parcel(00000000 00000001 ...)``.
    The first word is the call status. The second word is the screen state.
    """
    return parcel_values(response)[0] == 1


def parse_state(response: str) -> ProjectorState:
    """Read screen, brightness (1–10), and luminance boost from one shell reply."""
    values = parcel_values(response)
    if len(values) != 3:
        raise ValueError(f"Expected three projector replies, got {len(values)}")
    screen, level, boost = values
    if level < _BRIGHTNESS_MIN or level > _BRIGHTNESS_MAX:
        raise ValueError(f"Unexpected brightness level: {level}")
    if boost not in (0, 1):
        raise ValueError(f"Unexpected luminance boost state: {boost}")
    return ProjectorState(
        screen_on=screen == 1,
        brightness=level,
        luminance_boost=boost == 1,
    )


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

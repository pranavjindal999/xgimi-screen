"""Parse the projector's screen-state reply."""

from __future__ import annotations

_HEX = set("0123456789abcdefABCDEF")


def screen_is_on(response: str) -> bool:
    """Return whether the image is showing.

    A successful reply looks like ``Parcel(00000000 00000001 ...)``.
    The first word is the call status. The second word is the screen state.
    """
    words = [
        token
        for token in response.replace("(", " ").replace(")", " ").split()
        if len(token) == 8 and all(char in _HEX for char in token)
    ]
    if len(words) < 2:
        raise ValueError(f"Unexpected screen reply: {response!r}")
    return int(words[1], 16) == 1

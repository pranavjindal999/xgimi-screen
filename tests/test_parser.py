"""Screen-reply parsing."""

import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = (
    Path(__file__).parents[1] / "custom_components" / "xgimi_screen" / "parser.py"
)
_SPEC = importlib.util.spec_from_file_location("xgimi_screen_parser", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
parse_state = _MODULE.parse_state
screen_is_on = _MODULE.screen_is_on


def test_screen_on_reply() -> None:
    """The second parcel word is the on state."""
    reply = "Result: Parcel(\t00000000 00000001   '........')"
    assert screen_is_on(reply) is True


def test_screen_off_reply() -> None:
    """A zero second word means the image is off."""
    reply = "Result: Parcel(\t00000000 00000000   '........')"
    assert screen_is_on(reply) is False


def test_unreadable_reply() -> None:
    """A debugging error is not treated as screen off."""
    with pytest.raises(ValueError):
        screen_is_on("error: closed")


def test_combined_state() -> None:
    """Screen, brightness, and boost are the second word of each parcel."""
    reply = (
        "Result: Parcel(\t00000000 00000001   '........')\n"
        "Result: Parcel(\t00000000 00000007   '........')\n"
        "Result: Parcel(\t00000000 00000001   '........')"
    )
    state = parse_state(reply)
    assert state.screen_on is True
    assert state.brightness == 7
    assert state.luminance_boost is True


def test_brightness_out_of_range() -> None:
    """A level outside 1–10 is not shown as a real slider position."""
    reply = (
        "Result: Parcel(\t00000000 00000001   '........')\n"
        "Result: Parcel(\t00000000 00000000   '........')\n"
        "Result: Parcel(\t00000000 00000000   '........')"
    )
    with pytest.raises(ValueError):
        parse_state(reply)

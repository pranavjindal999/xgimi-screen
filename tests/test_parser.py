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
parse_power_on = _MODULE.parse_power_on
parse_state = _MODULE.parse_state
parse_wifi_mac = _MODULE.parse_wifi_mac
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


_SAMPLE = """Result: Parcel(\t00000000 00000001   '........')
Result: Parcel(\t00000000 00000007   '........')
Result: Parcel(\t00000000 00000001   '........')
[V] volume is 17 in range [0..100]
  mWakefulness=Awake
  mLastSleepReason=application
"""


def test_combined_state() -> None:
    """One shell reply carries screen, picture, volume, and standby."""
    state = parse_state(_SAMPLE)
    assert state.screen_on is True
    assert state.brightness == 7
    assert state.luminance_boost is True
    assert state.volume == 17
    assert state.volume_max == 100
    assert state.power_on is True


def test_power_button_standby() -> None:
    """Dreaming after the power button is standby."""
    reply = "mWakefulness=Dreaming\nmLastSleepReason=power_button"
    assert parse_power_on(reply) is False


def test_screensaver_stays_on() -> None:
    """A dream that did not come from the power button is still on."""
    reply = "mWakefulness=Dreaming\nmLastSleepReason=timeout"
    assert parse_power_on(reply) is True


def test_asleep_is_standby() -> None:
    """Deep sleep is standby."""
    assert parse_power_on("mWakefulness=Asleep") is False


def test_wifi_mac() -> None:
    """The Wi-Fi status line is the address used to wake the projector."""
    raw = 'WifiInfo: MAC: 32:59:9A:3E:C1:F6, IP: /192.168.1.8'
    assert parse_wifi_mac(raw) == "32:59:9a:3e:c1:f6"


def test_brightness_out_of_range() -> None:
    """A level outside 1–10 is not shown as a real slider position."""
    reply = (
        "Result: Parcel(\t00000000 00000001   '........')\n"
        "Result: Parcel(\t00000000 00000000   '........')\n"
        "Result: Parcel(\t00000000 00000000   '........')"
    )
    with pytest.raises(ValueError):
        parse_state(reply)

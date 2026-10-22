"""Wake packet formatting."""

import importlib.util
from pathlib import Path

_PATH = Path(__file__).parents[1] / "custom_components" / "xgimi_screen" / "wol.py"
_SPEC = importlib.util.spec_from_file_location("xgimi_screen_wol", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
magic_packet = _MODULE.magic_packet


def test_magic_packet() -> None:
    """A wake frame is six 0xff bytes plus the MAC repeated sixteen times."""
    packet = magic_packet("32:59:9a:3e:c1:f6")
    hardware = bytes.fromhex("32599a3ec1f6")
    assert packet == b"\xff" * 6 + hardware * 16

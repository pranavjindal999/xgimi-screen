"""Wake-on-LAN packet for bringing the projector out of standby."""

from __future__ import annotations


def magic_packet(mac: str) -> bytes:
    """Build a Wake-on-LAN frame for a MAC address like ``32:59:9a:3e:c1:f6``."""
    parts = mac.split(":")
    if len(parts) != 6:
        raise ValueError(f"Unexpected MAC address: {mac!r}")
    hardware = bytes(int(part, 16) for part in parts)
    return b"\xff" * 6 + hardware * 16

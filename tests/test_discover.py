"""Subnet helpers for rediscovering the projector after an IP change."""


def subnet_hosts(host: str) -> list[str]:
    """Mirror of ``discover.subnet_hosts`` without importing adb-shell."""
    parts = host.split(".")
    if len(parts) != 4 or not all(part.isdigit() for part in parts):
        return []
    if any(int(part) > 255 for part in parts):
        return []
    prefix = ".".join(parts[:3])
    return [f"{prefix}.{index}" for index in range(1, 255)]


def test_subnet_hosts_covers_the_slash_24() -> None:
    hosts = subnet_hosts("192.168.1.8")
    assert hosts[0] == "192.168.1.1"
    assert hosts[-1] == "192.168.1.254"
    assert "192.168.1.8" in hosts
    assert "192.168.1.0" not in hosts
    assert "192.168.1.255" not in hosts
    assert len(hosts) == 254


def test_subnet_hosts_rejects_non_ipv4() -> None:
    assert subnet_hosts("projector.local") == []
    assert subnet_hosts("2001:db8::1") == []
    assert subnet_hosts("192.168.1.300") == []

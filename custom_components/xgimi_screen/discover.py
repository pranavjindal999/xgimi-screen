"""Find the projector again after its IP changes."""

from __future__ import annotations

import asyncio
import logging

from .client import XgimiAuthRejected, XgimiClient, XgimiNotSupported, XgimiUnreachable

_LOGGER = logging.getLogger(__name__)

# Keep the scan short. A /24 at this concurrency finishes in a couple of seconds.
_TCP_TIMEOUT_S = 0.35
_TCP_CONCURRENCY = 64
_ADB_CONCURRENCY = 8


def subnet_hosts(host: str) -> list[str]:
    """Return every usable address on the /24 that contains ``host``."""
    parts = host.split(".")
    if len(parts) != 4 or not all(part.isdigit() for part in parts):
        return []
    if any(int(part) > 255 for part in parts):
        return []
    prefix = ".".join(parts[:3])
    return [f"{prefix}.{index}" for index in range(1, 255)]


async def tcp_open(host: str, port: int, timeout_s: float = _TCP_TIMEOUT_S) -> bool:
    """Return whether ``host:port`` accepts a TCP connection."""
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout_s
        )
    except (OSError, TimeoutError, asyncio.TimeoutError):
        return False
    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass
    return True


async def find_host_by_serial(
    serial: str,
    last_host: str,
    port: int,
    key_path: str,
) -> str | None:
    """Scan the last-known /24 for an ADB device that reports ``serial``.

    Hosts that do not answer on the debugging port are skipped. Hosts that
    answer but reject this debugging key, or report a different serial, are
    ignored. The first match wins.
    """
    hosts = subnet_hosts(last_host)
    if not hosts:
        _LOGGER.debug("Cannot derive a subnet from projector host %s", last_host)
        return None

    tcp_limit = asyncio.Semaphore(_TCP_CONCURRENCY)

    async def _probe_tcp(host: str) -> str | None:
        async with tcp_limit:
            return host if await tcp_open(host, port) else None

    open_hosts = [
        host
        for host in await asyncio.gather(*(_probe_tcp(host) for host in hosts))
        if host is not None
    ]
    if not open_hosts:
        _LOGGER.debug("No ADB listeners found near %s", last_host)
        return None

    # Prefer a new address. The old one already failed to answer.
    ordered = [host for host in open_hosts if host != last_host]
    if last_host in open_hosts:
        ordered.append(last_host)

    adb_limit = asyncio.Semaphore(_ADB_CONCURRENCY)
    found: str | None = None
    found_lock = asyncio.Lock()

    async def _probe_serial(host: str) -> None:
        nonlocal found
        async with found_lock:
            if found is not None:
                return
        async with adb_limit:
            async with found_lock:
                if found is not None:
                    return
            client = XgimiClient(host, port, key_path)
            try:
                reported = await client.async_read_serial()
            except (XgimiUnreachable, XgimiAuthRejected, XgimiNotSupported, ValueError):
                return
            except Exception:
                _LOGGER.debug("Ignoring %s during rediscovery", host, exc_info=True)
                return
            finally:
                await client.async_close()
            if reported != serial:
                return
            async with found_lock:
                if found is None:
                    found = host

    await asyncio.gather(*(_probe_serial(host) for host in ordered))
    return found

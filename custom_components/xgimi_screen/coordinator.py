"""Poll the projector so controls match the remote and the picture menu."""

from __future__ import annotations

import logging
import time
from dataclasses import replace

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import XgimiAuthRejected, XgimiClient, XgimiUnreachable
from .const import DOMAIN, POLL_INTERVAL, adb_key_path
from .discover import find_host_by_serial
from .parser import ProjectorState

_LOGGER = logging.getLogger(__name__)

# Do not scan the LAN on every failed poll. A /24 probe is cheap, but not free.
_REDISCOVER_COOLDOWN_S = 30.0


class XgimiCoordinator(DataUpdateCoordinator[ProjectorState]):
    """Screen, picture, volume, and standby, read from the projector."""

    def __init__(
        self, hass: HomeAssistant, client: XgimiClient, entry: ConfigEntry
    ) -> None:
        """Poll the projector every second."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=POLL_INTERVAL,
        )
        self.client = client
        self.entry = entry
        self._last_rediscover = 0.0
        self._rediscovering = False

    async def _async_update_data(self) -> ProjectorState:
        try:
            state = await self.client.async_state()
        except XgimiUnreachable as err:
            # Standby drops the network. Keep the last reading and show power off.
            if self.client.standing_by and self.data is not None:
                return replace(self.data, power_on=False)
            if await self.async_rediscover():
                try:
                    state = await self.client.async_state()
                except XgimiUnreachable as retry_err:
                    raise UpdateFailed(
                        str(retry_err) or retry_err.__class__.__name__
                    ) from retry_err
            else:
                raise UpdateFailed(str(err) or err.__class__.__name__) from err
        except (XgimiAuthRejected, ValueError) as err:
            raise UpdateFailed(str(err) or err.__class__.__name__) from err
        self.client.standing_by = not state.power_on
        updates: dict[str, str] = {}
        mac = self.client.wifi_mac
        if mac and self.entry.data.get("wifi_mac") != mac:
            updates["wifi_mac"] = mac
        if self.client.host != self.entry.data.get(CONF_HOST):
            updates[CONF_HOST] = self.client.host
        if updates:
            self.hass.config_entries.async_update_entry(
                self.entry, data={**self.entry.data, **updates}
            )
        return state

    async def async_rediscover(self, *, force: bool = False) -> bool:
        """Scan the last-known subnet for this projector's serial.

        Returns True when the client was pointed at a new working address.
        """
        serial = self.entry.data.get("serial")
        if not serial:
            return False
        if self._rediscovering:
            return False
        now = time.monotonic()
        if not force and now - self._last_rediscover < _REDISCOVER_COOLDOWN_S:
            return False
        self._last_rediscover = now
        self._rediscovering = True
        try:
            found = await find_host_by_serial(
                serial,
                self.client.host,
                self.client.port,
                adb_key_path(self.hass),
            )
        finally:
            self._rediscovering = False
        if not found or found == self.client.host:
            return False
        _LOGGER.info(
            "Projector %s answered at %s instead of %s",
            serial,
            found,
            self.client.host,
        )
        await self.client.async_set_host(found)
        self.hass.config_entries.async_update_entry(
            self.entry, data={**self.entry.data, CONF_HOST: found}
        )
        return True

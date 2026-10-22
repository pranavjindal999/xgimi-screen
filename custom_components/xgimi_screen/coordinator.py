"""Poll the projector so controls match the remote and the picture menu."""

from __future__ import annotations

import logging
from dataclasses import replace

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import XgimiAuthRejected, XgimiClient, XgimiUnreachable
from .const import DOMAIN, POLL_INTERVAL
from .parser import ProjectorState

_LOGGER = logging.getLogger(__name__)


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

    async def _async_update_data(self) -> ProjectorState:
        try:
            state = await self.client.async_state()
        except XgimiUnreachable as err:
            # Standby drops the network. Keep the last reading and show power off.
            if self.client.standing_by and self.data is not None:
                return replace(self.data, power_on=False)
            raise UpdateFailed(str(err) or err.__class__.__name__) from err
        except (XgimiAuthRejected, ValueError) as err:
            raise UpdateFailed(str(err) or err.__class__.__name__) from err
        self.client.standing_by = not state.power_on
        mac = self.client.wifi_mac
        if mac and self.entry.data.get("wifi_mac") != mac:
            self.hass.config_entries.async_update_entry(
                self.entry, data={**self.entry.data, "wifi_mac": mac}
            )
        return state

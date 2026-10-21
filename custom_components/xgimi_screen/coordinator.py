"""Poll the projector so the switch matches the remote."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import XgimiAuthRejected, XgimiClient, XgimiUnreachable
from .const import DOMAIN, POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class XgimiCoordinator(DataUpdateCoordinator[bool]):
    """Screen state. True means the image is showing."""

    def __init__(self, hass: HomeAssistant, client: XgimiClient) -> None:
        """Poll the projector every few seconds."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=POLL_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> bool:
        try:
            return await self.client.async_screen_is_on()
        except (XgimiUnreachable, XgimiAuthRejected, ValueError) as err:
            raise UpdateFailed(str(err) or err.__class__.__name__) from err

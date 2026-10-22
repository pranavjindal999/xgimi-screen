"""Poll the projector so controls match the remote and the picture menu."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import XgimiAuthRejected, XgimiClient, XgimiUnreachable
from .const import DOMAIN, POLL_INTERVAL
from .parser import ProjectorState

_LOGGER = logging.getLogger(__name__)


class XgimiCoordinator(DataUpdateCoordinator[ProjectorState]):
    """Screen, brightness, and luminance boost, read from the projector."""

    def __init__(self, hass: HomeAssistant, client: XgimiClient) -> None:
        """Poll the projector every second."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=POLL_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> ProjectorState:
        try:
            return await self.client.async_state()
        except (XgimiUnreachable, XgimiAuthRejected, ValueError) as err:
            raise UpdateFailed(str(err) or err.__class__.__name__) from err

"""Screen switch that follows the projector, including the remote."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODEL_NAMES
from .coordinator import XgimiCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the screen switch."""
    coordinator: XgimiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([XgimiScreenSwitch(coordinator, entry)])


class XgimiScreenSwitch(CoordinatorEntity[XgimiCoordinator], SwitchEntity):
    """On when the image is showing. Off is screen off, not shutdown."""

    _attr_has_entity_name = True
    _attr_name = "Screen"
    _attr_icon = "mdi:projector-screen"

    def __init__(self, coordinator: XgimiCoordinator, entry: ConfigEntry) -> None:
        """Attach the switch to the projector device."""
        super().__init__(coordinator)
        data = entry.data
        model = data["model"]
        self._attr_unique_id = f"{data['serial']}_screen"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, data["serial"])},
            manufacturer=data.get("manufacturer") or "XGIMI",
            model=MODEL_NAMES.get(model, model),
            name=data["device_name"],
            serial_number=data["serial"],
        )

    @property
    def is_on(self) -> bool | None:
        """Report the last state read from the projector."""
        return self.coordinator.data

    @property
    def icon(self) -> str:
        """Use the blank-screen icon while the image is off."""
        if self.is_on is False:
            return "mdi:projector-screen-off"
        return "mdi:projector-screen"

    async def async_turn_on(self, **kwargs: object) -> None:
        """Show the image, then read the projector again."""
        await self.coordinator.client.async_set_screen(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Blank the image, then read the projector again."""
        await self.coordinator.client.async_set_screen(False)
        await self.coordinator.async_request_refresh()

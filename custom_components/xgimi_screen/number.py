"""Brightness slider, levels 1 through 10."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BRIGHTNESS_MAX, BRIGHTNESS_MIN, DOMAIN
from .coordinator import XgimiCoordinator
from .device import projector_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the brightness and volume controls."""
    coordinator: XgimiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            XgimiBrightnessNumber(coordinator, entry),
            XgimiVolumeNumber(coordinator, entry),
        ]
    )


class XgimiBrightnessNumber(CoordinatorEntity[XgimiCoordinator], NumberEntity):
    """The picture-menu brightness slider. Luminance boost is a separate switch."""

    _attr_has_entity_name = True
    _attr_name = "Brightness"
    _attr_icon = "mdi:brightness-6"
    _attr_native_min_value = BRIGHTNESS_MIN
    _attr_native_max_value = BRIGHTNESS_MAX
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: XgimiCoordinator, entry: ConfigEntry) -> None:
        """Attach the slider to the projector device."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data['serial']}_brightness"
        self._attr_device_info = projector_device_info(entry)

    @property
    def native_value(self) -> float | None:
        """Report the last brightness level read from the projector."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.brightness

    async def async_set_native_value(self, value: float) -> None:
        """Set the level, then read the projector again."""
        await self.coordinator.client.async_set_brightness(int(value))
        await self.coordinator.async_request_refresh()


class XgimiVolumeNumber(CoordinatorEntity[XgimiCoordinator], NumberEntity):
    """The remote volume rocker. Zero is the bottom of the scale."""

    _attr_has_entity_name = True
    _attr_name = "Volume"
    _attr_icon = "mdi:volume-high"
    _attr_native_min_value = 0
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: XgimiCoordinator, entry: ConfigEntry) -> None:
        """Attach the slider to the projector device."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data['serial']}_volume"
        self._attr_device_info = projector_device_info(entry)

    @property
    def native_max_value(self) -> float:
        """Use the maximum the projector reported."""
        if self.coordinator.data is None:
            return 100
        return self.coordinator.data.volume_max

    @property
    def native_value(self) -> float | None:
        """Report the last volume read from the projector."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.volume

    @property
    def icon(self) -> str:
        """Use a quieter icon at the bottom of the scale."""
        if self.native_value == 0:
            return "mdi:volume-mute"
        return "mdi:volume-high"

    async def async_set_native_value(self, value: float) -> None:
        """Set the volume, then read the projector again."""
        await self.coordinator.client.async_set_volume(int(value))
        await self.coordinator.async_request_refresh()

"""Switches that follow the projector, including the remote and picture menu."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import XgimiCoordinator
from .device import projector_device_info
from .parser import ProjectorState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the power, screen, and luminance-boost switches."""
    coordinator: XgimiCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            XgimiPowerSwitch(coordinator, entry),
            XgimiScreenSwitch(coordinator, entry),
            XgimiLuminanceBoostSwitch(coordinator, entry),
        ]
    )


class _XgimiSwitch(CoordinatorEntity[XgimiCoordinator], SwitchEntity):
    """A switch whose state is the last value read from the projector."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: XgimiCoordinator, entry: ConfigEntry) -> None:
        """Attach the switch to the projector device."""
        super().__init__(coordinator)
        self._attr_device_info = projector_device_info(entry)

    def _state(self) -> ProjectorState | None:
        return self.coordinator.data


class XgimiPowerSwitch(_XgimiSwitch):
    """On when the projector is out of standby. Off is sleep, not shutdown."""

    _attr_name = "Power"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator: XgimiCoordinator, entry: ConfigEntry) -> None:
        """Attach the power switch to the projector device."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data['serial']}_power"

    @property
    def is_on(self) -> bool | None:
        """Report whether the projector is out of standby."""
        state = self._state()
        if state is None:
            return None
        return state.power_on

    @property
    def icon(self) -> str:
        """Use the standby icon while the projector is asleep."""
        if self.is_on is False:
            return "mdi:power-standby"
        return "mdi:power"

    async def async_turn_on(self, **kwargs: object) -> None:
        """Leave standby, then read the projector again."""
        await self.coordinator.client.async_set_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Enter standby, then read the projector again."""
        await self.coordinator.client.async_set_power(False)
        await self.coordinator.async_request_refresh()


class XgimiScreenSwitch(_XgimiSwitch):
    """On when the image is showing. Off is screen off, not shutdown."""

    _attr_name = "Screen"
    _attr_icon = "mdi:projector-screen"

    def __init__(self, coordinator: XgimiCoordinator, entry: ConfigEntry) -> None:
        """Attach the screen switch to the projector device."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data['serial']}_screen"

    @property
    def is_on(self) -> bool | None:
        """Report the last image state read from the projector."""
        state = self._state()
        if state is None:
            return None
        return state.screen_on

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


class XgimiLuminanceBoostSwitch(_XgimiSwitch):
    """On sends the light engine past brightness level 10."""

    _attr_name = "Luminance boost"
    _attr_icon = "mdi:brightness-7"

    def __init__(self, coordinator: XgimiCoordinator, entry: ConfigEntry) -> None:
        """Attach the boost switch to the projector device."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.data['serial']}_luminance_boost"

    @property
    def is_on(self) -> bool | None:
        """Report the last boost state read from the projector."""
        state = self._state()
        if state is None:
            return None
        return state.luminance_boost

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable luminance boost, then read the projector again."""
        await self.coordinator.client.async_set_luminance_boost(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable luminance boost, then read the projector again."""
        await self.coordinator.client.async_set_luminance_boost(False)
        await self.coordinator.async_request_refresh()

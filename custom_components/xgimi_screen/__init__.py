"""XGIMI projector controls for Home Assistant."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .client import XgimiClient, XgimiUnreachable
from .const import ATTR_KEY, DOMAIN, REMOTE_KEYS, SERVICE_SEND_KEY, adb_key_path
from .coordinator import XgimiCoordinator

PLATFORMS = [Platform.NUMBER, Platform.SWITCH]
CARD_URL = "/xgimi_screen/xgimi-screen-card.js"

SEND_KEY_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required(ATTR_KEY): vol.In(tuple(REMOTE_KEYS)),
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve the dashboard card that groups every projector control."""
    if not hass.data.setdefault(DOMAIN, {}).get("card_registered"):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    "/xgimi_screen",
                    str(Path(__file__).parent / "www"),
                    cache_headers=False,
                )
            ]
        )
        add_extra_js_url(hass, CARD_URL)
        hass.data[DOMAIN]["card_registered"] = True

    async def async_send_key(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        key = call.data[ATTR_KEY]
        registry = er.async_get(hass)
        entity = registry.async_get(entity_id)
        if entity is None or entity.config_entry_id is None:
            raise ServiceValidationError(f"Unknown projector entity: {entity_id}")
        coordinator = hass.data.get(DOMAIN, {}).get(entity.config_entry_id)
        if not isinstance(coordinator, XgimiCoordinator):
            raise ServiceValidationError(f"Unknown projector entity: {entity_id}")
        try:
            await coordinator.client.async_send_key(key)
        except XgimiUnreachable as err:
            raise HomeAssistantError("Projector did not answer") from err
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    if not hass.services.has_service(DOMAIN, SERVICE_SEND_KEY):
        hass.services.async_register(
            DOMAIN, SERVICE_SEND_KEY, async_send_key, schema=SEND_KEY_SCHEMA
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Connect to the projector and expose its controls."""
    client = XgimiClient(
        entry.data["host"],
        entry.data["port"],
        adb_key_path(hass),
        wifi_mac=entry.data.get("wifi_mac"),
    )
    coordinator = XgimiCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove the controls and close the projector connection."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: XgimiCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.client.async_close()
    return unload_ok

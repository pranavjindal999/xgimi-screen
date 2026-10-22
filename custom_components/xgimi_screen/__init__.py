"""XGIMI projector controls for Home Assistant."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .client import XgimiClient
from .const import DOMAIN, adb_key_path
from .coordinator import XgimiCoordinator

PLATFORMS = [Platform.NUMBER, Platform.SWITCH]
CARD_URL = "/xgimi_screen/xgimi-screen-card.js"


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

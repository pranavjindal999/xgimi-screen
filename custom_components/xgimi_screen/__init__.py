"""XGIMI projector controls for Home Assistant."""

from __future__ import annotations

import json
import logging
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

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.NUMBER, Platform.SWITCH]
CARD_PATH = "/xgimi_screen/xgimi-screen-card.js"
_WWW = Path(__file__).parent / "www"
_MANIFEST = Path(__file__).parent / "manifest.json"

try:
    _CARD_VERSION = json.loads(_MANIFEST.read_text(encoding="utf-8"))["version"]
except Exception:
    _CARD_VERSION = "0"

CARD_URL = f"{CARD_PATH}?v={_CARD_VERSION}"

SEND_KEY_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required(ATTR_KEY): vol.In(tuple(REMOTE_KEYS)),
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve the dashboard card and register projector services."""
    await _async_register_card(hass)

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


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve the card JS and register it as a Lovelace resource.

    ``add_extra_js_url`` alone races the dashboard on storage-mode Lovelace and
    surfaces as "Custom element doesn't exist". Persistent Lovelace resources
    are what HACS cards use and what the dashboard awaits before rendering.
    """
    if hass.data.setdefault(DOMAIN, {}).get("card_registered"):
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig("/xgimi_screen", str(_WWW), cache_headers=False)]
    )
    add_extra_js_url(hass, CARD_URL)
    await _async_ensure_lovelace_resource(hass)
    hass.data[DOMAIN]["card_registered"] = True


async def _async_ensure_lovelace_resource(hass: HomeAssistant) -> None:
    """Keep one versioned Lovelace resource pointing at the card."""
    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None) if lovelace else None
    if resources is None:
        return
    try:
        if not resources.loaded:
            await resources.async_load()
        existing = None
        for item in list(resources.async_items()):
            url = item.get("url", "")
            if url == CARD_PATH or url.startswith(f"{CARD_PATH}?"):
                existing = item
                break
        if existing is None:
            await resources.async_create_item(
                {"res_type": "module", "url": CARD_URL}
            )
            _LOGGER.info("Registered XGIMI Screen card as a Lovelace resource")
        elif existing.get("url") != CARD_URL:
            await resources.async_update_item(
                existing["id"],
                {"res_type": "module", "url": CARD_URL},
            )
            _LOGGER.info("Updated XGIMI Screen card resource to v%s", _CARD_VERSION)
    except Exception:
        _LOGGER.debug("Could not register Lovelace resource", exc_info=True)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Connect to the projector and expose its controls."""
    await _async_register_card(hass)
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

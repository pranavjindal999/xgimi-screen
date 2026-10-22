"""Shared device identity for every projector entity."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MODEL_NAMES


def projector_device_info(entry: ConfigEntry) -> DeviceInfo:
    """The projector these entities belong to."""
    data = entry.data
    model = data["model"]
    return DeviceInfo(
        identifiers={(DOMAIN, data["serial"])},
        manufacturer=data.get("manufacturer") or "XGIMI",
        model=MODEL_NAMES.get(model, model),
        name=data["device_name"],
        serial_number=data["serial"],
    )

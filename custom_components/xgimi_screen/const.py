"""Constants for the XGIMI screen integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant

DOMAIN = "xgimi_screen"


def adb_key_path(hass: HomeAssistant) -> str:
    """Path of the debugging key Home Assistant uses for the projector."""
    return hass.config.path(".storage", "xgimi_screen_adbkey")


DEFAULT_HOST = "192.168.1.8"
DEFAULT_PORT = 5555
POLL_INTERVAL = timedelta(seconds=5)

# Binder transactions on xgimi.hardware.gmpf.IDisplayManager.
# 27 sets the image on or off. 28 reads it back. The projector stays running.
CMD_ON = "service call xgimi.hardware.gmpf.IDisplayManager/default 27 i32 1"
CMD_OFF = "service call xgimi.hardware.gmpf.IDisplayManager/default 27 i32 0"
CMD_STATE = "service call xgimi.hardware.gmpf.IDisplayManager/default 28"

MODEL_NAMES = {
    "XR16A": "Horizon 20 Max",
}

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
POLL_INTERVAL = timedelta(seconds=1)

# Binder transactions on xgimi.hardware.gmpf.IDisplayManager.
# 27 sets the image on or off. 28 reads it back. The projector stays running.
# 6 sets the 1–10 brightness level. 7 reads it back.
# 151 sets luminance boost (lens display mode 1). 152 reads it back.
_DISPLAY = "service call xgimi.hardware.gmpf.IDisplayManager/default"
CMD_ON = f"{_DISPLAY} 27 i32 1"
CMD_OFF = f"{_DISPLAY} 27 i32 0"
CMD_STATE = f"{_DISPLAY} 28"
CMD_BRIGHTNESS_STATE = f"{_DISPLAY} 7"
CMD_BOOST_ON = f"{_DISPLAY} 151 i32 1"
CMD_BOOST_OFF = f"{_DISPLAY} 151 i32 0"
CMD_BOOST_STATE = f"{_DISPLAY} 152"
# Music stream. The remote volume rocker changes this. Range is read from the reply.
CMD_VOLUME_STATE = "cmd media_session volume --stream 3 --get"
# Short-press standby. KEYCODE_SLEEP is go-to-sleep, not the shutdown menu.
CMD_SLEEP = "input keyevent KEYCODE_SLEEP"
CMD_WAKE_KEY = "input keyevent KEYCODE_WAKEUP"
CMD_POWER_STATE = "dumpsys power | grep -E 'mWakefulness=|mLastSleepReason='"
CMD_WIFI_MAC = "cmd wifi status"
CMD_READ_ALL = (
    f"{CMD_STATE}; {CMD_BRIGHTNESS_STATE}; {CMD_BOOST_STATE}; "
    f"{CMD_VOLUME_STATE}; {CMD_POWER_STATE}"
)

BRIGHTNESS_MIN = 1
BRIGHTNESS_MAX = 10
VOLUME_STREAM = 3

# The picture menu stores the slider here and follows changes to it.
BRIGHTNESS_SETTING = "gm_projector_brightness"

MODEL_NAMES = {
    "XR16A": "Horizon 20 Max",
}

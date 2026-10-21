"""Config flow for connecting a projector."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT

from .client import (
    XgimiAuthRejected,
    XgimiClient,
    XgimiNotSupported,
    XgimiUnreachable,
)
from .const import DEFAULT_HOST, DEFAULT_PORT, DOMAIN, adb_key_path


def _address_schema(host: str, port: int) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=host): str,
            vol.Required(CONF_PORT, default=port): int,
        }
    )


class XgimiScreenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the projector address, then confirm debugging is allowed."""

    VERSION = 1

    def __init__(self) -> None:
        """Remember the address between the allow-debugging step and setup."""
        self._host = DEFAULT_HOST
        self._port = DEFAULT_PORT

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Collect the projector address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._host = user_input[CONF_HOST].strip()
            self._port = int(user_input[CONF_PORT])
            info, error = await self._async_try_connect()
            if error == "not_authorized":
                return await self.async_step_authorize()
            if error:
                errors["base"] = error
            elif info is not None:
                return await self._async_finish(info)
        return self.async_show_form(
            step_id="user",
            data_schema=_address_schema(self._host, self._port),
            errors=errors,
        )

    async def async_step_authorize(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Wait until the projector accepts the debugging key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            info, error = await self._async_try_connect()
            if error:
                errors["base"] = error
            elif info is not None:
                return await self._async_finish(info)
        return self.async_show_form(step_id="authorize", errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Update the address after the projector gets a new IP."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            self._host = user_input[CONF_HOST].strip()
            self._port = int(user_input[CONF_PORT])
            info, error = await self._async_try_connect()
            if error == "not_authorized":
                errors["base"] = "not_authorized"
            elif error:
                errors["base"] = error
            elif info is not None:
                await self.async_set_unique_id(info["serial"])
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_HOST: self._host,
                        CONF_PORT: self._port,
                        **info,
                    },
                )
        host = entry.data[CONF_HOST] if user_input is None else self._host
        port = entry.data[CONF_PORT] if user_input is None else self._port
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_address_schema(host, port),
            errors=errors,
        )

    async def _async_try_connect(
        self,
    ) -> tuple[dict[str, str] | None, str | None]:
        client = XgimiClient(self._host, self._port, adb_key_path(self.hass))
        try:
            return await client.async_probe(), None
        except XgimiAuthRejected:
            return None, "not_authorized"
        except XgimiUnreachable:
            return None, "cannot_connect"
        except XgimiNotSupported:
            return None, "not_xgimi"
        except Exception:
            return None, "unknown"
        finally:
            await client.async_close()

    async def _async_finish(self, info: dict[str, str]) -> ConfigFlowResult:
        await self.async_set_unique_id(info["serial"])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=info["device_name"],
            data={
                CONF_HOST: self._host,
                CONF_PORT: self._port,
                **info,
            },
        )

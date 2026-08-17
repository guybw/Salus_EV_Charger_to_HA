"""Config flow for the Salus EV Charger integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .api import SalusApiClient, SalusApiError
from .const import (
    CONF_REFRESH_TOKEN,
    CONF_THING_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class SalusEvChargerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Salus EV Charger."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SalusEvChargerOptionsFlow:
        return SalusEvChargerOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            client = SalusApiClient(username=email)
            try:
                await self.hass.async_add_executor_job(client.login, password)
                thing_name = await self.hass.async_add_executor_job(client.get_thing_name)
            except SalusApiError as exc:
                _LOGGER.warning("Salus login/lookup failed: %s", exc)
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during Salus config flow")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(thing_name)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Salus EV Charger ({thing_name})",
                    data={
                        CONF_EMAIL: email,
                        CONF_REFRESH_TOKEN: client.refresh_token,
                        CONF_THING_NAME: thing_name,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class SalusEvChargerOptionsFlow(config_entries.OptionsFlowWithReload):
    """Lets the user pick the shadow-polling interval after setup.

    OptionsFlowWithReload automatically reloads the config entry (and thus
    the coordinator, picking up the new interval) whenever options change --
    no manual update listener needed. Deliberately no __init__ override --
    recent Home Assistant versions supply self.config_entry automatically,
    and assigning to it manually raises AttributeError (it's a read-only
    property) on those versions, which is what caused the 500 error.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=5,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="s",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

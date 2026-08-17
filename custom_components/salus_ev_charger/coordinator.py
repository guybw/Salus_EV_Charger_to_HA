"""DataUpdateCoordinator for the Salus EV Charger integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SalusApiClient, SalusApiError, extract_reported_properties
from .const import CONF_REFRESH_TOKEN, CONF_THING_NAME, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SalusDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the charger's AWS IoT shadow and exposes flat reported properties."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.entry = entry
        self.client = SalusApiClient(
            username=entry.data[CONF_EMAIL],
            refresh_token=entry.data[CONF_REFRESH_TOKEN],
            thing_name=entry.data.get(CONF_THING_NAME),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            shadow = await self.hass.async_add_executor_job(self.client.get_shadow)
        except SalusApiError as exc:
            raise UpdateFailed(str(exc)) from exc

        self._persist_refresh_token_if_changed()
        return extract_reported_properties(shadow)

    def _persist_refresh_token_if_changed(self) -> None:
        """Cognito refresh tokens can rotate; keep the config entry in sync."""
        new_token = self.client.refresh_token
        if new_token and new_token != self.entry.data.get(CONF_REFRESH_TOKEN):
            self.hass.config_entries.async_update_entry(
                self.entry,
                data={**self.entry.data, CONF_REFRESH_TOKEN: new_token},
            )

    async def async_set_desired(self, properties: dict[str, Any]) -> None:
        """Write to the shadow's desired state and refresh afterward."""
        try:
            await self.hass.async_add_executor_job(self.client.update_shadow, properties)
        except SalusApiError as exc:
            raise UpdateFailed(str(exc)) from exc
        await self.async_request_refresh()

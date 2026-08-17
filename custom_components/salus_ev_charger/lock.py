"""Lock entity (charger connector lock) for the Salus EV Charger integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_THING_NAME, DOMAIN
from .coordinator import SalusDataUpdateCoordinator
from .shadow_helpers import connector

REPORTED_PROPERTY = "ep0:sCharger:IsLocked"
# Unverified: no observed desired-state write for this property exists in
# research.md (only SetOffPeakScheduleOn and SetStaticLoadManagement writes
# were directly confirmed). Guessing it mirrors the reported value's own
# "Locked"/"Unlocked" string format and connector nesting -- test carefully
# before relying on it, same caveat as the charging_on switch.
DESIRED_PROPERTY = "ep0:sCharger:SetIsLocked"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the charger lock entity from a config entry."""
    coordinator: SalusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SalusChargerLock(coordinator, entry)])


class SalusChargerLock(CoordinatorEntity[SalusDataUpdateCoordinator], LockEntity):
    """Locks/unlocks the charger's connector."""

    _attr_has_entity_name = True
    _attr_name = "Charger Lock"

    def __init__(self, coordinator: SalusDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        thing_name = entry.data[CONF_THING_NAME]
        self._attr_unique_id = f"{thing_name}_charger_lock"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, thing_name)},
            name="Salus EV Charger",
            manufacturer="Salus",
        )

    @property
    def is_locked(self) -> bool | None:
        value = connector(self.coordinator.data or {}, REPORTED_PROPERTY)
        if value is None:
            return None
        return str(value).lower() == "locked"

    async def async_lock(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_desired({DESIRED_PROPERTY: {"connector_1": "Locked"}})

    async def async_unlock(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_desired({DESIRED_PROPERTY: {"connector_1": "Unlocked"}})

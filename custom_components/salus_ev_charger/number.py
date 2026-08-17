"""Number entities for the Salus EV Charger integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_THING_NAME, DOMAIN, MIN_CHARGING_CURRENT
from .coordinator import SalusDataUpdateCoordinator
from .shadow_helpers import flat

MAX_CURRENT_DESCRIPTION = NumberEntityDescription(
    key="max_charging_current",
    translation_key="max_charging_current",
    name="Max Charging Current",
    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    native_min_value=MIN_CHARGING_CURRENT,
    native_step=1,
    mode=NumberMode.SLIDER,
)

# Confirmed format from an observed shadow write: flat integer, not
# connector-scoped (unlike ChargingOn/OffPeakScheduleOn).
DESIRED_PROPERTY = "ep0:sCharger:SetStaticLoadManagement"
REPORTED_PROPERTY = "ep0:sCharger:StaticLoadManagement"
MAX_SUPPORTED_PROPERTY = "ep0:sCharger:MaxChargingCurrentSupported"
FALLBACK_MAX_CURRENT = 32


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the max charging current number entity from a config entry."""
    coordinator: SalusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SalusMaxCurrentNumber(coordinator, entry)])


class SalusMaxCurrentNumber(CoordinatorEntity[SalusDataUpdateCoordinator], NumberEntity):
    """Controls the charger's static load management max current."""

    entity_description = MAX_CURRENT_DESCRIPTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: SalusDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        thing_name = entry.data[CONF_THING_NAME]
        self._attr_unique_id = f"{thing_name}_{MAX_CURRENT_DESCRIPTION.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, thing_name)},
            name="Salus EV Charger",
            manufacturer="Salus",
        )

    @property
    def native_max_value(self) -> float:
        properties = self.coordinator.data or {}
        supported = flat(properties, MAX_SUPPORTED_PROPERTY)
        return float(supported) if supported else FALLBACK_MAX_CURRENT

    @property
    def native_value(self) -> float | None:
        value = flat(self.coordinator.data or {}, REPORTED_PROPERTY)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_desired({DESIRED_PROPERTY: int(value)})

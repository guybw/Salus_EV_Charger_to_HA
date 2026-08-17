"""Sensor entities for the Salus EV Charger integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_THING_NAME, DOMAIN
from .coordinator import SalusDataUpdateCoordinator
from .shadow_helpers import connector as _connector
from .shadow_helpers import flat as _flat
from .shadow_helpers import meter as _meter


@dataclass(frozen=True, kw_only=True)
class SalusSensorEntityDescription(SensorEntityDescription):
    """Sensor description with a function to pull its value out of shadow properties."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[SalusSensorEntityDescription, ...] = (
    SalusSensorEntityDescription(
        key="power",
        translation_key="power",
        name="Power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: _meter(p, "Power"),
    ),
    SalusSensorEntityDescription(
        key="energy",
        translation_key="energy",
        name="Energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda p: _meter(p, "Energy"),
    ),
    SalusSensorEntityDescription(
        key="charger_current",
        translation_key="charger_current",
        name="Charger Current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: _meter(p, "ChargerCurrentConsumption"),
    ),
    SalusSensorEntityDescription(
        key="household_current",
        translation_key="household_current",
        name="Household Current (CT Clamp)",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda p: _meter(p, "HouseholdCurrentConsumption"),
    ),
    SalusSensorEntityDescription(
        key="charging_status",
        translation_key="charging_status",
        name="Charging Status",
        value_fn=lambda p: _connector(p, "ep0:sCharger:ChargingStatus"),
    ),
    SalusSensorEntityDescription(
        key="availability",
        translation_key="availability",
        name="Availability",
        value_fn=lambda p: _connector(p, "ep0:sCharger:Availability"),
    ),
    SalusSensorEntityDescription(
        key="error_code",
        translation_key="error_code",
        name="Error Code",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: _flat(p, "ep0:sCharger:ErrorCode"),
    ),
    SalusSensorEntityDescription(
        key="error_info",
        translation_key="error_info",
        name="Error Info",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: _flat(p, "ep0:sCharger:ErrorInfo"),
    ),
    SalusSensorEntityDescription(
        key="software_version",
        translation_key="software_version",
        name="Firmware Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: _flat(p, "ep0:sCharger:SoftwareVersion"),
    ),
    SalusSensorEntityDescription(
        key="max_charging_current_supported",
        translation_key="max_charging_current_supported",
        name="Max Charging Current Supported",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: _flat(p, "ep0:sCharger:MaxChargingCurrentSupported"),
    ),
    SalusSensorEntityDescription(
        key="load_curtailment_status",
        translation_key="load_curtailment_status",
        name="Load Curtailment Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: _flat(p, "ep0:sCharger:LoadCurtailmentStatus"),
    ),
    SalusSensorEntityDescription(
        key="transaction_id",
        translation_key="transaction_id",
        name="Transaction ID",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: _connector(p, "ep0:sCharger:TransactionId"),
    ),
    SalusSensorEntityDescription(
        key="ota_status",
        translation_key="ota_status",
        name="OTA Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda p: _flat(p, "ep0:sCharger:OTAStatus_d"),
    ),
)

# Voltage isn't in the shadow schema today (see research.md), but the field
# is wired up so it starts working automatically if that ever changes --
# e.g. once actively charging, since OCPP testing showed it's only nonzero
# during an active transaction.
VOLTAGE_DESCRIPTION = SalusSensorEntityDescription(
    key="voltage",
    translation_key="voltage",
    name="Voltage",
    device_class=SensorDeviceClass.VOLTAGE,
    native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    state_class=SensorStateClass.MEASUREMENT,
    entity_registry_enabled_default=False,
    value_fn=lambda p: _meter(p, "Voltage"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Salus EV Charger sensors from a config entry."""
    coordinator: SalusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    descriptions = (*SENSOR_DESCRIPTIONS, VOLTAGE_DESCRIPTION)
    async_add_entities(
        SalusSensor(coordinator, entry, description) for description in descriptions
    )


class SalusSensor(CoordinatorEntity[SalusDataUpdateCoordinator], SensorEntity):
    """A single read-only sensor sourced from the charger's device shadow."""

    entity_description: SalusSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SalusDataUpdateCoordinator,
        entry: ConfigEntry,
        description: SalusSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        thing_name = entry.data[CONF_THING_NAME]
        self._attr_unique_id = f"{thing_name}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, thing_name)},
            name="Salus EV Charger",
            manufacturer="Salus",
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})

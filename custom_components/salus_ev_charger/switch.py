"""Switch entities for the Salus EV Charger integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_THING_NAME, DOMAIN
from .coordinator import SalusDataUpdateCoordinator
from .shadow_helpers import connector

CONNECTOR = "connector_1"


@dataclass(frozen=True, kw_only=True)
class SalusSwitchEntityDescription(SwitchEntityDescription):
    """Switch description: how to read current state and how to write a new one."""

    is_on_fn: Callable[[dict[str, Any]], bool | None]
    desired_property: str
    # Whether the write value needs to be wrapped as {"connector_1": value}
    # (confirmed for SetOffPeakScheduleOn from an observed shadow write;
    # inferred for SetChargingOn by analogy with its reported-state shape,
    # not yet directly confirmed -- verify the first time you use it).
    connector_scoped_write: bool = True


SWITCH_DESCRIPTIONS: tuple[SalusSwitchEntityDescription, ...] = (
    SalusSwitchEntityDescription(
        key="charging_on",
        translation_key="charging_on",
        name="Charging",
        is_on_fn=lambda p: bool(connector(p, "ep0:sCharger:ChargingOn")),
        desired_property="ep0:sCharger:SetChargingOn",
    ),
    SalusSwitchEntityDescription(
        key="off_peak_schedule_on",
        translation_key="off_peak_schedule_on",
        name="Off-Peak Schedule",
        is_on_fn=lambda p: bool(connector(p, "ep0:sCharger:OffPeakScheduleOn")),
        desired_property="ep0:sCharger:SetOffPeakScheduleOn",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Salus EV Charger switches from a config entry."""
    coordinator: SalusDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SalusSwitch(coordinator, entry, description) for description in SWITCH_DESCRIPTIONS
    )


class SalusSwitch(CoordinatorEntity[SalusDataUpdateCoordinator], SwitchEntity):
    """A control switch that writes to the charger's desired shadow state."""

    entity_description: SalusSwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SalusDataUpdateCoordinator,
        entry: ConfigEntry,
        description: SalusSwitchEntityDescription,
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
    def is_on(self) -> bool | None:
        return self.entity_description.is_on_fn(self.coordinator.data or {})

    def _desired_value(self, turn_on: bool) -> Any:
        value = 1 if turn_on else 0
        if self.entity_description.connector_scoped_write:
            return {CONNECTOR: value}
        return value

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_desired(
            {self.entity_description.desired_property: self._desired_value(True)}
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_desired(
            {self.entity_description.desired_property: self._desired_value(False)}
        )

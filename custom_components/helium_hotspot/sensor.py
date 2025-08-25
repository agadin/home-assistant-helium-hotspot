from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SENSOR_TYPES
from .coordinator import HeliumCoordinator

# Add this mapping (Material Design Icons):
ICON_MAP = {
    "tokens_earned_30d_hnt": "mdi:alpha-h-circle-outline",   # HNT-ish
    "proof_of_coverage_30d": "mdi:shield-check-outline",     # PoC
    "data_transfer_30d":     "mdi:database-arrow-right-outline",  # HNT from data xfer
    "carrier_offload":       "mdi:access-point-network",     # offload
    "helium_mobile":         "mdi:cellphone-wireless",       # mobile data
    "avg_daily_data":        "mdi:chart-line",               # avg data
    "avg_daily_users":       "mdi:account-group-outline",    # users
}

@dataclass
class HeliumDesc:
    key: str
    name: str
    unit: str | None

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator: HeliumCoordinator = hass.data[DOMAIN][entry.entry_id]

    descs: List[HeliumDesc] = [
        HeliumDesc(k, v[0], v[1]) for k, v in SENSOR_TYPES.items()
    ]

    entities: List[SensorEntity] = []
    for hotspot_id in coordinator._hotspots:
        for desc in descs:
            entities.append(HeliumSensor(coordinator, hotspot_id, desc, entry.entry_id))

    async_add_entities(entities, True)

class HeliumSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: HeliumCoordinator, hotspot_id: str, desc, entry_id: str):
        self.coordinator = coordinator
        self._hotspot_id = hotspot_id
        self._desc = desc
        self._entry_id = entry_id

        self._attr_unique_id = f"{entry_id}_{hotspot_id}_{desc.key}"
        self._attr_name = f"{hotspot_id} {desc.name}"

        # Unit from SENSOR_TYPES
        if desc.unit:
            self._attr_native_unit_of_measurement = desc.unit

        # NEW: per-sensor icon
        self._attr_icon = ICON_MAP.get(desc.key, "mdi:alpha-h-circle-outline")

    @property
    def device_info(self):
        data = self.coordinator.data.get(self._hotspot_id) or {}
        title = data.get("hotspot_name") or f"Helium Hotspot {self._hotspot_id}"
        return {
            "identifiers": {(DOMAIN, self._hotspot_id)},
            "name": title,
            "manufacturer": "Helium Mobile (community)",
            "configuration_url": data.get(
                "url") or f"https://world.helium.com/en/network/mobile/hotspot/{self._hotspot_id}",
        }

    @property
    def native_value(self):
        data: Dict[str, Any] = self.coordinator.data.get(self._hotspot_id) or {}
        return data.get(self._desc.key)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data.get(self._hotspot_id) or {}
        base = {
            "hotspot": self._hotspot_id,
            "url": data.get("url"),
            "hotspot_name": data.get("hotspot_name"),
            "hotspot_location": data.get("hotspot_location"),  # NEW
        }
        if self._desc.key == "tokens_earned_30d_hnt":
            base.update({
                "hnt_source": data.get("hnt_source"),
                "proof_of_coverage_30d": data.get("proof_of_coverage_30d"),
                "data_transfer_30d": data.get("data_transfer_30d"),
            })
        return base

    async def async_update(self):
        await self.coordinator.async_request_refresh()

    @property
    def should_poll(self) -> bool:
        return False

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))

from __future__ import annotations
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN, CONF_HOTSPOTS, CONF_UPDATE_INTERVAL_MINUTES
from .coordinator import HeliumCoordinator

PLATFORMS: Final = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hotspots_raw: str = entry.data.get(CONF_HOTSPOTS, "")
    hotspots = [h.strip() for h in hotspots_raw.split(",") if h.strip()]
    update_minutes = entry.options.get(CONF_UPDATE_INTERVAL_MINUTES) if entry.options else None

    coordinator = HeliumCoordinator(hass, hotspots, update_minutes)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coord: HeliumCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coord.async_close()
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

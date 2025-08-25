from __future__ import annotations

import voluptuous as vol
from typing import Any, Dict

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_HOTSPOTS,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
)

HOTSPOT_SCHEMA = vol.Schema({
    vol.Required(CONF_HOTSPOTS): str,  # comma-separated: e.g. "9982 # ,123456"
})

OPTIONS_SCHEMA = vol.Schema({
    vol.Optional(CONF_UPDATE_INTERVAL_MINUTES, default=DEFAULT_UPDATE_INTERVAL_MINUTES): vol.All(int, vol.Clamp(min=5, max=1440)),
})

def _normalize_hotspots(s: str) -> str:
    # keep only digits and commas/spaces, collapse
    parts = [p.strip() for p in s.split(",") if p.strip().isdigit()]
    return ",".join(parts)

class HeliumConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        errors: Dict[str, str] = {}
        if user_input is not None:
            hotspots = _normalize_hotspots(user_input[CONF_HOTSPOTS])
            if not hotspots:
                errors["base"] = "invalid_hotspots"
            else:
                await self.async_set_unique_id(f"{DOMAIN}_{hotspots}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Helium Hotspot(s) {hotspots}",
                    data={CONF_HOTSPOTS: hotspots},
                )
        return self.async_show_form(step_id="user", data_schema=HOTSPOT_SCHEMA, errors=errors)

    async def async_step_import(self, user_input: Dict[str, Any]) -> FlowResult:
        return await self.async_step_user(user_input)

    async def async_step_options(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_init(user_input)

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        return self.async_show_form(step_id="init", data_schema=OPTIONS_SCHEMA)

class HeliumOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        schema = vol.Schema({
            vol.Optional(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=self._entry.options.get(CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_UPDATE_INTERVAL_MINUTES)
            ): vol.All(int, vol.Clamp(min=5, max=1440)),
        })
        return self.async_show_form(step_id="init", data_schema=schema)

async def async_get_options_flow(config_entry):
    return HeliumOptionsFlow(config_entry)

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Dict, List

import httpx
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, USER_AGENT, DEFAULT_UPDATE_INTERVAL_MINUTES
from .parser import parse_hotspot_html

_HOTSPOT_URL_TMPL = "https://world.helium.com/en/network/mobile/hotspot/{hotspot}"
_LOGGER = logging.getLogger(__name__)


class HeliumCoordinator(DataUpdateCoordinator[Dict[str, dict]]):
    """Fetch & parse data for one or more hotspots."""

    def __init__(self, hass: HomeAssistant, hotspots: List[str], update_minutes: int | None):
        super().__init__(
            hass,
            _LOGGER,  # <-- use module logger
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(minutes=update_minutes or DEFAULT_UPDATE_INTERVAL_MINUTES),
        )
        self._hotspots = [h.strip() for h in hotspots if h.strip()]
        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            timeout=httpx.Timeout(20.0),
            follow_redirects=True,
        )

    async def _async_update_data(self) -> Dict[str, dict]:
        try:
            results: Dict[str, dict] = {}

            async def fetch_one(hsid: string):
                url = _HOTSPOT_URL_TMPL.format(hotspot=hsid)
                r = await self._client.get(url)
                r.raise_for_status()
                parsed = parse_hotspot_html(r.text)
                _LOGGER.debug("Hotspot %s parsed name=%s location=%s", hsid, parsed.get("hotspot_name"),
                              parsed.get("hotspot_location"))
                parsed["hotspot"] = hsid
                parsed["url"] = url
                results[hsid] = parsed

            await asyncio.gather(*(fetch_one(h) for h in self._hotspots))
            return results
        except Exception as err:
            raise UpdateFailed(str(err)) from err

    async def async_close(self):
        await self._client.aclose()

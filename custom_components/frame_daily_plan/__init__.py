"""The Frame Daily Plan integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import CLIENT_NAME, CONF_TOKEN, DOMAIN, SERVICE_RESTORE_ARTWORK, SERVICE_SHOW_PLAN, TV_TIMEOUT
from .coordinator import FrameCoordinator
from .tv import FrameTV

PLATFORMS = [Platform.BUTTON, Platform.IMAGE, Platform.SWITCH]
SERVICE_SCHEMA = vol.Schema({vol.Optional("device_id"): cv.string})

type FrameConfigEntry = ConfigEntry[FrameCoordinator]


def _coordinator_for_call(hass: HomeAssistant, call: ServiceCall) -> FrameCoordinator:
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
    if device_id := call.data.get("device_id"):
        device = dr.async_get(hass).async_get(device_id)
        entries = [e for e in entries if device and e.entry_id in device.config_entries]
    if not entries:
        raise HomeAssistantError("No Frame Daily Plan device matches this call")
    return entries[0].runtime_data


async def async_setup_entry(hass: HomeAssistant, entry: FrameConfigEntry) -> bool:
    tv = FrameTV(entry.data[CONF_HOST], entry.data[CONF_TOKEN], CLIENT_NAME, TV_TIMEOUT)
    coordinator = FrameCoordinator(hass, entry, tv)
    await coordinator.async_load_state()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_show_plan(call: ServiceCall) -> None:
        await _coordinator_for_call(hass, call).async_show_plan()

    async def handle_restore(call: ServiceCall) -> None:
        await _coordinator_for_call(hass, call).async_restore_artwork()

    hass.services.async_register(DOMAIN, SERVICE_SHOW_PLAN, handle_show_plan, schema=SERVICE_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_RESTORE_ARTWORK, handle_restore, schema=SERVICE_SCHEMA)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FrameConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and not any(e.entry_id != entry.entry_id and e.state is ConfigEntryState.LOADED
                             for e in hass.config_entries.async_entries(DOMAIN)):
        hass.services.async_remove(DOMAIN, SERVICE_SHOW_PLAN)
        hass.services.async_remove(DOMAIN, SERVICE_RESTORE_ARTWORK)
    return unload_ok

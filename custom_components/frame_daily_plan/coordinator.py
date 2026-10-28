"""Coordinator: polls Art Mode, owns the TV client, plan state, and the last rendered image."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import plan
from .const import DOMAIN, STORAGE_VERSION, UPDATE_INTERVAL_SECONDS
from .tv import FrameTV, FrameTVError, new_state

_LOGGER = logging.getLogger(__name__)


class FrameCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """One Frame TV."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, tv: FrameTV) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry,
                         update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS))
        self.entry = entry
        self.tv = tv
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}")
        self.state: dict[str, Any] = new_state()
        self.last_plan: bytes | None = None
        self.last_plan_at = None

    async def async_load_state(self) -> None:
        stored = await self._store.async_load()
        if stored:
            self.state.update(stored)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            art_mode = await self.hass.async_add_executor_job(self.tv.art_mode)
        except FrameTVError as err:
            raise UpdateFailed(str(err)) from err
        return {"art_mode": art_mode}

    async def async_set_art_mode(self, on: bool) -> None:
        try:
            await self.hass.async_add_executor_job(self.tv.set_art_mode, on)
        except FrameTVError as err:
            raise HomeAssistantError(f"Frame TV: {err}") from err
        await self.async_request_refresh()

    async def async_show_plan(self) -> None:
        jpeg = await plan.async_render(self.hass, dict(self.entry.options))
        self.last_plan, self.last_plan_at = jpeg, dt_util.utcnow()
        self.async_update_listeners()
        try:
            self.state = await self.hass.async_add_executor_job(self.tv.show_image, jpeg, self.state)
        except FrameTVError as err:
            raise HomeAssistantError(f"Frame TV: {err}") from err
        finally:
            await self._store.async_save(self.state)
        _LOGGER.info("Plan shown as %s", self.state["plan_ids"][-1:] or "?")

    async def async_restore_artwork(self) -> None:
        try:
            self.state = await self.hass.async_add_executor_job(self.tv.restore, self.state)
        except FrameTVError as err:
            raise HomeAssistantError(f"Frame TV: {err}") from err
        finally:
            await self._store.async_save(self.state)
        _LOGGER.info("Artwork restored")

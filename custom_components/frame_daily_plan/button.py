"""Show plan / restore artwork buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import FrameEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities([
        FrameButton(coordinator, "show_plan", coordinator.async_show_plan),
        FrameButton(coordinator, "restore_artwork", coordinator.async_restore_artwork),
    ])


class FrameButton(FrameEntity, ButtonEntity):
    def __init__(self, coordinator, key: str, action) -> None:
        super().__init__(coordinator, key)
        self._action = action

    async def async_press(self) -> None:
        await self._action()

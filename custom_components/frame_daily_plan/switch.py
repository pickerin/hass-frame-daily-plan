"""Art Mode switch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import FrameEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([ArtModeSwitch(entry.runtime_data)])


class ArtModeSwitch(FrameEntity, SwitchEntity):
    """On = the Frame shows art, off = it shows TV / an HDMI source."""

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "art_mode")

    @property
    def is_on(self) -> bool | None:
        return (self.coordinator.data or {}).get("art_mode")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_art_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_art_mode(False)

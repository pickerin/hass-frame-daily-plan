"""The last rendered plan, as an image entity (dashboard preview)."""

from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import FrameEntity


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([PlanImage(hass, entry.runtime_data)])


class PlanImage(FrameEntity, ImageEntity):
    _attr_content_type = "image/jpeg"

    def __init__(self, hass: HomeAssistant, coordinator) -> None:
        FrameEntity.__init__(self, coordinator, "plan")
        ImageEntity.__init__(self, hass)

    @property
    def image_last_updated(self):
        return self.coordinator.last_plan_at

    @property
    def available(self) -> bool:
        return True  # the preview stays viewable while the TV sleeps

    async def async_image(self) -> bytes | None:
        return self.coordinator.last_plan

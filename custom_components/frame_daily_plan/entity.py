"""Base entity for Frame Daily Plan."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FrameCoordinator


class FrameEntity(CoordinatorEntity[FrameCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: FrameCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.entry
        uid = entry.unique_id or entry.entry_id
        self._attr_translation_key = key
        self._attr_unique_id = f"{uid}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            connections={(CONNECTION_NETWORK_MAC, entry.unique_id)} if ":" in (entry.unique_id or "") else set(),
            name=entry.title,
            manufacturer="Samsung",
            model=entry.data.get("model"),
        )

"""Gather today's data from Home Assistant entities and render the plan."""

from __future__ import annotations

import datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import logic, render
from .const import CONF_CALENDARS, CONF_CLOCK, CONF_TODO_LISTS, CONF_WEATHER, CONF_WEEK_START, DEFAULT_CLOCK, DEFAULT_WEEK_START, PALETTE

_LOGGER = logging.getLogger(__name__)


async def _call(hass: HomeAssistant, domain: str, service: str, data: dict[str, Any]) -> dict[str, Any]:
    try:
        return await hass.services.async_call(domain, service, data, blocking=True, return_response=True) or {}
    except Exception as err:  # noqa: BLE001  one broken source must not stop the plan
        _LOGGER.warning("%s.%s failed: %s", domain, service, err)
        return {}


async def async_build(hass: HomeAssistant, options: dict[str, Any]) -> dict[str, Any]:
    now = dt_util.now()
    tz = now.tzinfo
    today = now.date()
    tomorrow = today + datetime.timedelta(days=1)
    clock = options.get(CONF_CLOCK, DEFAULT_CLOCK)
    calendars = list(options.get(CONF_CALENDARS) or [])
    todo_lists = list(options.get(CONF_TODO_LISTS) or [])
    weather_entity = options.get(CONF_WEATHER)

    events_today: list[dict[str, Any]] = []
    events_tomorrow: list[dict[str, Any]] = []
    if calendars:
        start = datetime.datetime.combine(today, datetime.time(0), tz)
        resp = await _call(hass, "calendar", "get_events", {
            "entity_id": calendars, "start_date_time": start.isoformat(),
            "end_date_time": (start + datetime.timedelta(days=2)).isoformat()})
        events_today = logic.events_for_day(resp, calendars, today, tz, now, clock, PALETTE)
        events_tomorrow = logic.events_for_day(resp, calendars, tomorrow, tz, now, clock, PALETTE)

    todos: list[str] = []
    if todo_lists:
        resp = await _call(hass, "todo", "get_items", {"entity_id": todo_lists, "status": ["needs_action"]})
        todos = logic.todos(resp, todo_lists)

    weather = None
    if weather_entity:
        resp = await _call(hass, "weather", "get_forecasts", {"entity_id": weather_entity, "type": "daily"})
        forecast = ((resp.get(weather_entity) or {}).get("forecast") or [None])[0]
        weather = logic.weather(forecast, str(hass.config.units.temperature_unit))

    return {"date": today.isoformat(), "today": events_today, "tomorrow": events_tomorrow, "todos": todos,
            "weather": weather, "week_start": options.get(CONF_WEEK_START, DEFAULT_WEEK_START)}


async def async_render(hass: HomeAssistant, options: dict[str, Any]) -> bytes:
    day = await async_build(hass, options)
    return await hass.async_add_executor_job(render.render, day)

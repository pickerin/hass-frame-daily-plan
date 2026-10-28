"""Config flow: TV address, then the TV's Allow prompt. Options: what goes on the plan."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector, EntitySelectorConfig, SelectSelector, SelectSelectorConfig, SelectSelectorMode)

from . import tv
from .const import (
    CLIENT_NAME, CONF_CALENDARS, CONF_CLOCK, CONF_TODO_LISTS, CONF_TOKEN, CONF_WEATHER, CONF_WEEK_START,
    DEFAULT_CLOCK, DEFAULT_WEEK_START, DOMAIN, PAIR_TIMEOUT, TV_TIMEOUT)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


def _select(key: str, options: list[str]) -> SelectSelector:
    return SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN, translation_key=key))


class FrameConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._host = ""
        self._info: dict[str, Any] = {}
        self._pair_task: asyncio.Task[str] | None = None
        self._token: str | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._host = user_input[CONF_HOST].strip()
            try:
                self._info = await self.hass.async_add_executor_job(tv.device_info, self._host, TV_TIMEOUT)
            except tv.FrameTVError:
                errors["base"] = "cannot_connect"
            else:
                if self._info.get("FrameTVSupport") != "true":
                    errors["base"] = "not_a_frame"
                else:
                    await self.async_set_unique_id(self._info.get("wifiMac") or self._info.get("id") or self._host)
                    self._abort_if_unique_id_configured(updates={CONF_HOST: self._host})
                    return await self.async_step_pair()
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

    async def async_step_pair(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._pair_task is None:
            self._pair_task = self.hass.async_create_task(
                self.hass.async_add_executor_job(tv.pair, self._host, CLIENT_NAME, PAIR_TIMEOUT))
        if not self._pair_task.done():
            return self.async_show_progress(step_id="pair", progress_action="pair", progress_task=self._pair_task)
        try:
            self._token = self._pair_task.result()
        except tv.FrameTVError as err:
            _LOGGER.warning("Pairing with %s failed: %s", self._host, err)
            self._pair_task = None
            return self.async_show_progress_done(next_step_id="pair_failed")
        return self.async_show_progress_done(next_step_id="finish")

    async def async_step_pair_failed(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_pair()
        return self.async_show_form(step_id="pair_failed")

    async def async_step_finish(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        name = (self._info.get("name") or "Frame TV").replace("[TV]", "").strip()
        return self.async_create_entry(
            title=name,
            data={CONF_HOST: self._host, CONF_TOKEN: self._token, "model": self._info.get("modelName")},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return FrameOptionsFlow()


class FrameOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        o = self.config_entry.options
        schema = vol.Schema({
            vol.Optional(CONF_CALENDARS, default=list(o.get(CONF_CALENDARS) or [])):
                EntitySelector(EntitySelectorConfig(domain="calendar", multiple=True)),
            vol.Optional(CONF_TODO_LISTS, default=list(o.get(CONF_TODO_LISTS) or [])):
                EntitySelector(EntitySelectorConfig(domain="todo", multiple=True)),
            vol.Optional(CONF_WEATHER, description={"suggested_value": o.get(CONF_WEATHER)}):
                EntitySelector(EntitySelectorConfig(domain="weather")),
            vol.Required(CONF_CLOCK, default=o.get(CONF_CLOCK, DEFAULT_CLOCK)): _select(CONF_CLOCK, ["12", "24"]),
            vol.Required(CONF_WEEK_START, default=o.get(CONF_WEEK_START, DEFAULT_WEEK_START)):
                _select(CONF_WEEK_START, ["monday", "sunday"]),
        })
        return self.async_show_form(step_id="init", data_schema=schema)

"""Schakelaar 'Ask meter for current': standaard uit, ook na een herstart."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN

MEETWAARDEN = ("i_a", "i_b", "i_c", "_pbase_a", "_pbase_b", "_pbase_c")


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([AskSwitch(entry, hass.data[DOMAIN][entry.entry_id])])


class AskSwitch(SwitchEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = "Ask meter for current"
    _attr_icon = "mdi:lightning-bolt-circle"

    def __init__(self, entry, rt):
        self._rt = rt
        self._attr_unique_id = f"{entry.entry_id}_ask"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)})

    @property
    def is_on(self):
        return self._rt["bus"].ask

    async def async_turn_on(self, **kwargs):
        self._rt["bus"].ask = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._rt["bus"].ask = False
        # gemeten I wordt oud: weg ermee, terug naar |P| / U (U blijft elke minuut vers)
        for k in MEETWAARDEN:
            self._rt["state"].pop(k, None)
        async_dispatcher_send(self.hass, self._rt["signal"])
        self.async_write_ha_state()

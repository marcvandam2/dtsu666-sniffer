from __future__ import annotations

import time

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, EXTRA, JUMP, MIN_WRITE_S, REGS


async def async_setup_entry(hass, entry, async_add_entities):
    rt = hass.data[DOMAIN][entry.entry_id]
    device = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name="DTSU666",
                        manufacturer="Chint", model="DTSU666 (sniffed)")
    async_add_entities(Dtsu666Sensor(entry, rt, device, *spec) for spec in [*REGS.values(), *EXTRA])


class Dtsu666Sensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry, rt, device, key, name, unit, _factor, dclass, sclass):
        self._rt, self._key = rt, key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = device
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = SensorDeviceClass(dclass)
        self._attr_state_class = SensorStateClass(sclass)
        # meterresolutie: 0,1 V, 0,001 A, 0,1 W, 0,001 PF, 0,01 Hz, 0,01 kWh
        self._attr_suggested_display_precision = {
            "voltage": 1, "current": 2, "power": 0, "reactive_power": 0,
            "power_factor": 3, "frequency": 2, "energy": 2,
        }.get(dclass)
        self._jump = JUMP.get(dclass)
        self._last_t = 0.0
        self._last_v = None
        self._last_avail = None

    async def async_added_to_hass(self):
        self.async_on_remove(async_dispatcher_connect(
            self.hass, self._rt["signal"], self._update))

    @callback
    def _update(self):
        # Hooguit eens per MIN_WRITE_S naar HA (en dus naar de database), behalve bij
        # een sprong van minstens JUMP: dan meteen (een doorstromer die aanslaat).
        v, now, avail = self.native_value, time.monotonic(), self.available
        if avail == self._last_avail and v == self._last_v:
            return
        if (avail == self._last_avail and now - self._last_t < MIN_WRITE_S
                and not (self._jump and v is not None and self._last_v is not None
                         and abs(v - self._last_v) >= self._jump)):
            return
        self._last_t, self._last_v, self._last_avail = now, v, avail
        self.async_write_ha_state()

    @property
    def available(self):
        return self._key in self._rt["state"]

    @property
    def native_value(self):
        return self._rt["state"].get(self._key)

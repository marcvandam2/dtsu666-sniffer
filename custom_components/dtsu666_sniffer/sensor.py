from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, EXTRA, REGS


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

    async def async_added_to_hass(self):
        self.async_on_remove(async_dispatcher_connect(
            self.hass, self._rt["signal"], self.async_write_ha_state))

    @property
    def available(self):
        return self._key in self._rt["state"]

    @property
    def native_value(self):
        return self._rt["state"].get(self._key)

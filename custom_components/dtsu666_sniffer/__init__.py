"""DTSU666 Sniffer: meter tussen Deye en Chint DTSU666 meelezen via een RS485-ETH-gateway."""
from __future__ import annotations

import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .bus import Dtsu666Bus
from .const import (CONF_INTERVAL, CONF_MODE, CONF_SLAVE, CONF_U, CONF_U_INTERVAL, DOMAIN, U_DEFAULT,
                    U_MAX_AGE, U_NOMINAAL)

PLATFORMS = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    cfg = {**entry.data, **entry.options}
    state: dict = {}
    signal = f"{DOMAIN}_{entry.entry_id}"

    u_entities = [cfg.get(k, u) for k, u in zip(CONF_U, U_DEFAULT)]

    def deye_volt(ent):
        st = hass.states.get(ent) if ent else None
        try:
            if st and time.time() - getattr(st, "last_reported", st.last_updated).timestamp() <= U_MAX_AGE:
                return float(st.state)
        except ValueError:
            pass
        return None

    def on_data(data):
        state.update(data)
        # Stroom per fase. Zelf meevragen aan: de laatst gemeten stroom, bijgewerkt
        # met de vermogensverandering sinds die meting (de Deye leest P ~7x per s):
        # I = I_meting + (|P| - |P_meting|) / U. Uit: |P| / U met de spanning van de
        # meter (elke minuut gevraagd), anders die van de Deye, anders 230 V; een
        # ondergrens, want PF < 1 geeft meer stroom.
        for f, ent in zip("abc", u_entities):
            p, i, u = f"p_{f}", f"i_{f}", f"u_{f}"
            if i in data and p in state:
                state[f"_pbase_{f}"] = abs(state[p])
            if p not in state:
                continue
            volt = state.get(u) or deye_volt(ent) or U_NOMINAAL
            if i in state and f"_pbase_{f}" in state:
                snel = state[i] + (abs(state[p]) - state[f"_pbase_{f}"]) / volt
            else:
                snel = abs(state[p]) / volt
            state[f"i_snel_{f}"] = round(max(snel, 0.0), 2)
        snel = [state[k] for k in ("i_snel_a", "i_snel_b", "i_snel_c") if k in state]
        if snel:
            state["i_max"] = max(snel)
        async_dispatcher_send(hass, signal)

    bus = Dtsu666Bus(cfg[CONF_HOST], cfg[CONF_PORT], cfg[CONF_MODE],
                     cfg[CONF_SLAVE], cfg[CONF_INTERVAL], on_data, cfg.get(CONF_U_INTERVAL, 60))
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"bus": bus, "state": state, "signal": signal}
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    bus.start(hass)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await hass.data[DOMAIN].pop(entry.entry_id)["bus"].stop()
    return ok

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback

from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import (CONF_INTERVAL, CONF_MODE, CONF_SLAVE, CONF_U, CONF_U_INTERVAL, DOMAIN, MODE_POLL,
                    MODE_SNIFF, U_DEFAULT)


def _schema(d):
    return vol.Schema({
        vol.Required(CONF_HOST, default=d.get(CONF_HOST, "")): str,
        vol.Required(CONF_PORT, default=d.get(CONF_PORT, 502)): int,
        vol.Required(CONF_MODE, default=d.get(CONF_MODE, MODE_SNIFF)): vol.In([MODE_SNIFF, MODE_POLL]),
        vol.Required(CONF_SLAVE, default=d.get(CONF_SLAVE, 1)): vol.All(int, vol.Range(1, 247)),
        vol.Required(CONF_INTERVAL, default=d.get(CONF_INTERVAL, 1) or 1): vol.All(int, vol.Range(1, 3600)),
        vol.Required(CONF_U_INTERVAL, default=d.get(CONF_U_INTERVAL, 60)): vol.All(int, vol.Range(0, 3600)),
        **{vol.Optional(k, default=d.get(k, u)): EntitySelector(EntitySelectorConfig(domain="sensor"))
           for k, u in zip(CONF_U, U_DEFAULT)},
    })


class Dtsu666Flow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=f"DTSU666 {user_input[CONF_HOST]}", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(entry):
        return Dtsu666Options()


class Dtsu666Options(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        cfg = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(cfg))

"""Config flow for the Mitsubishi Heavy IR Climate integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_PROTOCOL,
    CONF_REMOTE_ENTITY,
    DEFAULT_NAME,
    DOMAIN,
    PROTOCOL_MHI_88,
    PROTOCOLS,
)
from .helpers import discover_remote_entities


def _protocol_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(value=key, label=label)
                for key, label in PROTOCOLS.items()
            ],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


class MitsubishiHeavyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mitsubishi Heavy IR Climate."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return MitsubishiHeavyOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step (single `protocol` parameter by default)."""
        ir_remotes, fallback_remotes = discover_remote_entities(self.hass)
        candidates = ir_remotes or fallback_remotes

        if user_input is not None:
            protocol = user_input[CONF_PROTOCOL]
            remote_entity = user_input.get(CONF_REMOTE_ENTITY)
            if not remote_entity and len(candidates) == 1:
                remote_entity = candidates[0]

            data: dict[str, Any] = {CONF_PROTOCOL: protocol}
            if remote_entity:
                data[CONF_REMOTE_ENTITY] = remote_entity

            title = DEFAULT_NAME
            if remote_entity and len(candidates) > 1:
                short_remote = remote_entity.split(".", 1)[-1].replace("_", " ").title()
                title = f"{DEFAULT_NAME} ({short_remote})"

            return self.async_create_entry(title=title, data=data)

        schema_fields: dict[Any, Any] = {
            vol.Required(CONF_PROTOCOL, default=PROTOCOL_MHI_88): _protocol_selector(),
        }
        # Only prompt for remote_entity when multiple IR remotes exist on the instance
        if len(candidates) > 1:
            schema_fields[
                vol.Required(CONF_REMOTE_ENTITY, default=candidates[0])
            ] = EntitySelector(EntitySelectorConfig(domain="remote"))

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_fields),
        )


class MitsubishiHeavyOptionsFlow(OptionsFlow):
    """Handle options updates for Mitsubishi Heavy IR Climate."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_protocol = self.config_entry.options.get(
            CONF_PROTOCOL,
            self.config_entry.data.get(CONF_PROTOCOL, PROTOCOL_MHI_88),
        )
        current_remote = self.config_entry.options.get(
            CONF_REMOTE_ENTITY,
            self.config_entry.data.get(CONF_REMOTE_ENTITY),
        )

        schema_fields: dict[Any, Any] = {
            vol.Required(CONF_PROTOCOL, default=current_protocol): _protocol_selector(),
        }

        ir_remotes, fallback_remotes = discover_remote_entities(self.hass)
        candidates = ir_remotes or fallback_remotes
        if candidates or current_remote:
            default_remote = current_remote or (candidates[0] if candidates else vol.UNDEFINED)
            schema_fields[
                vol.Optional(CONF_REMOTE_ENTITY, default=default_remote)
            ] = EntitySelector(EntitySelectorConfig(domain="remote"))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_fields),
        )

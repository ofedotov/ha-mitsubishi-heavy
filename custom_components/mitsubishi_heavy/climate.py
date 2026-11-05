"""Climate platform for Mitsubishi Heavy Industries IR AC units."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    PLATFORM_SCHEMA as CLIMATE_PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.remote import ATTR_COMMAND, DOMAIN as REMOTE_DOMAIN, SERVICE_SEND_COMMAND
from homeassistant.const import ATTR_ENTITY_ID, ATTR_TEMPERATURE, CONF_NAME, CONF_UNIQUE_ID, UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_PROTOCOL,
    CONF_REMOTE_ENTITY,
    DEFAULT_NAME,
    DEFAULT_TEMP,
    DOMAIN,
    MAX_TEMP,
    MIN_TEMP,
    PROTOCOLS,
    TEMP_STEP,
)
from .helpers import resolve_default_remote_entity
from .protocol import (
    FAN_AUTO,
    MODE_COOL,
    MODE_DRY,
    MODE_FAN_ONLY,
    MODE_HEAT,
    MODE_HEAT_COOL,
    PRESET_NONE,
    PROTOCOL_CAPABILITIES,
    ACState,
    encode_broadlink_command,
    encode_frame_bytes,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

_HVAC_TO_PROTO_MODE: dict[HVACMode, str] = {
    HVACMode.HEAT_COOL: MODE_HEAT_COOL,
    HVACMode.COOL: MODE_COOL,
    HVACMode.HEAT: MODE_HEAT,
    HVACMode.DRY: MODE_DRY,
    HVACMode.FAN_ONLY: MODE_FAN_ONLY,
}

_ATTR_LAST_ACTIVE_MODE = "last_active_hvac_mode"
_ATTR_LAST_FRAME_HEX = "last_ir_frame_hex"

# YAML configuration: `protocol` is the ONLY required parameter
PLATFORM_SCHEMA = CLIMATE_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_PROTOCOL): vol.In(list(PROTOCOLS)),
        vol.Optional(CONF_REMOTE_ENTITY): cv.entity_id,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Mitsubishi Heavy IR Climate from a UI config entry."""
    protocol: str = entry.options.get(CONF_PROTOCOL, entry.data[CONF_PROTOCOL])
    remote_entity: str | None = entry.options.get(
        CONF_REMOTE_ENTITY, entry.data.get(CONF_REMOTE_ENTITY)
    )

    async_add_entities(
        [
            MitsubishiHeavyClimate(
                protocol=protocol,
                remote_entity=remote_entity,
                name=None,
                unique_id=entry.entry_id,
                device_info=DeviceInfo(
                    identifiers={(DOMAIN, entry.entry_id)},
                    manufacturer="Mitsubishi Heavy Industries",
                    model=PROTOCOLS.get(protocol, protocol),
                    name=entry.title or DEFAULT_NAME,
                ),
            )
        ]
    )


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Mitsubishi Heavy IR Climate from YAML (`protocol` only)."""
    protocol: str = config[CONF_PROTOCOL]
    remote_entity: str | None = config.get(CONF_REMOTE_ENTITY)
    name: str = config[CONF_NAME]
    unique_id: str | None = config.get(CONF_UNIQUE_ID) or f"{DOMAIN}_{protocol}"

    async_add_entities(
        [
            MitsubishiHeavyClimate(
                protocol=protocol,
                remote_entity=remote_entity,
                name=name,
                unique_id=unique_id,
                device_info=None,
            )
        ]
    )


class MitsubishiHeavyClimate(ClimateEntity, RestoreEntity):
    """Representation of a Mitsubishi Heavy Industries IR Air Conditioner."""

    _attr_assumed_state = True
    _attr_should_poll = False
    _attr_translation_key = "mitsubishi_heavy"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = float(MIN_TEMP)
    _attr_max_temp = float(MAX_TEMP)
    _attr_target_temperature_step = TEMP_STEP
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT_COOL,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        protocol: str,
        remote_entity: str | None,
        name: str | None,
        unique_id: str | None,
        device_info: DeviceInfo | None,
    ) -> None:
        """Initialize the Mitsubishi Heavy IR Climate entity."""
        self._protocol = protocol
        self._configured_remote_entity = remote_entity
        self._caps = PROTOCOL_CAPABILITIES[protocol]

        if device_info is not None:
            self._attr_has_entity_name = True
            self._attr_name = None
            self._attr_device_info = device_info
        else:
            self._attr_name = name or DEFAULT_NAME

        self._attr_unique_id = unique_id

        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        self._attr_fan_modes = list(self._caps.fan_modes)

        if self._caps.swing_v_modes:
            features |= ClimateEntityFeature.SWING_MODE
            self._attr_swing_modes = list(self._caps.swing_v_modes)

        swing_h_flag = getattr(ClimateEntityFeature, "SWING_HORIZONTAL_MODE", 0)
        if self._caps.swing_h_modes and swing_h_flag:
            features |= swing_h_flag
            self._attr_swing_horizontal_modes = list(self._caps.swing_h_modes)

        if self._caps.preset_modes:
            features |= ClimateEntityFeature.PRESET_MODE
            self._attr_preset_modes = list(self._caps.preset_modes)

        self._attr_supported_features = features

        # Current state
        self._attr_hvac_mode: HVACMode = HVACMode.OFF
        self._last_active_hvac_mode: HVACMode = HVACMode.COOL
        self._attr_target_temperature: float = float(DEFAULT_TEMP)
        self._attr_fan_mode: str = FAN_AUTO
        self._attr_swing_mode: str | None = (
            self._caps.default_swing_v if self._caps.swing_v_modes else None
        )
        self._attr_swing_horizontal_mode: str | None = (
            self._caps.default_swing_h if self._caps.swing_h_modes else None
        )
        self._attr_preset_mode: str | None = (
            PRESET_NONE if self._caps.preset_modes else None
        )
        self._last_frame_hex: str | None = None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return protocol & transmission diagnostics."""
        remote_id = self._configured_remote_entity or (
            resolve_default_remote_entity(self.hass) if self.hass else None
        )
        return {
            CONF_PROTOCOL: self._protocol,
            CONF_REMOTE_ENTITY: remote_id,
            _ATTR_LAST_ACTIVE_MODE: self._last_active_hvac_mode.value,
            _ATTR_LAST_FRAME_HEX: self._last_frame_hex,
        }

    async def async_added_to_hass(self) -> None:
        """Restore previous climate state upon Home Assistant startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None:
            return

        if last_state.state in {m.value for m in self._attr_hvac_modes}:
            self._attr_hvac_mode = HVACMode(last_state.state)
            if self._attr_hvac_mode != HVACMode.OFF:
                self._last_active_hvac_mode = self._attr_hvac_mode

        attrs = last_state.attributes
        saved_active = attrs.get(_ATTR_LAST_ACTIVE_MODE)
        if saved_active in {m.value for m in self._attr_hvac_modes if m != HVACMode.OFF}:
            self._last_active_hvac_mode = HVACMode(saved_active)

        temp = attrs.get(ATTR_TEMPERATURE)
        if temp is not None:
            try:
                self._attr_target_temperature = float(
                    max(MIN_TEMP, min(MAX_TEMP, round(float(temp))))
                )
            except (TypeError, ValueError):
                pass

        fan = attrs.get("fan_mode")
        if fan in self._caps.fan_modes:
            self._attr_fan_mode = fan

        swing_v = attrs.get("swing_mode")
        if self._caps.swing_v_modes and swing_v in self._caps.swing_v_modes:
            self._attr_swing_mode = swing_v

        swing_h = attrs.get("swing_horizontal_mode")
        if self._caps.swing_h_modes and swing_h in self._caps.swing_h_modes:
            self._attr_swing_horizontal_mode = swing_h

        preset = attrs.get("preset_mode")
        if self._caps.preset_modes and preset in self._caps.preset_modes:
            self._attr_preset_mode = preset

        if attrs.get(_ATTR_LAST_FRAME_HEX):
            self._last_frame_hex = attrs[_ATTR_LAST_FRAME_HEX]

    def _build_ac_state(self) -> ACState:
        """Construct the logical ACState snapshot for the protocol encoder."""
        is_on = self._attr_hvac_mode != HVACMode.OFF
        active_hvac = self._attr_hvac_mode if is_on else self._last_active_hvac_mode
        proto_mode = _HVAC_TO_PROTO_MODE.get(active_hvac, MODE_COOL)
        return ACState(
            power=is_on,
            mode=proto_mode,
            temperature=int(round(self._attr_target_temperature or DEFAULT_TEMP)),
            fan=self._attr_fan_mode or FAN_AUTO,
            swing_v=self._attr_swing_mode or self._caps.default_swing_v,
            swing_h=self._attr_swing_horizontal_mode or self._caps.default_swing_h,
            preset=self._attr_preset_mode or PRESET_NONE,
        )

    async def _async_transmit_state(self) -> None:
        """Encode the current ACState and send it via Home Assistant's `remote` entity."""
        remote_entity = self._configured_remote_entity or resolve_default_remote_entity(
            self.hass
        )
        if not remote_entity:
            raise HomeAssistantError(
                "No IR `remote` entity found in Home Assistant. "
                "Add a Broadlink/IR remote integration first."
            )

        ac_state = self._build_ac_state()
        frame = encode_frame_bytes(self._protocol, ac_state)
        command = encode_broadlink_command(self._protocol, ac_state)
        self._last_frame_hex = frame.hex(" ")

        _LOGGER.debug(
            "Sending %s frame (%s) via %s",
            self._protocol,
            self._last_frame_hex,
            remote_entity,
        )
        await self.hass.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_SEND_COMMAND,
            {
                ATTR_ENTITY_ID: remote_entity,
                ATTR_COMMAND: command,
            },
            blocking=True,
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode and transmit."""
        if hvac_mode not in self._attr_hvac_modes:
            raise HomeAssistantError(f"Unsupported HVAC mode: {hvac_mode}")

        self._attr_hvac_mode = hvac_mode
        if hvac_mode != HVACMode.OFF:
            self._last_active_hvac_mode = hvac_mode

        await self._async_transmit_state()
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn the AC unit on using the last active HVAC mode."""
        await self.async_set_hvac_mode(self._last_active_hvac_mode)

    async def async_turn_off(self) -> None:
        """Turn the AC unit off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature (and optional simultaneous HVAC mode)."""
        hvac_mode: HVACMode | None = kwargs.get(ATTR_HVAC_MODE)
        if hvac_mode is not None:
            if hvac_mode not in self._attr_hvac_modes:
                raise HomeAssistantError(f"Unsupported HVAC mode: {hvac_mode}")
            self._attr_hvac_mode = hvac_mode
            if hvac_mode != HVACMode.OFF:
                self._last_active_hvac_mode = hvac_mode

        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            self._attr_target_temperature = float(
                max(MIN_TEMP, min(MAX_TEMP, int(round(float(temp)))))
            )

        if self._attr_hvac_mode != HVACMode.OFF or hvac_mode == HVACMode.OFF:
            await self._async_transmit_state()
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan speed."""
        if fan_mode not in self._caps.fan_modes:
            raise HomeAssistantError(f"Unsupported fan mode: {fan_mode}")
        self._attr_fan_mode = fan_mode
        # Selecting a manual fan speed clears fan-override presets (Boost / Eco)
        if self._attr_preset_mode in ("boost", "eco"):
            self._attr_preset_mode = PRESET_NONE
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._async_transmit_state()
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set vertical louver swing mode."""
        if swing_mode not in self._caps.swing_v_modes:
            raise HomeAssistantError(f"Unsupported vertical swing mode: {swing_mode}")
        self._attr_swing_mode = swing_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._async_transmit_state()
        self.async_write_ha_state()

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode: str) -> None:
        """Set horizontal louver / 3D Auto mode."""
        if swing_horizontal_mode not in self._caps.swing_h_modes:
            raise HomeAssistantError(
                f"Unsupported horizontal swing mode: {swing_horizontal_mode}"
            )
        self._attr_swing_horizontal_mode = swing_horizontal_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._async_transmit_state()
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode (None, Boost/Hi-Power, Eco, Silent, Sleep)."""
        if preset_mode not in self._caps.preset_modes:
            raise HomeAssistantError(f"Unsupported preset mode: {preset_mode}")
        self._attr_preset_mode = preset_mode
        if self._attr_hvac_mode != HVACMode.OFF:
            await self._async_transmit_state()
        self.async_write_ha_state()

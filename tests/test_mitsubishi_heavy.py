"""Unit tests for the Mitsubishi Heavy IR Climate custom component."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from enum import IntFlag, StrEnum
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent
COMP_DIR = ROOT_DIR / "custom_components" / "mitsubishi_heavy"


# ---------------------------------------------------------------------------
# Lightweight Home Assistant Stubs for Local Testing (Python 3.15 without HA)
# ---------------------------------------------------------------------------
def _install_ha_stubs() -> None:
    if "homeassistant" in sys.modules:
        return

    ha = ModuleType("homeassistant")

    # homeassistant.const
    ha_const = ModuleType("homeassistant.const")

    class Platform(StrEnum):
        CLIMATE = "climate"

    class UnitOfTemperature(StrEnum):
        CELSIUS = "°C"

    ha_const.Platform = Platform
    ha_const.UnitOfTemperature = UnitOfTemperature
    ha_const.ATTR_ENTITY_ID = "entity_id"
    ha_const.ATTR_TEMPERATURE = "temperature"
    ha_const.CONF_NAME = "name"
    ha_const.CONF_UNIQUE_ID = "unique_id"

    # homeassistant.exceptions
    ha_exc = ModuleType("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    ha_exc.HomeAssistantError = HomeAssistantError

    # homeassistant.core
    ha_core = ModuleType("homeassistant.core")
    ha_core.callback = lambda fn: fn
    ha_core.HomeAssistant = object

    # homeassistant.components & climate & remote
    ha_comp = ModuleType("homeassistant.components")
    ha_climate = ModuleType("homeassistant.components.climate")

    class HVACMode(StrEnum):
        OFF = "off"
        HEAT_COOL = "heat_cool"
        COOL = "cool"
        HEAT = "heat"
        DRY = "dry"
        FAN_ONLY = "fan_only"

    class ClimateEntityFeature(IntFlag):
        TARGET_TEMPERATURE = 1
        FAN_MODE = 8
        PRESET_MODE = 16
        SWING_MODE = 32
        TURN_OFF = 128
        TURN_ON = 256
        SWING_HORIZONTAL_MODE = 512

    class _MockSchema:
        def __init__(self, d=None):
            self.schema = dict(d or {})

        def extend(self, other):
            merged = dict(self.schema)
            merged.update(other)
            return _MockSchema(merged)

    class ClimateEntity:
        hass = None

        @property
        def native_temperature_unit(self):
            return getattr(self, "_attr_native_temperature_unit", None)

        @property
        def native_target_temperature(self):
            return getattr(self, "_attr_native_target_temperature", None)

        @property
        def hvac_mode(self):
            return getattr(self, "_attr_hvac_mode", None)

        @property
        def target_temperature(self):
            if hasattr(self, "_attr_native_target_temperature"):
                return self._attr_native_target_temperature
            return getattr(self, "_attr_target_temperature", None)

        @property
        def fan_mode(self):
            return getattr(self, "_attr_fan_mode", None)

        @property
        def swing_mode(self):
            return getattr(self, "_attr_swing_mode", None)

        @property
        def swing_horizontal_mode(self):
            return getattr(self, "_attr_swing_horizontal_mode", None)

        @property
        def preset_mode(self):
            return getattr(self, "_attr_preset_mode", None)

        @property
        def supported_features(self):
            return getattr(self, "_attr_supported_features", 0)

        def async_write_ha_state(self):
            pass

        async def async_added_to_hass(self):
            pass

        async def async_will_remove_from_hass(self):
            pass

    ha_climate.HVACMode = HVACMode
    ha_climate.ClimateEntityFeature = ClimateEntityFeature
    ha_climate.ClimateEntity = ClimateEntity
    ha_climate.ATTR_HVAC_MODE = "hvac_mode"
    ha_climate.PLATFORM_SCHEMA = _MockSchema()

    ha_remote = ModuleType("homeassistant.components.remote")
    ha_remote.DOMAIN = "remote"
    ha_remote.SERVICE_SEND_COMMAND = "send_command"
    ha_remote.ATTR_COMMAND = "command"

    # homeassistant.config_entries
    ha_ce = ModuleType("homeassistant.config_entries")

    class ConfigFlow:
        def __init_subclass__(cls, domain=None, **kwargs):
            super().__init_subclass__(**kwargs)
            cls._domain = domain

        def async_create_entry(self, *, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(self, *, step_id, data_schema, errors=None):
            return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors}

    class OptionsFlow:
        config_entry = None

        def async_create_entry(self, *, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(self, *, step_id, data_schema, errors=None):
            return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors}

    ha_ce.ConfigEntry = object
    ha_ce.ConfigFlow = ConfigFlow
    ha_ce.ConfigFlowResult = dict
    ha_ce.OptionsFlow = OptionsFlow

    # homeassistant.helpers.*
    ha_helpers = ModuleType("homeassistant.helpers")
    ha_cv = ModuleType("homeassistant.helpers.config_validation")
    ha_cv.entity_id = str
    ha_cv.string = str

    ha_dr = ModuleType("homeassistant.helpers.device_registry")
    ha_dr.DeviceInfo = lambda **kw: kw

    ha_er = ModuleType("homeassistant.helpers.entity_registry")
    ha_er.async_get = lambda hass: hass._entity_registry

    ha_rs = ModuleType("homeassistant.helpers.restore_state")

    class RestoreEntity:
        _mock_last_state = None

        async def async_get_last_state(self):
            return self._mock_last_state

    ha_rs.RestoreEntity = RestoreEntity

    ha_sel = ModuleType("homeassistant.helpers.selector")
    ha_sel.EntitySelector = lambda cfg=None: ("EntitySelector", cfg)
    ha_sel.EntitySelectorConfig = lambda **kw: kw
    ha_sel.SelectOptionDict = lambda **kw: kw
    ha_sel.SelectSelector = lambda cfg=None: ("SelectSelector", cfg)
    ha_sel.SelectSelectorConfig = lambda **kw: kw

    class SelectSelectorMode(StrEnum):
        DROPDOWN = "dropdown"

    ha_sel.SelectSelectorMode = SelectSelectorMode

    # voluptuous stub if not installed
    if "voluptuous" not in sys.modules:
        vol = ModuleType("voluptuous")
        vol.UNDEFINED = object()
        vol.Required = lambda k, default=vol.UNDEFINED: ("Required", k, default)
        vol.Optional = lambda k, default=vol.UNDEFINED: ("Optional", k, default)
        vol.In = lambda seq: ("In", list(seq))
        vol.Schema = lambda fields: fields
        sys.modules["voluptuous"] = vol

    sys.modules.update(
        {
            "homeassistant": ha,
            "homeassistant.const": ha_const,
            "homeassistant.exceptions": ha_exc,
            "homeassistant.core": ha_core,
            "homeassistant.components": ha_comp,
            "homeassistant.components.climate": ha_climate,
            "homeassistant.components.remote": ha_remote,
            "homeassistant.config_entries": ha_ce,
            "homeassistant.helpers": ha_helpers,
            "homeassistant.helpers.config_validation": ha_cv,
            "homeassistant.helpers.device_registry": ha_dr,
            "homeassistant.helpers.entity_registry": ha_er,
            "homeassistant.helpers.restore_state": ha_rs,
            "homeassistant.helpers.selector": ha_sel,
        }
    )


_install_ha_stubs()
sys.path.insert(0, str(ROOT_DIR))

from homeassistant.components.climate import HVACMode  # noqa: E402
from homeassistant.exceptions import HomeAssistantError  # noqa: E402

from custom_components.mitsubishi_heavy import async_setup_entry, async_unload_entry  # noqa: E402
from custom_components.mitsubishi_heavy.climate import (  # noqa: E402
    MitsubishiHeavyClimate,
    async_setup_entry as climate_setup_entry,
    async_setup_platform as climate_setup_platform,
)
from custom_components.mitsubishi_heavy.config_flow import (  # noqa: E402
    MitsubishiHeavyConfigFlow,
    MitsubishiHeavyOptionsFlow,
)
from custom_components.mitsubishi_heavy.const import (  # noqa: E402
    CONF_PROTOCOL,
    CONF_REMOTE_ENTITY,
    PROTOCOL_MHI_48,
    PROTOCOL_MHI_88,
    PROTOCOL_MHI_152,
    PROTOCOL_MHI_160,
)
from custom_components.mitsubishi_heavy.protocol import (  # noqa: E402
    ACState,
    encode_broadlink_command,
    encode_broadlink_ticks,
    encode_frame_bytes,
)


@dataclass
class _MockRegEntry:
    entity_id: str
    domain: str
    platform: str
    disabled_by: str | None = None


class _FakeHass:
    def __init__(self, reg_entries=(), state_remote_ids=()):
        self._entity_registry = SimpleNamespace(
            entities={e.entity_id: e for e in reg_entries}
        )
        self._state_remote_ids = list(state_remote_ids)
        self.sent_calls: list[tuple[str, str, dict]] = []

        async def _async_call(domain, service, data, blocking=False):
            self.sent_calls.append((domain, service, dict(data)))

        self.services = SimpleNamespace(async_call=_async_call)
        self.states = SimpleNamespace(
            async_entity_ids=lambda domain: list(self._state_remote_ids) if domain == "remote" else []
        )


class TestMitsubishiHeavyComponent(unittest.TestCase):
    """Test protocol encoding, remote discovery, config flow, and climate entity."""

    def test_json_metadata_files_valid(self) -> None:
        for rel in ("manifest.json", "strings.json", "translations/en.json"):
            content = json.loads((COMP_DIR / rel).read_text())
            self.assertIsInstance(content, dict)

    def test_mhi_88_matches_rkx502a001c_frames(self) -> None:
        # 23C Heat, Fan Auto, SwingV Auto (4), SwingH Off (0) -> AD 51 3C D9 26 00 FF 10 EF 6C 93
        st = ACState(power=True, mode="heat", temperature=23, fan="auto", swing_v="auto", swing_h="off")
        self.assertEqual(encode_frame_bytes(PROTOCOL_MHI_88, st).hex(" "), "ad 51 3c d9 26 00 ff 10 ef 6c 93")

        # SwingH Auto (8 -> B5=0x80), matching 1687.json SRK35ZJX-S!
        st_1687 = ACState(power=True, mode="cool", temperature=24, fan="medium", swing_v="auto", swing_h="auto")
        self.assertEqual(encode_frame_bytes(PROTOCOL_MHI_88, st_1687).hex(" "), "ad 51 3c d9 26 80 7f 70 8f 79 86")

        # 3D Auto (14 -> B5=0xC8) + Boost/Hi-Power (6 -> B7 |= 0xC0)
        st_3d = ACState(power=True, mode="cool", temperature=20, fan="low", swing_v="auto", swing_h="3d_auto", preset="boost")
        f_3d = encode_frame_bytes(PROTOCOL_MHI_88, st_3d)
        self.assertEqual(f_3d[5], 0xC8)
        self.assertEqual(f_3d[7], 0xD0)  # 0xC0 (Turbo) | 0x10 (SwingV Auto)
        for k in range(3):
            self.assertEqual(f_3d[5 + 2 * k] ^ f_3d[6 + 2 * k], 0xFF)

        # SwingV Lowest (7 = 0b111 -> SwingV5=1 -> B5=0x02, SwingV7=3 -> B7|=0x18) + Fan High (4 -> B7|=0x80) -> B7=0x98
        st_lowest = ACState(power=True, mode="heat", temperature=23, fan="high", swing_v="lowest", swing_h="off")
        self.assertEqual(encode_frame_bytes(PROTOCOL_MHI_88, st_lowest).hex(" "), "ad 51 3c d9 26 02 fd 98 67 6c 93")

        # Off clears bit 3 of B9
        st_off = ACState(power=False, mode="heat", temperature=23, fan="auto", swing_v="auto", swing_h="off")
        self.assertEqual(encode_frame_bytes(PROTOCOL_MHI_88, st_off)[9], 0x64)

    def test_mhi_152_48_160_frames_and_broadlink_packets(self) -> None:
        expected_ticks = {
            PROTOCOL_MHI_88: 180,
            PROTOCOL_MHI_152: 308,
            PROTOCOL_MHI_48: 102,
            PROTOCOL_MHI_160: 326,
        }
        for proto, exp_len in expected_ticks.items():
            st = ACState(power=True, mode="cool", temperature=22, fan="low", swing_h="3d_auto", preset="quiet")
            ticks = encode_broadlink_ticks(proto, st)
            self.assertEqual(len(ticks), exp_len)
            cmd = encode_broadlink_command(proto, st)
            self.assertTrue(cmd.startswith("b64:"))
            raw = base64.b64decode(cmd[4:], validate=True)
            self.assertEqual(raw[:2], b"\x26\x00")
            decl = int.from_bytes(raw[2:4], "little")
            self.assertEqual(len(raw), 4 + decl)

        # Check MHI_152 3D Auto + Quiet bits
        f152 = encode_frame_bytes(
            PROTOCOL_MHI_152,
            ACState(power=True, mode="cool", temperature=22, fan="low", swing_v="high", swing_h="3d_auto", preset="quiet"),
        )
        self.assertEqual(f152[:5], bytes.fromhex("ad513ce51a"))
        self.assertEqual(f152[5], 0x09)   # Power + Cool
        self.assertEqual(f152[7], 0x05)   # 22 - 17
        self.assertEqual(f152[9], 0x02)   # Low
        self.assertEqual(f152[11], 0x52)  # SwingV=High (0x40) | 3D (0x12), matches 1691.json!
        self.assertEqual(f152[15], 0x80)  # Quiet/Silent

    def test_config_flow_single_parameter_when_one_broadlink_remote(self) -> None:
        hass = _FakeHass(
            reg_entries=[
                _MockRegEntry("remote.apple_tv", "remote", "apple_tv"),
                _MockRegEntry("remote.living_room_rm4", "remote", "broadlink"),
            ]
        )
        flow = MitsubishiHeavyConfigFlow()
        flow.hass = hass

        form = asyncio.run(flow.async_step_user(None))
        self.assertEqual(form["type"], "form")
        # Only 1 field (`protocol`) shown because Apple TV is filtered out and 1 Broadlink exists!
        self.assertEqual(len(form["data_schema"]), 1)

        result = asyncio.run(flow.async_step_user({CONF_PROTOCOL: PROTOCOL_MHI_88}))
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(
            result["data"],
            {
                CONF_PROTOCOL: PROTOCOL_MHI_88,
                CONF_REMOTE_ENTITY: "remote.living_room_rm4",
            },
        )

    def test_climate_entity_lifecycle_and_remote_transmission(self) -> None:
        hass = _FakeHass(
            reg_entries=[
                _MockRegEntry("remote.tv", "remote", "androidtv_remote"),
                _MockRegEntry("remote.rm_mini", "remote", "broadlink"),
            ]
        )
        entity = MitsubishiHeavyClimate(
            protocol=PROTOCOL_MHI_88,
            remote_entity=None,  # Auto-resolved!
            name="Bedroom AC",
            unique_id="test_mhi_88",
            device_info=None,
            coalesce_delay=0.0,
            min_tx_gap=0.0,
        )
        entity.hass = hass
        self.assertFalse(hasattr(entity, "_attr_target_temperature"))
        self.assertEqual(entity.native_target_temperature, 23.0)

        # Changing temperature while OFF updates state without firing IR
        asyncio.run(entity.async_set_temperature(temperature=25))
        self.assertEqual(entity.target_temperature, 25.0)
        self.assertEqual(len(hass.sent_calls), 0)

        # Turning ON transmits Heat/Cool via auto-discovered remote.rm_mini
        asyncio.run(entity.async_set_hvac_mode(HVACMode.HEAT))
        self.assertEqual(len(hass.sent_calls), 1)
        dom, svc, payload = hass.sent_calls[-1]
        self.assertEqual((dom, svc), ("remote", "send_command"))
        self.assertEqual(payload["entity_id"], "remote.rm_mini")
        self.assertTrue(payload["command"].startswith("b64:"))
        self.assertEqual(entity.extra_state_attributes["last_ir_frame_hex"], "ad 51 3c d9 26 00 ff 10 ef 8c 73")

        # Setting Boost preset transmits Turbo fan code (0xC0 | 0x10 = 0xD0)
        asyncio.run(entity.async_set_preset_mode("boost"))
        self.assertEqual(entity.extra_state_attributes["last_ir_frame_hex"], "ad 51 3c d9 26 00 ff d0 2f 8c 73")

        # Setting manual fan speed clears Boost preset automatically
        asyncio.run(entity.async_set_fan_mode("high"))
        self.assertEqual(entity.preset_mode, "none")
        self.assertEqual(entity.extra_state_attributes["last_ir_frame_hex"], "ad 51 3c d9 26 00 ff 90 6f 8c 73")

        # Enabling 3D Auto sets B5=0xC8; Fan Auto keeps 3D Auto, whereas manual fan / Boost / manual SwingV cancels 3D Auto
        asyncio.run(entity.async_set_swing_horizontal_mode("3d_auto"))
        self.assertEqual(entity.swing_horizontal_mode, "3d_auto")
        self.assertEqual(entity.extra_state_attributes["last_ir_frame_hex"], "ad 51 3c d9 26 c8 37 90 6f 8c 73")

        asyncio.run(entity.async_set_fan_mode("auto"))
        self.assertEqual(entity.swing_horizontal_mode, "3d_auto")

        asyncio.run(entity.async_set_fan_mode("high"))
        self.assertEqual(entity.swing_horizontal_mode, "off")
        self.assertEqual(entity.extra_state_attributes["last_ir_frame_hex"], "ad 51 3c d9 26 00 ff 90 6f 8c 73")

        asyncio.run(entity.async_set_swing_horizontal_mode("3d_auto"))
        asyncio.run(entity.async_set_swing_mode("lowest"))
        self.assertEqual(entity.swing_horizontal_mode, "off")
        self.assertEqual(entity.extra_state_attributes["last_ir_frame_hex"], "ad 51 3c d9 26 02 fd 98 67 8c 73")

        asyncio.run(entity.async_set_swing_mode("auto"))
        asyncio.run(entity.async_set_swing_horizontal_mode("3d_auto"))
        asyncio.run(entity.async_set_preset_mode("boost"))
        self.assertEqual(entity.swing_horizontal_mode, "off")
        self.assertEqual(entity.extra_state_attributes["last_ir_frame_hex"], "ad 51 3c d9 26 00 ff d0 2f 8c 73")

        asyncio.run(entity.async_set_fan_mode("high"))

        # Turn OFF clears power bit and remembers last active mode (HEAT) for next Turn ON
        asyncio.run(entity.async_turn_off())
        self.assertEqual(entity.hvac_mode, HVACMode.OFF)
        self.assertEqual(entity.extra_state_attributes["last_ir_frame_hex"], "ad 51 3c d9 26 00 ff 90 6f 84 7b")

        asyncio.run(entity.async_turn_on())
        self.assertEqual(entity.hvac_mode, HVACMode.HEAT)

        # Error when zero remotes exist (fails fast synchronously even when coalescing is active)
        entity_no_rem = MitsubishiHeavyClimate(PROTOCOL_MHI_88, None, "AC", "id2", None)
        entity_no_rem.hass = _FakeHass()
        with self.assertRaises(HomeAssistantError):
            asyncio.run(entity_no_rem.async_turn_on())

    def test_burst_coalescing_for_versatile_thermostat(self) -> None:
        hass = _FakeHass(reg_entries=[_MockRegEntry("remote.rm_mini", "remote", "broadlink")])
        entity = MitsubishiHeavyClimate(
            protocol=PROTOCOL_MHI_88,
            remote_entity="remote.rm_mini",
            name="Bedroom AC",
            unique_id="test_coalesce",
            device_info=None,
            coalesce_delay=0.05,
            min_tx_gap=0.0,
        )
        entity.hass = hass

        async def _run_burst() -> None:
            # Simulate Versatile Thermostat firing 4 sequential service calls back-to-back
            await entity.async_set_hvac_mode(HVACMode.HEAT)
            await entity.async_set_temperature(temperature=24)
            await entity.async_set_fan_mode("high")
            await entity.async_set_swing_mode("lowest")

            # Attributes update immediately for VTherm, while 0 IR bursts have fired yet
            self.assertEqual(entity.hvac_mode, HVACMode.HEAT)
            self.assertEqual(entity.target_temperature, 24.0)
            self.assertEqual(entity.fan_mode, "high")
            self.assertEqual(entity.swing_mode, "lowest")
            self.assertEqual(len(hass.sent_calls), 0)

            # Wait past the 50ms coalesce window -> exactly ONE consolidated IR packet sent!
            await asyncio.sleep(0.08)
            self.assertEqual(len(hass.sent_calls), 1)
            self.assertEqual(
                entity.extra_state_attributes["last_ir_frame_hex"],
                "ad 51 3c d9 26 02 fd 98 67 7c 83",
            )

            # Removal cancels any pending task without transmitting
            await entity.async_set_temperature(temperature=26)
            await entity.async_will_remove_from_hass()
            await asyncio.sleep(0.08)
            self.assertEqual(len(hass.sent_calls), 1)

        asyncio.run(_run_burst())

    def test_entry_and_yaml_platform_setup_and_restore(self) -> None:
        hass = _FakeHass(reg_entries=[_MockRegEntry("remote.rm4", "remote", "broadlink")])
        forwarded = []
        hass.config_entries = SimpleNamespace(
            async_forward_entry_setups=lambda e, p: asyncio.sleep(0, result=forwarded.extend(p)),
            async_unload_platforms=lambda e, p: asyncio.sleep(0, result=True),
            async_reload=lambda eid: asyncio.sleep(0),
        )
        entry = SimpleNamespace(
            entry_id="entry_1",
            title="Mitsubishi Heavy AC",
            data={CONF_PROTOCOL: PROTOCOL_MHI_152},
            options={},
            async_on_unload=lambda cb: None,
            add_update_listener=lambda fn: fn,
        )
        self.assertTrue(asyncio.run(async_setup_entry(hass, entry)))
        self.assertEqual(len(forwarded), 1)
        self.assertTrue(asyncio.run(async_unload_entry(hass, entry)))

        added = []
        asyncio.run(climate_setup_entry(hass, entry, added.extend))
        asyncio.run(climate_setup_platform(hass, {CONF_PROTOCOL: PROTOCOL_MHI_88, "name": "Living AC"}, added.extend))
        self.assertEqual(len(added), 2)

        # Verify RestoreEntity restores state cleanly without transmitting IR
        ent = added[1]
        ent.hass = hass
        ent._mock_last_state = SimpleNamespace(
            state="cool",
            attributes={
                "temperature": 21,
                "fan_mode": "medium",
                "swing_mode": "middle",
                "swing_horizontal_mode": "3d_auto",
                "preset_mode": "eco",
                "last_active_hvac_mode": "cool",
                "last_ir_frame_hex": "ad 51 3c d9 26 c8 37 f8 07 49 b6",
            },
        )
        asyncio.run(ent.async_added_to_hass())
        self.assertEqual(ent.hvac_mode, HVACMode.COOL)
        self.assertEqual(ent.target_temperature, 21.0)
        self.assertEqual(ent.fan_mode, "medium")
        self.assertEqual(ent.swing_horizontal_mode, "3d_auto")
        self.assertEqual(ent.preset_mode, "eco")
        self.assertEqual(len(hass.sent_calls), 0)

        # Verify OptionsFlow
        opt_flow = MitsubishiHeavyOptionsFlow()
        opt_flow.hass = hass
        opt_flow.config_entry = entry
        opt_form = asyncio.run(opt_flow.async_step_init(None))
        self.assertEqual(opt_form["type"], "form")
        opt_res = asyncio.run(opt_flow.async_step_init({CONF_PROTOCOL: PROTOCOL_MHI_48}))
        self.assertEqual(opt_res["data"], {CONF_PROTOCOL: PROTOCOL_MHI_48})


if __name__ == "__main__":
    unittest.main()

"""Pure-Python IR protocol encoder for Mitsubishi Heavy Industries AC units."""

from __future__ import annotations

import base64
from dataclasses import dataclass

from .const import (
    MAX_TEMP,
    MIN_TEMP,
    PROTOCOL_MHI_48,
    PROTOCOL_MHI_88,
    PROTOCOL_MHI_152,
    PROTOCOL_MHI_160,
)

# HVAC mode names aligned with homeassistant.components.climate.HVACMode
MODE_HEAT_COOL = "heat_cool"
MODE_COOL = "cool"
MODE_DRY = "dry"
MODE_FAN_ONLY = "fan_only"
MODE_HEAT = "heat"

SUPPORTED_HVAC_MODES: tuple[str, ...] = (
    MODE_HEAT_COOL,
    MODE_COOL,
    MODE_HEAT,
    MODE_DRY,
    MODE_FAN_ONLY,
)

# Fan speeds
FAN_AUTO = "auto"
FAN_ULTRALOW = "ultralow"
FAN_LOW = "low"
FAN_MEDIUM = "medium"
FAN_HIGH = "high"

# Presets
PRESET_NONE = "none"
PRESET_BOOST = "boost"  # HI POWER / Turbo
PRESET_ECO = "eco"      # ECONO
PRESET_QUIET = "quiet"  # SILENT (152-bit)
PRESET_SLEEP = "sleep"  # NIGHT setback (152-bit)

# Vertical swing modes
SWING_V_AUTO = "auto"
SWING_V_HIGHEST = "highest"
SWING_V_HIGH = "high"
SWING_V_MIDDLE = "middle"
SWING_V_LOW = "low"
SWING_V_LOWEST = "lowest"
SWING_V_OFF = "off"

# Horizontal swing modes
SWING_H_AUTO = "auto"
SWING_H_3D_AUTO = "3d_auto"
SWING_H_LEFT_MAX = "left_max"
SWING_H_LEFT = "left"
SWING_H_MIDDLE = "middle"
SWING_H_RIGHT = "right"
SWING_H_RIGHT_MAX = "right_max"
SWING_H_LEFT_RIGHT = "left_right"
SWING_H_RIGHT_LEFT = "right_left"
SWING_H_OFF = "off"


@dataclass(frozen=True)
class ProtocolCapabilities:
    """Capabilities supported by a specific Mitsubishi Heavy IR protocol."""

    fan_modes: tuple[str, ...]
    swing_v_modes: tuple[str, ...] = ()
    swing_h_modes: tuple[str, ...] = ()
    preset_modes: tuple[str, ...] = ()
    default_swing_v: str = SWING_V_AUTO
    default_swing_h: str = SWING_H_OFF


PROTOCOL_CAPABILITIES: dict[str, ProtocolCapabilities] = {
    PROTOCOL_MHI_88: ProtocolCapabilities(
        fan_modes=(FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH),
        swing_v_modes=(
            SWING_V_AUTO,
            SWING_V_HIGHEST,
            SWING_V_HIGH,
            SWING_V_MIDDLE,
            SWING_V_LOW,
            SWING_V_OFF,
        ),
        swing_h_modes=(
            SWING_H_OFF,
            SWING_H_AUTO,
            SWING_H_3D_AUTO,
            SWING_H_LEFT_MAX,
            SWING_H_LEFT,
            SWING_H_MIDDLE,
            SWING_H_RIGHT,
            SWING_H_RIGHT_MAX,
            SWING_H_LEFT_RIGHT,
            SWING_H_RIGHT_LEFT,
        ),
        preset_modes=(PRESET_NONE, PRESET_BOOST, PRESET_ECO),
        default_swing_v=SWING_V_AUTO,
        default_swing_h=SWING_H_OFF,
    ),
    PROTOCOL_MHI_152: ProtocolCapabilities(
        fan_modes=(FAN_AUTO, FAN_ULTRALOW, FAN_LOW, FAN_MEDIUM, FAN_HIGH),
        swing_v_modes=(
            SWING_V_AUTO,
            SWING_V_HIGHEST,
            SWING_V_HIGH,
            SWING_V_MIDDLE,
            SWING_V_LOW,
            SWING_V_LOWEST,
            SWING_V_OFF,
        ),
        swing_h_modes=(
            SWING_H_OFF,
            SWING_H_AUTO,
            SWING_H_3D_AUTO,
            SWING_H_LEFT_MAX,
            SWING_H_LEFT,
            SWING_H_MIDDLE,
            SWING_H_RIGHT,
            SWING_H_RIGHT_MAX,
            SWING_H_LEFT_RIGHT,
            SWING_H_RIGHT_LEFT,
        ),
        preset_modes=(PRESET_NONE, PRESET_BOOST, PRESET_ECO, PRESET_QUIET, PRESET_SLEEP),
        default_swing_v=SWING_V_AUTO,
        default_swing_h=SWING_H_MIDDLE,
    ),
    PROTOCOL_MHI_48: ProtocolCapabilities(
        fan_modes=(FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH),
    ),
    PROTOCOL_MHI_160: ProtocolCapabilities(
        fan_modes=(FAN_AUTO, FAN_ULTRALOW, FAN_LOW, FAN_MEDIUM, FAN_HIGH),
    ),
}


@dataclass
class ACState:
    """Full logical state transmitted in each stateless MHI IR frame."""

    power: bool = False
    mode: str = MODE_COOL
    temperature: int = 23
    fan: str = FAN_AUTO
    swing_v: str = SWING_V_AUTO
    swing_h: str = SWING_H_OFF
    preset: str = PRESET_NONE
    clean: bool = False


_MODE_CODE_3BIT: dict[str, int] = {
    MODE_HEAT_COOL: 0x0,
    MODE_COOL: 0x1,
    MODE_DRY: 0x2,
    MODE_FAN_ONLY: 0x3,
    MODE_HEAT: 0x4,
}

_MHI88_FAN_CODE: dict[str, int] = {
    FAN_AUTO: 0,
    FAN_ULTRALOW: 1,
    FAN_LOW: 2,
    FAN_MEDIUM: 3,
    FAN_HIGH: 4,
}

_MHI88_SWING_V_CODE: dict[str, int] = {
    SWING_V_OFF: 0,      # 0b000
    SWING_V_HIGH: 1,     # 0b001
    SWING_V_MIDDLE: 3,   # 0b011
    SWING_V_AUTO: 4,     # 0b100
    SWING_V_LOW: 5,      # 0b101
    SWING_V_HIGHEST: 6,  # 0b110
}

_MHI88_SWING_H_CODE: dict[str, int] = {
    SWING_H_OFF: 0,          # 0b0000
    SWING_H_LEFT_MAX: 1,     # 0b0001
    SWING_H_RIGHT_MAX: 2,    # 0b0010
    SWING_H_LEFT: 5,         # 0b0101
    SWING_H_LEFT_RIGHT: 6,   # 0b0110
    SWING_H_AUTO: 8,         # 0b1000
    SWING_H_MIDDLE: 9,       # 0b1001
    SWING_H_RIGHT_LEFT: 10,  # 0b1010
    SWING_H_RIGHT: 13,       # 0b1101
    SWING_H_3D_AUTO: 14,     # 0b1110
}

_MHI152_FAN_CODE: dict[str, int] = {
    FAN_AUTO: 0x0,
    FAN_ULTRALOW: 0x1,
    FAN_LOW: 0x2,
    FAN_MEDIUM: 0x3,
    FAN_HIGH: 0x4,
}

_MHI152_SWING_V_CODE: dict[str, int] = {
    SWING_V_AUTO: 0,
    SWING_V_HIGHEST: 1,
    SWING_V_HIGH: 2,
    SWING_V_MIDDLE: 3,
    SWING_V_LOW: 4,
    SWING_V_LOWEST: 5,
    SWING_V_OFF: 6,
}

_MHI152_SWING_H_CODE: dict[str, int] = {
    SWING_H_AUTO: 0,
    SWING_H_LEFT_MAX: 1,
    SWING_H_LEFT: 2,
    SWING_H_MIDDLE: 3,
    SWING_H_RIGHT: 4,
    SWING_H_RIGHT_MAX: 5,
    SWING_H_RIGHT_LEFT: 6,
    SWING_H_LEFT_RIGHT: 7,
    SWING_H_OFF: 8,
    SWING_H_3D_AUTO: 0,
}

_MHI48_FAN_BYTE: dict[str, int] = {
    FAN_AUTO: 0x10,
    FAN_HIGH: 0x30,
    FAN_MEDIUM: 0x50,
    FAN_LOW: 0x70,
}

_MHI160_FAN_BYTE: dict[str, int] = {
    FAN_ULTRALOW: 0x00,
    FAN_LOW: 0x01,
    FAN_MEDIUM: 0x02,
    FAN_HIGH: 0x03,
    FAN_AUTO: 0x04,
}

_MHI160_MODE_BASE: dict[str, int] = {
    MODE_HEAT_COOL: 0x00,
    MODE_DRY: 0x10,
    MODE_COOL: 0x20,
    MODE_FAN_ONLY: 0x30,
    MODE_HEAT: 0x40,
}


def _clamp_temp(temp: int | float) -> int:
    return max(MIN_TEMP, min(MAX_TEMP, int(round(temp))))


def _bytes_to_lsb_bits(data: bytes) -> list[int]:
    bits: list[int] = []
    for byte in data:
        for k in range(8):
            bits.append((byte >> k) & 1)
    return bits


def pack_broadlink_b64(ticks: list[int]) -> str:
    """Pack Broadlink 32.84us tick counts into a 0x26 IR Base64 string."""
    payload = bytearray()
    for tick in ticks:
        if tick < 256:
            payload.append(tick)
        else:
            payload.extend((0x00, (tick >> 8) & 0xFF, tick & 0xFF))
    packet = bytearray((0x26, 0x00)) + len(payload).to_bytes(2, "little") + payload
    return base64.b64encode(bytes(packet)).decode("ascii")


def encode_frame_bytes(protocol: str, state: ACState) -> bytes:
    """Build the raw protocol byte payload for the given ACState."""
    temp_c = _clamp_temp(state.temperature)
    mode = state.mode if state.mode in _MODE_CODE_3BIT else MODE_COOL

    if protocol == PROTOCOL_MHI_88:
        v_code = _MHI88_SWING_V_CODE.get(state.swing_v, 4)
        h_code = _MHI88_SWING_H_CODE.get(state.swing_h, 0)

        if state.preset == PRESET_BOOST:
            fan_code = 6
        elif state.preset == PRESET_ECO:
            fan_code = 7
        else:
            fan_code = _MHI88_FAN_CODE.get(state.fan, 0)

        # Byte 5: bit 1 = SwingV5, bits 2..3 = SwingH1, bit 5 = Clean, bits 6..7 = SwingH2
        b5 = (
            ((v_code & 0x01) << 1)
            | ((h_code & 0x03) << 2)
            | (0x20 if (state.clean and state.power) else 0x00)
            | (((h_code >> 2) & 0x03) << 6)
        )
        # Byte 7: bits 3..4 = SwingV7, bits 5..7 = Fan
        b7 = (((v_code >> 1) & 0x03) << 3) | ((fan_code & 0x07) << 5)
        # Byte 9: bits 0..2 = Mode, bit 3 = Power, bits 4..7 = Temp
        t_nib = 0x4 if mode == MODE_FAN_ONLY else (temp_c - 17)
        b9 = (t_nib << 4) | (0x08 if state.power else 0x00) | _MODE_CODE_3BIT[mode]
        return bytes(
            (0xAD, 0x51, 0x3C, 0xD9, 0x26, b5, b5 ^ 0xFF, b7, b7 ^ 0xFF, b9, b9 ^ 0xFF)
        )

    if protocol == PROTOCOL_MHI_152:
        b5 = (
            (0x08 if state.power else 0x00)
            | _MODE_CODE_3BIT[mode]
            | (0x20 if (state.clean and state.power) else 0x00)
        )
        b7 = 0x0D if mode == MODE_FAN_ONLY else (temp_c - 17)

        if state.preset == PRESET_BOOST:
            b9 = 0x08
        elif state.preset == PRESET_ECO:
            b9 = 0x06
        elif mode == MODE_DRY:
            b9 = 0x00
        else:
            b9 = _MHI152_FAN_CODE.get(state.fan, 0x00)

        v_code = _MHI152_SWING_V_CODE.get(state.swing_v, 0)
        b11 = (v_code & 0x07) << 5
        if state.swing_h == SWING_H_3D_AUTO and mode in (MODE_HEAT_COOL, MODE_COOL, MODE_HEAT):
            b11 |= 0x12

        b13 = _MHI152_SWING_H_CODE.get(state.swing_h, 0) & 0x0F
        b15 = (
            (0x80 if state.preset == PRESET_QUIET else 0x00)
            | (0x40 if state.preset == PRESET_SLEEP else 0x00)
        )
        b17 = 0x80

        out = bytearray((0xAD, 0x51, 0x3C, 0xE5, 0x1A))
        for reg in (b5, b7, b9, b11, b13, b15, b17):
            out.extend((reg, reg ^ 0xFF))
        return bytes(out)

    if protocol == PROTOCOL_MHI_48:
        b0 = _MHI48_FAN_BYTE.get(state.fan, 0x10)
        t_nib = 0x4 if mode == MODE_FAN_ONLY else (temp_c - 17)
        b2 = (t_nib << 4) | (0x08 if state.power else 0x00) | _MODE_CODE_3BIT[mode]
        return bytes((b0, b0 ^ 0xFF, b2, b2 ^ 0xFF, 0xD5, 0x2A))

    if protocol == PROTOCOL_MHI_160:
        if not state.power:
            b2 = 0x02
        else:
            b2 = 0x80 | _MHI160_MODE_BASE[mode] | (temp_c - 16)
        b8 = _MHI160_FAN_BYTE.get(state.fan, 0x04)
        b0_3 = [0x0D, 0x00, b2, 0x00]
        b8_11 = [b8, 0x01, 0x14, 0x00]
        return bytes(
            b0_3
            + [x ^ 0xFF for x in b0_3]
            + b8_11
            + [x ^ 0xFF for x in b8_11]
            + [0x02, 0xFD, 0x00, 0x00]
        )

    raise ValueError(f"Unsupported Mitsubishi Heavy IR protocol: {protocol}")


def encode_broadlink_ticks(protocol: str, state: ACState) -> list[int]:
    """Encode ACState into Broadlink 32.84us tick durations."""
    frame = encode_frame_bytes(protocol, state)
    bits = _bytes_to_lsb_bits(frame)

    if protocol in (PROTOCOL_MHI_88, PROTOCOL_MHI_152):
        ticks = [99, 50]
        for bit in bits:
            ticks.extend((13, 12 if bit == 1 else 37))
        ticks.extend((13, 3333))
        return ticks

    if protocol == PROTOCOL_MHI_48:
        ticks = [192, 250]
        for bit in bits:
            ticks.extend((18, 51 if bit == 1 else 118))
        ticks.extend((18, 250, 18, 3333))
        return ticks

    if protocol == PROTOCOL_MHI_160:
        ticks = [195, 247]
        for bit in bits:
            ticks.extend((16, 50 if bit == 0 else 115))
        ticks.extend((16, 247, 16, 3333))
        return ticks

    raise ValueError(f"Unsupported Mitsubishi Heavy IR protocol: {protocol}")


def encode_broadlink_command(protocol: str, state: ACState) -> str:
    """Return a `b64:...` command string ready for Home Assistant `remote.send_command`."""
    ticks = encode_broadlink_ticks(protocol, state)
    return f"b64:{pack_broadlink_b64(ticks)}"

"""Constants for the Mitsubishi Heavy IR Climate integration."""

from __future__ import annotations

DOMAIN = "mitsubishi_heavy"

CONF_PROTOCOL = "protocol"
CONF_REMOTE_ENTITY = "remote_entity"

PROTOCOL_MHI_88 = "mhi_88"
PROTOCOL_MHI_152 = "mhi_152"
PROTOCOL_MHI_48 = "mhi_48"
PROTOCOL_MHI_160 = "mhi_160"

PROTOCOLS: dict[str, str] = {
    PROTOCOL_MHI_88: "MHI 88-bit (RKX502A001 / SRK-ZJ, ZJX, ZSP, ZK)",
    PROTOCOL_MHI_152: "MHI 152-bit (RLA502A700 / SRK-ZM, ZS, ZSA, ZSX, ZRA)",
    PROTOCOL_MHI_48: "MHI 48-bit (RKS502A502 / SRKM25H, SRK40HBE)",
    PROTOCOL_MHI_160: "MHI 160-bit (FDUM VF2 Commercial Ducted)",
}

DEFAULT_NAME = "Mitsubishi Heavy AC"
DEFAULT_TEMP = 23
MIN_TEMP = 18
MAX_TEMP = 30
TEMP_STEP = 1.0

# Debounce window to coalesce multi-service bursts (e.g. Versatile Thermostat setting
# mode + temperature + fan together) into a single complete MHI state IR packet, and
# minimum gap between consecutive physical IR transmissions.
COALESCE_DELAY_SECONDS = 0.25
MIN_TX_GAP_SECONDS = 0.35

# Known Home Assistant integrations that provide physical IR blaster `remote` entities
IR_REMOTE_PLATFORMS: frozenset[str] = frozenset(
    {
        "broadlink",
        "esphome",
        "xiaomi_miio",
        "tuya",
        "localtuya",
        "zha",
        "mqtt",
        "switchbot",
        "lookin",
        "harmony",
        "globalcache",
        "kira",
    }
)

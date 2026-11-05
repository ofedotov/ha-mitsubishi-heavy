"""Helper utilities for resolving Home Assistant IR `remote` entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import entity_registry as er

from .const import IR_REMOTE_PLATFORMS

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# Media-player `remote` platforms that cannot transmit raw IR Base64 packets
_NON_IR_PLATFORMS: frozenset[str] = frozenset(
    {
        "apple_tv",
        "androidtv_remote",
        "samsungtv",
        "webostv",
        "braviatv",
        "roku",
        "LG_netcast",
        "panasonic_viera",
        "viziotv",
    }
)


def discover_remote_entities(hass: HomeAssistant) -> tuple[list[str], list[str]]:
    """Return `(ir_remotes, fallback_remotes)` available in Home Assistant."""
    ir_remotes: list[str] = []
    broadlink_remotes: list[str] = []
    fallback_remotes: list[str] = []
    seen: set[str] = set()

    registry = er.async_get(hass)
    for entry in registry.entities.values():
        if entry.domain != "remote" or entry.disabled_by is not None:
            continue
        seen.add(entry.entity_id)
        if entry.platform == "broadlink":
            broadlink_remotes.append(entry.entity_id)
        elif entry.platform in IR_REMOTE_PLATFORMS:
            ir_remotes.append(entry.entity_id)
        elif entry.platform not in _NON_IR_PLATFORMS:
            fallback_remotes.append(entry.entity_id)

    for entity_id in hass.states.async_entity_ids("remote"):
        if entity_id not in seen:
            fallback_remotes.append(entity_id)

    return sorted(broadlink_remotes) + sorted(ir_remotes), sorted(fallback_remotes)


def resolve_default_remote_entity(hass: HomeAssistant) -> str | None:
    """Resolve the best IR `remote` entity automatically when not specified."""
    ir_remotes, fallback_remotes = discover_remote_entities(hass)
    if len(ir_remotes) == 1:
        return ir_remotes[0]
    if len(ir_remotes) > 1:
        return ir_remotes[0]
    if len(fallback_remotes) >= 1:
        return fallback_remotes[0]
    return None

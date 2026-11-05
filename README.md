# Mitsubishi Heavy IR Climate for Home Assistant

Native Home Assistant `climate` integration that controls **Mitsubishi Heavy Industries (MHI)** air conditioners via any Home Assistant IR `remote` entity (such as **Broadlink RM Mini 3 / RM4 Mini / RM4 Pro**)—synthesizing bit-exact infrared frames in real time with **zero static JSON code files** and **only a single parameter: `protocol`**.

## Features

- **Single-parameter setup (`protocol`)**: Automatically discovers your Broadlink/IR `remote.*` entity while ignoring TV/media remotes (`apple_tv`, `androidtv_remote`, etc.). Supports overriding `remote_entity` when multiple IR blasters exist on the same Home Assistant server.
- **All 4 Mitsubishi Heavy IR protocols built-in**:
  | Protocol ID | Bits | Remote Models | Compatible Indoor Series |
  | :--- | :--- | :--- | :--- |
  | `mhi_88` | 88-bit | `RKX502A001` / `RKX502A001C` / `RKX502A001P` | `SRK-ZJ-S`, `SRK-ZJX-S`, `SRK-ZSP-W`, `SRK-ZMP-S`, `SRK71ZK-S`, `DXK-Z3/Z5` |
  | `mhi_152` | 152-bit | `RLA502A700` / `RLA502A700B` | `SRK-ZM-S`, `SRK-ZS-S`, `SRK-ZSA-W`, `SRK-ZSX`, `SRK-ZRA-W`, `DXK-ZMA/ZSA/ZRA` |
  | `mhi_48` | 48-bit | `RKS502A502` / `RKS502A503` | `SRKM25H`, `SRK40HBE` |
  | `mhi_160` | 160-bit | `FDUM` IR Receiver Kit | `FDUM VF2` Commercial Ducted |
- **Full native controls** (on protocols that support them):
  - **HVAC Modes**: `off`, `heat_cool` (Auto), `cool`, `heat`, `dry`, `fan_only`
  - **Temperature**: `18°C – 30°C` (`1°C` step)
  - **Fan Speeds**: `auto`, `ultralow` (`152`/`160`-bit), `low`, `medium`, `high`
  - **Vertical & Horizontal Swing**: Full vane positions + **`3D Auto`** (`3d_auto`)
  - **Presets**: `boost` (`HI POWER`), `eco` (`ECONO`), plus `quiet` (`SILENT`) & `sleep` (`NIGHT`) on `mhi_152`
  - **State Restoration**: Restores mode, temperature, fan, swing, and preset across Home Assistant restarts without sending spurious IR signals.

## Installation via HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=ofedotov&repository=ha-mitsubishi-heavy&category=integration)

1. Open **HACS** in Home Assistant.
2. Click the three-dot menu (top right) -> **Custom repositories**.
3. Enter `https://github.com/ofedotov/ha-mitsubishi-heavy` and select Category: **Integration**, then click **Add**.
4. Find **Mitsubishi Heavy IR Climate**, click **Download**, and **restart Home Assistant**.

## Configuration

### Option 1: UI Config Flow (Recommended)

Go to **Settings -> Devices & Services -> Add Integration -> Mitsubishi Heavy IR Climate** and select your **IR Protocol** (e.g. `mhi_88`).

### Option 2: `configuration.yaml`

```yaml
climate:
  - platform: mitsubishi_heavy
    protocol: mhi_88
```

*(Optional keys if you have multiple IR blasters: `remote_entity: remote.living_room_broadlink`, `name: Living Room AC`.)*

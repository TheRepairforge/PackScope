"""Data model + diagnostic thresholds for PackScope.

The thresholds and the Reading fields are a 1:1 mirror of the PocketOBI
firmware (PocketOBI/PocketOBI.ino) so the desktop app and the on-device
tool always reach the SAME verdict on the same pack. When a firmware
threshold changes, change it here too.

Field names follow the firmware's `BatteryData` struct, not new parallel
naming, per the project spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Diagnostic thresholds. These MIRROR the firmware #defines of the SAME name in
# PocketOBI.ino (the "Cell diagnostic thresholds" block) — keep the values in sync
# there, which is the single source of truth for the verdict.
# ---------------------------------------------------------------------------
CELL_V_MIN = 2.5    # below this = recoverable over-discharge (SUSPECT), not healthy
CELL_V_DEAD = 2.0   # below this a cell is genuinely dead/unrecoverable (FAULT)
CELL_V_MAX = 4.2    # full cell, bar-scale top
CELL_V_CRIT = 3.0   # critical cell voltage
DIFF_WARN = 0.15    # moderate imbalance, spread in volts
DIFF_BAD = 0.30     # bad imbalance, spread in volts
CELL_V_SENSE = 0.50  # below this = broken sense wire, not a real cell

TEMP_MIN_PLAUS = -20.0  # plausible temperature window, low end
TEMP_MAX_PLAUS = 80.0   # plausible temperature window, high end
TEMP_SPREAD_BAD = 10.0  # two in-range sensors disagreeing by more => suspect NTC
TEMP_WARM_C = 45.0      # Desk advisory only: above this a probe reads "warm" (let it cool)


def valid_ymd(year: int, month: int, day: int) -> bool:
    """Plausible pack date (ino: fmtPackDate). Old packs read the ROM/assembly-date
    bytes back as all-FF (-> 2255/255/255) or leave them 0; only a real date formats."""
    return 2005 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31


class Verdict(str, Enum):
    """Traffic-light verdict (PocketOBI.ino, enum Verdict). Five states.

    The .value strings are stable DB identifiers; the on-screen wording comes
    from ``verdict.verdict_label()`` (matching the firmware: HEALTHY / UNLOCK /
    POSSIBLE HW FIX / HARDWARE FIX)."""

    UNKNOWN = "UNKNOWN"        # V_UNKNOWN  (no valid pack)
    HEALTHY = "HEALTHY"        # V_HEALTHY  (green)
    REPAIRABLE = "REPAIRABLE"  # V_REPAIRABLE (yellow, false lock our unlock clears)
    SUSPECT = "SUSPECT"        # V_SUSPECT  (orange, soft/empirical hint: latched or sensor spread)
    REAL_FAULT = "REAL_FAULT"  # V_FAULT    (red, confirmed hardware fault)


class HwFault(str, Enum):
    """Stage-1 hardware fault classes (PocketOBI.ino, enum HwFault)."""

    NONE = "NONE"
    SENSE_WIRE = "SENSE_WIRE"    # a cell near 0 V while the pack is alive
    WEAK_CELL = "WEAK_CELL"      # a cell below the minimum
    IMBALANCE = "IMBALANCE"      # spread too wide
    THERMISTOR = "THERMISTOR"    # pinned sensor / sensors disagree


@dataclass
class Reading:
    """One decoded pack reading. Mirrors the firmware `BatteryData` struct.

    Populated by the functions in ``decode.py`` (apply_static / apply_live /
    apply_extended). A freshly-constructed Reading is ``valid == False`` until
    a static read succeeds.
    """

    # --- identity / static ---
    valid: bool = False
    model: str = ""
    command_version: str = ""          # "" = standard, "F0513" = older generation
    rom_id: bytes = b""                # 8-byte ROM ID
    msg: bytes = b""                   # raw 32-byte "battery message" frame
    raw_model: bytes = b""             # raw MODEL_CMD payload (kept for re-decode)
    raw_live: bytes = b""              # raw READ_DATA payload (kept for re-decode)
    charge_count: int = 0
    locked: bool = False               # BMS internal lock, msg[20] low nibble > 0
    charger_locked: bool = False       # charger will refuse: nybble34 / CS0 / CS2
    error_code: int = 0                # msg[19]
    capacity_ah: float = 0.0
    battery_type: int = 0
    mfg_year: int = 0
    mfg_month: int = 0
    mfg_day: int = 0
    overload_pct: int = 0              # decoded from msg[25]
    overdischarge_pct: int = 0         # decoded from msg[24]
    health_est_pct: int = 0            # ESTIMATE from cycle count, not the BMS gauge

    # --- live ---
    pack_voltage: float = 0.0
    cell: List[float] = field(default_factory=lambda: [0.0] * 5)
    cell_diff: float = 0.0
    temp_cell: float = 0.0             # "Sensor 1", offset 14 (label unverified)
    temp_mosfet: float = -1.0          # "Sensor 2", offset 16 (-1 if unavailable)
    board_temp_valid: bool = False     # False = single-sensor read (F0513 cell path): ignore temp_mosfet

    # --- extended (D4/D6), read only on standard packs ---
    ext_valid: bool = False
    latched_fault: bool = False        # D6 0x58D/0x309 != 0 -> real fault, unlock won't hold
    soc_raw: int = 0                   # D4 0x150: charge level (SOC), NOT health
    od_event_count: int = 0            # D4 0x0BA: over-discharge event count
    ol_event_count: int = 0            # D4 0x08D: over-load event count
    od_wear_pct: int = 0               # SECONDARY/UNPROVEN
    ol_wear_pct: int = 0               # SECONDARY/UNPROVEN
    fault_marker_a: int = 0            # raw D6 0x58D
    fault_marker_b: int = 0            # raw D6 0x309
    asm_year: int = 0
    asm_month: int = 0
    asm_day: int = 0

    @property
    def is_f0513(self) -> bool:
        return self.command_version == "F0513"

    @property
    def rom_hex(self) -> str:
        """ROM ID as Makita's tool prints it: uppercase hex, no separators."""
        return self.rom_id.hex().upper()

    @property
    def serial_no(self) -> str:
        """Serial number = the ROM ID, as 16-char uppercase hex (Makita format)."""
        return self.rom_hex

    def mfg_date_iso(self) -> Optional[str]:
        if not self.mfg_year:
            return None
        if not valid_ymd(self.mfg_year, self.mfg_month, self.mfg_day):
            return "?"      # garbage ROM (all-FF) -> "?" not "2255-255-255" (ino: fmtPackDate)
        return f"{self.mfg_year:04d}-{self.mfg_month:02d}-{self.mfg_day:02d}"

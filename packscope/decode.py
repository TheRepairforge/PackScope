"""Frame decode, ported 1:1 from PocketOBI/PocketOBI.ino.

These functions are PURE: they take raw command payloads (the bytes the
firmware reads back over OneWire, which the PC gets verbatim through the
bridge) and fill a ``Reading``. No serial / OneWire I/O happens here, so
the whole decode is unit-testable without hardware.

Source of truth is the firmware, NOT makita_lxt.py: the firmware fixed the
temperature unit (1/10 K, not /100) and added the newer zones. References below
name the firmware SYMBOL (function) and/or the stable byte/nybble offset rather
than line numbers, which drift as PocketOBI.ino changes.
"""

from __future__ import annotations

from typing import Sequence

from .models import Reading


# ---------------------------------------------------------------------------
# Low-level helpers (PocketOBI.ino: nibbleSwap, le16, nybGet, csCalc).
# ---------------------------------------------------------------------------
def nibble_swap(b: int) -> int:
    """Swap the two nibbles of a byte (ino: nibbleSwap)."""
    b &= 0xFF
    return ((b & 0xF0) >> 4) | ((b & 0x0F) << 4)


def le16(buf: Sequence[int], idx: int) -> int:
    """Little-endian u16 at ``idx`` (ino: le16)."""
    return buf[idx] | (buf[idx + 1] << 8)


def nyb_get(d: Sequence[int], n: int) -> int:
    """Read 4-bit nybble ``n`` from a byte buffer (ino: nybGet)."""
    byte = d[n >> 1]
    return (byte >> 4) & 0x0F if (n & 1) else (byte & 0x0F)


def cs_calc(d: Sequence[int], s: int, e: int) -> int:
    """Makita checksum: low nibble of the sum of nybbles [s, e] (ino: csCalc)."""
    total = 0
    for i in range(s, e + 1):
        total += nyb_get(d, i)
    return total & 0x0F


# Charger-lock cause masks (ino: enum LF_CS0/LF_CS2/LF_N34/LF_CS1).
LF_CS0 = 0x01
LF_CS2 = 0x02
LF_N34 = 0x04
LF_CS1 = 0x08


def lock_causes(frame: Sequence[int]) -> int:
    """Which charger-lock conditions a 32-byte frame trips (ino: lockCauses)."""
    c = 0
    if nyb_get(frame, 41) != cs_calc(frame, 0, 15):
        c |= LF_CS0
    if nyb_get(frame, 42) != cs_calc(frame, 16, 31):
        c |= LF_CS1
    if nyb_get(frame, 43) != cs_calc(frame, 32, 40):
        c |= LF_CS2
    if nyb_get(frame, 34) != 0:
        c |= LF_N34
    return c


def nyb_set(d: bytearray, n: int, v: int) -> None:
    """Write 4-bit nybble ``n`` into a byte buffer (ino: nybSet)."""
    v &= 0x0F
    if n & 1:
        d[n >> 1] = (d[n >> 1] & 0x0F) | (v << 4)
    else:
        d[n >> 1] = (d[n >> 1] & 0xF0) | v


def build_repaired_frame(frame: Sequence[int]) -> bytes:
    """Return a repaired copy of a 32-byte frame (ino: buildRepairedFrame).

    Clears ONLY the charger-lock nybble (34) and recomputes the three primary
    checksums (CS0/CS1/CS2). The failure code (nybble 40) and everything else are
    left untouched — we never force a genuinely-dead pack back into service. This
    is a clean-room reimplementation of the same facts used on-device.
    """
    out = bytearray(bytes(frame)[:32])
    nyb_set(out, 34, 0)                      # charger lock -> unlocked
    nyb_set(out, 41, cs_calc(out, 0, 15))    # CS0
    nyb_set(out, 42, cs_calc(out, 16, 31))   # CS1
    nyb_set(out, 43, cs_calc(out, 32, 40))   # CS2
    return bytes(out)


# Notable nybbles in the 32-byte static frame (for the Compare frame-diff).
NYBBLE_LABELS = {
    34: "charger lock (N34)",
    40: "failure code",
    41: "CS0 checksum",
    42: "CS1 checksum",
    43: "CS2 checksum",
    62: "CS3 checksum",
    63: "CS4 checksum",
}


def frame_diff(a: Sequence[int], b: Sequence[int]) -> list:
    """Per-nybble diff of two 32-byte frames. Returns a list of
    ``(nybble_index, byte_index, old, new, label)`` for every nybble that changed.
    Used by the Compare view to investigate what the BMS rewrote between two reads
    (e.g. a pack that re-locks on charge)."""
    out = []
    n_nyb = min(len(a), len(b)) * 2
    for n in range(n_nyb):
        va, vb = nyb_get(a, n), nyb_get(b, n)
        if va != vb:
            out.append((n, n // 2, va, vb, NYBBLE_LABELS.get(n, f"byte {n // 2}")))
    return out


def is_printable_ascii(b: Sequence[int], n: int) -> bool:
    """True if the first ``n`` bytes are printable ASCII (ino, isPrintableAscii)."""
    return all(0x20 <= b[i] <= 0x7E for i in range(n))


def is_all_ff(b: Sequence[int]) -> bool:
    """True if every byte is 0xFF (a silent/no-answer read over the bridge).
    Used to tell a real 0x33 frame / D7 live read from "no answer" (ino: a read
    that returns all-FF is treated as absent — see readStaticInfo / readLiveData)."""
    return len(b) > 0 and all(x == 0xFF for x in b)


def _round5up(num: int, den: int) -> int:
    """Percentage rounded UP to a 5% step (ino: round5up), so any nonzero event count
    reads >= 5% rather than 0 (e.g. a count of 1 over 83 cycles = 5%). The 5% quantizer
    used for the OD/OL wear percentages."""
    if den == 0:
        return 0
    p = (num * 100) // den
    if p > 100:
        p = 100
    return ((p + 4) // 5) * 5


# ---------------------------------------------------------------------------
# Static info (MODEL_CMD + READ_MSG_CMD) -> readStaticInfo().
# ---------------------------------------------------------------------------
def apply_static_standard(r: Reading, model_payload: Sequence[int],
                          msg_payload: Sequence[int], rom_id: Sequence[int]) -> None:
    """Decode a standard (non-F0513) pack's static info into ``r``.

    Mirrors the standard branch of readStaticInfo(). The caller
    is responsible for having already decided this is a standard pack (model
    response is printable ASCII).
    """
    p = bytes(model_payload)
    r.command_version = ""
    r.model = p[:7].decode("ascii", errors="replace")

    msg = bytes(msg_payload)
    r.rom_id = bytes(rom_id[:8])
    r.msg = msg[:32]

    # chargeCount: nibble-swap of msg[26] (MSB) and msg[27] (LSB) (ino: readStaticInfo).
    swapped = (nibble_swap(msg[26]) << 8) | nibble_swap(msg[27])
    r.charge_count = swapped & 0x0FFF
    r.locked = (msg[20] & 0x0F) > 0
    r.charger_locked = lock_causes(msg) != 0
    r.error_code = msg[19]

    # Capacity (byte 16), two encodings (ino: readStaticInfo).
    cap_raw = msg[16]
    cap_sw = nibble_swap(cap_raw)
    if 1 <= cap_raw <= 8 and cap_sw > 60:
        r.capacity_ah = float(cap_raw)          # newer format: whole Ah
    else:
        r.capacity_ah = cap_sw / 10.0           # legacy format: tenths of an Ah

    r.battery_type = nibble_swap(msg[11])
    r.mfg_year = 2000 + r.rom_id[0]
    r.mfg_month = r.rom_id[1]
    r.mfg_day = r.rom_id[2]

    # Overload: msg[25] nibble-swapped, bit 0x20 = enabled, low 5 bits * 5%
    # (ino: readStaticInfo).
    ol = nibble_swap(msg[25])
    r.overload_pct = (ol & 0x1F) * 5 if (ol & 0xE0) else 0
    # Over-discharge: msg[24], inverted high nibble, step 5.33% (ino: readStaticInfo).
    od_nib = ((~msg[24]) & 0xFF) >> 4
    r.overdischarge_pct = int(od_nib * 5.33 + 0.5)
    # SoH estimate from cycle count (ino: readStaticInfo, healthEstPct).
    h = 100 - int(r.charge_count / 8.96 + 0.5)
    r.health_est_pct = max(0, min(100, h))

    r.valid = True


def apply_static_f0513(r: Reading, model: str) -> None:
    """Set the fields for an older F0513 pack (ino: readStaticInfo, F0513 branch).

    ``model`` is the already-decoded "BL...." string (from the raw 0x31 path,
    handled in the protocol layer). Diagnostics are limited on this generation.
    """
    r.command_version = "F0513"
    r.model = model
    r.charge_count = 0
    r.locked = False
    r.charger_locked = False
    r.error_code = 0
    r.capacity_ah = 0.0
    r.battery_type = 0
    r.overload_pct = 0
    r.overdischarge_pct = 0
    r.health_est_pct = 0
    r.mfg_year = r.mfg_month = r.mfg_day = 0
    r.rom_id = b"\x00" * 8
    r.msg = b"\x00" * 32
    r.valid = True


def f0513_model_string(byte1: int, byte2: int) -> str:
    """Build the F0513 model string 'BL{b2:X}{b1:X}' (ino: readStaticInfo, F0513 branch)."""
    return f"BL{byte2:X}{byte1:X}"


# ---------------------------------------------------------------------------
# Live data (READ_DATA_CMD) -> readLiveData(), standard path.
# ---------------------------------------------------------------------------
def apply_live_standard(r: Reading, payload: Sequence[int]) -> None:
    """Decode the standard live-data payload into ``r`` (ino: readLiveData, standard path)."""
    p = payload
    r.pack_voltage = le16(p, 0) / 1000.0
    r.cell = [le16(p, 2 + 2 * i) / 1000.0 for i in range(5)]
    r.cell_diff = max(r.cell) - min(r.cell)
    # Temperature is 1/10 K: T_C = raw/10 - 273.15 (ino: readLiveData). Confirmed on
    # real packs; a dead thermistor pins near raw 2430 (= -30 C).
    r.temp_cell = le16(p, 14) / 10.0 - 273.15
    r.temp_mosfet = le16(p, 16) / 10.0 - 273.15
    r.board_temp_valid = True         # D7 path exposes both sensors (ino: readLiveData)


def apply_live_f0513(r: Reading, cells_raw: Sequence[int], temp_raw: int) -> None:
    """Decode single-sensor cell data (ino: readF0513Cells).

    Used for genuine F0513 packs AND as the live fallback for old standard packs
    whose D7 read is silent. ``cells_raw`` is the 5 per-cell u16 values (mV),
    ``temp_raw`` the raw cell-temperature u16.
    """
    r.cell = [cells_raw[i] / 1000.0 for i in range(5)]
    r.pack_voltage = sum(r.cell)
    r.cell_diff = max(r.cell) - min(r.cell)
    # Same 1/10 K encoding as the standard path (ino: readF0513Cells). Confirmed on a
    # real F0513 pack (raw 2972 -> 24 C; a /100 decode gives an implausible 29.7 C).
    r.temp_cell = temp_raw / 10.0 - 273.15
    r.temp_mosfet = -1.0               # no board sensor on the single-sensor path
    r.board_temp_valid = False         # single sensor: ignore temp_mosfet


# ---------------------------------------------------------------------------
# Extended D4/D6 diagnostics -> readExtended().
# ---------------------------------------------------------------------------
def apply_extended(r: Reading, fault_a: int, fault_b: int,
                   asm: Sequence[int], soc: Sequence[int],
                   od_event: int, ol_block: Sequence[int]) -> None:
    """Decode the extended D4/D6 reads into ``r`` (ino: readExtended).

    - ``fault_a`` / ``fault_b`` : raw D6 0x58D / 0x309 (latched-fault markers).
    - ``asm``    : 3 bytes, D4 0x000-0x002 (assembly date YY MM DD, year binary).
    - ``soc``    : 2 bytes, D4 0x150 (charge level, u16 LE).
    - ``od_event``: D4 0x0BA (over-discharge event count).
    - ``ol_block``: 7 bytes, D4 0x08D (over-load block, bit-packed).

    Not applicable to F0513 packs (caller should skip; kept defensive here).
    """
    if r.is_f0513:
        return

    r.fault_marker_a = fault_a
    r.fault_marker_b = fault_b
    r.asm_year, r.asm_month, r.asm_day = asm[0], asm[1], asm[2]

    r.soc_raw = le16(soc, 0)
    r.od_event_count = od_event

    # Over-load block: two packed counters summed (ino: readExtended).
    ol = ol_block
    counter_c = (((ol[4] & 0x03) << 8) | ol[3]) + ((ol[0] >> 6) | ((ol[1] & 0x3F) << 2))
    counter_e = (ol[5] >> 4) | ((ol[6] & 0x0F) << 4)
    r.ol_event_count = counter_c + counter_e

    # Latched real fault: a marker set to a real (non 0 / non 0xFF) value.
    r.latched_fault = ((fault_a not in (0, 0xFF)) or (fault_b not in (0, 0xFF)))

    # Over-discharge % / over-load % = round5up(count*100/charges).
    r.od_wear_pct = _round5up(r.od_event_count, r.charge_count)
    r.ol_wear_pct = _round5up(r.ol_event_count, r.charge_count)
    r.ext_valid = True

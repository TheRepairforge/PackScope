"""Decode tests.

Two kinds of vectors:
  * REAL ANCHORS  — values captured from actual packs (BL1860B / BL1830B /
    BL1850B) during PocketOBI bench validation.
  * ROUND-TRIP    — for fields where only the decoded value is documented
    (not the raw bytes), we encode the value with the inverse transform and
    assert the decode returns it. This proves the port matches the firmware's
    math; byte-exact golden frames get added once captured from hardware.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packscope import decode
from packscope.models import Reading


def le(v):
    """2-byte little-endian, as the firmware's le16 reads it."""
    return bytes([v & 0xFF, (v >> 8) & 0xFF])


def build_live(pack_mv, cells_mv, t1_raw, t2_raw, mid=0):
    """Assemble a 29-byte standard READ_DATA payload."""
    p = bytearray(29)
    p[0:2] = le(pack_mv)
    for i in range(5):
        p[2 + 2 * i:4 + 2 * i] = le(cells_mv[i])
    p[12:14] = le(mid)
    p[14:16] = le(t1_raw)
    p[16:18] = le(t2_raw)
    return bytes(p)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------
def test_nibble_swap():
    assert decode.nibble_swap(0xC3) == 0x3C
    assert decode.nibble_swap(0xE1) == 0x1E
    assert decode.nibble_swap(0x00) == 0x00
    assert decode.nibble_swap(0x82) == 0x28


def test_round5up_matches_vendor_pct():
    # Makita OD/OL% = round5up(count*100/charges); calibrated on the vendor tool's readout.
    assert decode._round5up(1, 83) == 5     # 5Ah: 1.2% -> 5 (not floored to 0)
    assert decode._round5up(1, 40) == 5     # 6Ah: 2.5% -> 5
    assert decode._round5up(0, 40) == 0     # no event -> 0
    assert decode._round5up(0, 83) == 0
    assert decode._round5up(5, 100) == 5    # exact 5% stays 5
    assert decode._round5up(6, 100) == 10   # 6% -> 10 (ceil to next step)
    assert decode._round5up(3, 0) == 0      # den 0 guard
    assert decode._round5up(300, 100) == 100  # capped


def test_le16():
    assert decode.le16(le(20457), 0) == 20457
    assert decode.le16(le(2430), 0) == 2430


def test_checksum_and_lock_causes():
    # An all-zero frame: every checksum is 0 and matches -> no lock cause.
    frame = bytearray(32)
    assert decode.lock_causes(frame) == 0

    # Trip the charger-lock nybble 34 (byte 17 low nibble). It lives in the
    # CS2 range (nybbles 32-40), so it also invalidates CS2 -> both flags.
    frame[17] = 0x01  # nybble 34 = 1
    causes = decode.lock_causes(frame)
    assert causes & decode.LF_N34
    assert causes & decode.LF_CS2

    # A clean CS0 break: change a nybble in [0,15] without fixing its checksum.
    frame2 = bytearray(32)
    frame2[0] = 0x05  # nybble 0 = 5, cs(0,15) becomes 5 != stored 0
    assert decode.lock_causes(frame2) & decode.LF_CS0


# ---------------------------------------------------------------------------
# Live data — REAL ANCHORS (raw sensor values captured on hardware)
# ---------------------------------------------------------------------------
def test_live_bl1860b_healthy():
    # BL1860B, healthy: pack 20.457 V, 5 cells 4.096 V, T raw 3053 / 3061.
    r = Reading()
    decode.apply_live_standard(r, build_live(20457, [4096] * 5, 3053, 3061))
    assert r.pack_voltage == pytest.approx(20.457, abs=1e-3)
    assert all(c == pytest.approx(4.096, abs=1e-3) for c in r.cell)
    assert r.cell_diff == pytest.approx(0.0, abs=1e-6)
    # 1/10 K decode: raw/10 - 273.15
    assert r.temp_cell == pytest.approx(32.15, abs=0.01)
    assert r.temp_mosfet == pytest.approx(32.95, abs=0.01)


def test_live_bl1830b_dead_thermistor():
    # BL1830B, deep-discharged + faulty thermistor: T1 raw 2430 = -30 C pinned.
    r = Reading()
    decode.apply_live_standard(r, build_live(15680, [3130] * 5, 2430, 3085))
    assert r.pack_voltage == pytest.approx(15.680, abs=1e-3)
    assert r.temp_cell == pytest.approx(-30.15, abs=0.01)   # pinned = faulty NTC
    assert r.temp_mosfet == pytest.approx(35.35, abs=0.01)


def test_live_bl1850b_balanced():
    # BL1850B, locked pack: cells balanced ~3.72 V, temps normal 26/27 C.
    r = Reading()
    decode.apply_live_standard(r, build_live(18570, [3720] * 5, 2992, 3002))
    assert r.pack_voltage == pytest.approx(18.570, abs=1e-3)
    assert r.temp_cell == pytest.approx(26.05, abs=0.05)
    assert r.temp_mosfet == pytest.approx(27.05, abs=0.05)
    assert r.cell_diff == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Static info — REAL ANCHORS + ROUND-TRIP
# ---------------------------------------------------------------------------
def test_static_capacity_real_anchors():
    # Capacity byte 16 -> Ah, confirmed on 3 packs (BMS map): C3=6.0, E1=3.0,
    # and 5.0 Ah encodes as nibble-swap(50)=0x23.
    for cap_byte, expected in [(0xC3, 6.0), (0xE1, 3.0), (0x23, 5.0)]:
        r = Reading()
        msg = bytearray(32)
        msg[16] = cap_byte
        decode.apply_static_standard(r, b"BL1860B", msg, bytes(8))
        assert r.capacity_ah == pytest.approx(expected), f"cap byte {cap_byte:#x}"


def test_static_rom_and_date_real_anchor():
    # Real ROM ID for the BL1860B: 1807050214BC4E37 -> mfg 2024-07-05.
    rom = bytes.fromhex("1807050214BC4E37")
    r = Reading()
    decode.apply_static_standard(r, b"BL1860B", bytearray(32), rom)
    assert r.rom_hex == "1807050214BC4E37"
    assert r.serial_no == "1807050214BC4E37"
    assert (r.mfg_year, r.mfg_month, r.mfg_day) == (2024, 7, 5)
    assert r.mfg_date_iso() == "2024-07-05"


def test_static_model_ascii():
    r = Reading()
    decode.apply_static_standard(r, b"BL1860B\x00\x00", bytearray(32), bytes(8))
    assert r.model == "BL1860B"
    assert not r.is_f0513


def test_static_lock_nibble_real_anchor():
    # msg[20] low nibble > 0 => locked (=3 on the locked BL1850B, 0 otherwise).
    r_locked = Reading()
    msg = bytearray(32)
    msg[20] = 0x03
    decode.apply_static_standard(r_locked, b"BL1850B", msg, bytes(8))
    assert r_locked.locked is True

    r_unlocked = Reading()
    decode.apply_static_standard(r_unlocked, b"BL1860B", bytearray(32), bytes(8))
    assert r_unlocked.locked is False


def test_static_charge_count_roundtrip():
    # Charge count 40 (BL1860B) = swapped nibble-swap of msg[26]/msg[27].
    msg = bytearray(32)
    msg[26] = decode.nibble_swap(0x00)   # MSB
    msg[27] = decode.nibble_swap(0x28)   # LSB -> 0x28 = 40
    r = Reading()
    decode.apply_static_standard(r, b"BL1860B", msg, bytes(8))
    assert r.charge_count == 40


def test_static_f0513():
    r = Reading()
    model = decode.f0513_model_string(0x51, 0x30)  # BL{b2}{b1}
    decode.apply_static_f0513(r, model)
    assert r.is_f0513
    assert r.model.startswith("BL")
    assert r.capacity_ah == 0.0


def test_f0513_cells_temp_unit_is_tenth_kelvin():
    # #38: a real 2010 F0513 pack read raw 2972 -> 24.0 C (not 29.7 with the old /100).
    r = Reading()
    decode.apply_live_f0513(r, [3600] * 5, 2972)
    assert r.pack_voltage == pytest.approx(18.0, abs=1e-3)     # 5 x 3.600 V
    assert r.temp_cell == pytest.approx(24.05, abs=0.01)  # 2972/10-273.15, shows 24 C
    assert r.temp_mosfet == -1.0
    assert r.board_temp_valid is False                         # single sensor (#38)


def test_board_temp_valid_flag_by_path():
    # D7 (two-sensor) sets the flag; the single-sensor cell path clears it.
    r_std = Reading()
    decode.apply_live_standard(r_std, build_live(20457, [4096] * 5, 3053, 3061))
    assert r_std.board_temp_valid is True
    r_ss = Reading()
    decode.apply_live_f0513(r_ss, [3600] * 5, 2972)
    assert r_ss.board_temp_valid is False


def test_is_all_ff():
    assert decode.is_all_ff(b"\xff" * 29) is True
    assert decode.is_all_ff(bytes([0xFF, 0xFF, 0x00])) is False
    assert decode.is_all_ff(b"") is False


def test_mfg_date_invalid_shows_question_mark():
    # An all-0xFF ROM -> mfg 2255/255/255: must read "?" not "2255-255-255" (#38).
    r = Reading()
    decode.apply_static_standard(r, b"BL1860B", bytearray(32), bytes([0xFF] * 8))
    assert r.mfg_date_iso() == "?"


# ---------------------------------------------------------------------------
# Extended D4/D6
# ---------------------------------------------------------------------------
def test_extended_latched_fault_marker():
    # BL1850B: D6 0x58D=11, 0x309=72 -> latched real fault.
    r = Reading()
    r.valid = True
    decode.apply_extended(r, 0x0B, 0x48, [0, 0, 0], le(4434), 0, [0] * 7)
    assert r.latched_fault is True
    assert r.fault_marker_a == 0x0B and r.fault_marker_b == 0x48

    # Healthy / deep-discharged packs: markers 0 (or 0xFF) -> not latched.
    r2 = Reading()
    r2.valid = True
    decode.apply_extended(r2, 0x00, 0x00, [0, 0, 0], le(5243), 1, [0] * 7)
    assert r2.latched_fault is False


def test_extended_skipped_on_f0513():
    r = Reading()
    r.valid = True
    r.command_version = "F0513"
    decode.apply_extended(r, 0x0B, 0x48, [1, 1, 1], le(100), 5, [1] * 7)
    assert r.ext_valid is False
    assert r.latched_fault is False


def test_extended_overload_block_formula():
    # Deterministic round-trip of the bit-packed over-load decode (ino:1743).
    ol = [0x00, 0x00, 0x00, 0x05, 0x00, 0x00, 0x00]  # ol[3]=5 -> counter_c=5
    r = Reading()
    r.valid = True
    decode.apply_extended(r, 0, 0, [0, 0, 0], le(0), 0, ol)
    assert r.ol_event_count == 5

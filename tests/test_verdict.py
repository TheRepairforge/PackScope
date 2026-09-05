"""Verdict tests — 5-state logic, ported 1:1 from the firmware.

Ground truth (real packs on the bench):
  * BL1860B — healthy                                          -> HEALTHY
  * BL1830B — faulty thermistor pinned at raw ~2430 (-30 C)    -> REAL_FAULT (red)
  * BL1850B — latched marker set (soft, empirical)             -> SUSPECT (orange)
  * false lock (healthy cells/temps, charger lock, no latched) -> REPAIRABLE
Latched and sensor-spread are SOFT signals -> orange SUSPECT, not red.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packscope.models import HwFault, Reading, Verdict
from packscope.verdict import (
    cell_spread_grade,
    compute_verdict,
    find_hardware_fault,
    health_band,
    thermistor_fault,
    thermistor_suspect,
    verdict_label,
)


def test_cell_spread_grade_bound_to_firmware_thresholds():
    assert cell_spread_grade(0.01) == ("EXCELLENT", "green")
    assert cell_spread_grade(0.08) == ("GOOD", "green")
    assert cell_spread_grade(0.20) == ("WARNING", "amber")   # >= DIFF_WARN (0.15)
    assert cell_spread_grade(0.35) == ("CRITICAL", "red")    # >= DIFF_BAD (0.30)


def test_health_band():
    assert health_band(100) == "green"
    assert health_band(80) == "green"     # boundary
    assert health_band(79) == "amber"
    assert health_band(50) == "amber"     # boundary
    assert health_band(49) == "red"
    assert health_band(0) == "red"


def make_reading(cells, t1, t2, locked=False, charger_locked=False,
                 latched=False, valid=True):
    r = Reading(valid=valid)
    r.cell = list(cells)
    r.cell_diff = max(r.cell) - min(r.cell)
    r.pack_voltage = sum(r.cell)
    r.temp_cell = t1
    r.temp_mosfet = t2
    r.board_temp_valid = True   # two-sensor D7 read (single-sensor packs set this False)
    r.locked = locked
    r.charger_locked = charger_locked
    r.latched_fault = latched
    return r


def test_verdict_unknown_when_invalid():
    assert compute_verdict(Reading()) == Verdict.UNKNOWN


def test_verdict_unknown_when_no_live_data():
    # valid=True (static decoded) but no live read yet -> pack ~0 V. Must be UNKNOWN,
    # never HEALTHY (firmware #38 defence-in-depth guard).
    r = make_reading([0.0] * 5, 25.0, 26.0)
    assert compute_verdict(r) == Verdict.UNKNOWN


def test_bl1860b_healthy():
    r = make_reading([4.096] * 5, 32.15, 32.95)
    assert compute_verdict(r) == Verdict.HEALTHY
    assert find_hardware_fault(r)[0] == HwFault.NONE


def test_bl1830b_thermistor_pinned_is_real_fault():
    # A sensor pinned at -30 C = CONFIRMED fault (red), not a suspicion.
    r = make_reading([3.13] * 5, -30.15, 35.35)
    assert thermistor_fault(r) is True
    assert thermistor_suspect(r) is False
    assert compute_verdict(r) == Verdict.REAL_FAULT
    assert find_hardware_fault(r)[0] == HwFault.THERMISTOR


def test_bl1850b_latched_is_suspect_not_red():
    # Cells balanced, temps normal, but a latched marker -> orange SUSPECT.
    r = make_reading([3.72] * 5, 26.05, 27.05, locked=True, latched=True)
    assert compute_verdict(r) == Verdict.SUSPECT
    assert verdict_label(Verdict.SUSPECT) == "POSSIBLE HW FIX"


def test_sensor_spread_is_suspect():
    # Both sensors in range but disagreeing by > TEMP_SPREAD_BAD (10 C) -> soft
    # SUSPECT (not red). Here 40 C apart.
    r = make_reading([3.9] * 5, 20.0, 60.0)
    assert thermistor_fault(r) is False
    assert thermistor_suspect(r) is True
    assert compute_verdict(r) == Verdict.SUSPECT


def test_false_lock_is_repairable():
    r = make_reading([3.80] * 5, 25.0, 26.0, charger_locked=True, latched=False)
    assert compute_verdict(r) == Verdict.REPAIRABLE
    assert verdict_label(Verdict.REPAIRABLE) == "UNLOCK"


def test_lock_plus_latched_is_suspect():
    # Latched is checked before the lock -> SUSPECT wins over REPAIRABLE.
    r = make_reading([3.8] * 5, 25.0, 26.0, charger_locked=True, latched=True)
    assert compute_verdict(r) == Verdict.SUSPECT


def test_dead_cell_is_real_fault():
    # A cell genuinely below the dead floor (< CELL_V_DEAD 2.0 V) -> FAULT, and the
    # weak-cell path fires before imbalance (D13).
    r = make_reading([3.9, 3.9, 1.5, 3.9, 3.9], 25.0, 26.0)
    assert compute_verdict(r) == Verdict.REAL_FAULT
    fault, group, _ = find_hardware_fault(r)
    assert fault == HwFault.WEAK_CELL and group == 3


def test_uniform_over_discharge_is_suspect_not_fault():
    # Uniform ~2.2 V/cell, no imbalance: recoverable over-discharge (D13) -> orange
    # SUSPECT, NOT red, and it does NOT register as a hardware fault (unlock stays open).
    r = make_reading([2.2] * 5, 25.0, 26.0)
    assert compute_verdict(r) == Verdict.SUSPECT
    assert find_hardware_fault(r)[0] == HwFault.NONE


def test_over_discharged_cell_with_imbalance_is_real_fault():
    # A single cell at 2.1 V (in the recoverable band) but far below the rest is a real
    # bad cell -> surfaces as an imbalance -> FAULT, independent of the absolute level (D13).
    r = make_reading([3.9, 3.9, 2.1, 3.9, 3.9], 25.0, 26.0)
    assert compute_verdict(r) == Verdict.REAL_FAULT
    assert find_hardware_fault(r)[0] == HwFault.IMBALANCE


def test_broken_sense_wire_detected_first():
    r = make_reading([3.9, 0.1, 3.9, 3.9, 3.9], 25.0, 26.0)
    fault, group, _ = find_hardware_fault(r)
    assert fault == HwFault.SENSE_WIRE and group == 2
    assert compute_verdict(r) == Verdict.REAL_FAULT


def test_imbalance_is_real_fault():
    r = make_reading([4.1, 4.1, 4.1, 4.1, 3.5], 25.0, 26.0)  # spread 0.6 > 0.30
    assert compute_verdict(r) == Verdict.REAL_FAULT
    assert find_hardware_fault(r)[0] == HwFault.IMBALANCE

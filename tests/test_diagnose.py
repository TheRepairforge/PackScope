"""Evidence-based diagnosis wording (observation / cause / check + context)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packscope.models import HwFault, Reading
from packscope.verdict import diagnose


def reading(cells, t1, t2, latched=False, od=0):
    r = Reading(valid=True)
    r.cell = list(cells)
    r.cell_diff = max(r.cell) - min(r.cell)
    r.pack_voltage = sum(r.cell)
    r.temp_cell = t1        # cell probe (sensor 1)
    r.temp_mosfet = t2      # board probe (sensor 2)
    r.board_temp_valid = True   # two-sensor D7 read
    r.latched_fault = latched
    r.od_event_count = od
    return r


def test_pinned_board_probe_is_named():
    d = diagnose(reading([4.0] * 5, 29.0, -30.0))
    assert d["hw_fault"] == HwFault.THERMISTOR
    assert d["color"] == "red"
    assert "board probe" in d["observation"]
    assert "-30" in d["observation"]
    assert "board thermistor" in d["cause"]
    # never a bare "replace the thermistor" order
    assert "re-read at room temperature" in d["check"]


def test_gap_cold_vs_hot_wording():
    cold = diagnose(reading([4.0] * 5, 29.0, 62.0), recently_used=False)
    assert cold["color"] == "orange"
    assert cold["title"] == "Cell and board temperatures disagree"
    assert "external thermometer" in cold["check"]

    hot = diagnose(reading([4.0] * 5, 29.0, 62.0), recently_used=True)
    assert "rest to room temperature" in hot["check"]
    assert "charge or heavy use" in hot["cause"]


def test_warm_info_is_advisory_not_a_fault():
    d = diagnose(reading([4.0] * 5, 50.0, 50.0))       # both warm, no gap
    assert d["thermistor_state"] == 0
    assert d["info"] and "warm" in d["info"]


def test_latched_why_over_discharge():
    d = diagnose(reading([3.8] * 5, 25.0, 26.0, latched=True, od=5))
    assert d["color"] == "orange"
    assert "over-discharge" in d["observation"]
    assert "re-locks" in d["check"]


def test_three_part_keys_present_for_all():
    for r in (reading([4.0] * 5, 25.0, 26.0),                  # healthy
              reading([4.1, 4.1, 4.1, 4.1, 3.4], 25.0, 26.0),  # imbalance
              reading([3.8] * 5, 25.0, 26.0, latched=True)):   # latched
        d = diagnose(r)
        for k in ("observation", "cause", "check", "title", "color", "gate_hint"):
            assert d[k], f"{k} empty"

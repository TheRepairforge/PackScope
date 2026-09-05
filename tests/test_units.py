"""Temperature unit formatting."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date

from packscope.units import fmt_delta, fmt_temp, fmt_wear, pack_age_years


def test_fmt_temp_celsius_default():
    assert fmt_temp(32) == "32 °C"
    assert fmt_temp(-30, "C") == "-30 °C"


def test_fmt_temp_fahrenheit():
    assert fmt_temp(0, "F") == "32 °F"
    assert fmt_temp(100, "F") == "212 °F"


def test_fmt_delta_scales_without_offset():
    assert fmt_delta(25, "C") == "25 °C"
    assert fmt_delta(25, "F") == "45 °F"     # a 25 K delta = 45 °F delta (no +32)


def test_fmt_wear_event_count():
    assert fmt_wear(True, 3) == "3×"
    assert fmt_wear(True, 0) == "0×"        # clean, read succeeded


def test_fmt_wear_ext_invalid_is_dash():
    # count unknown (extended read didn't survive the bridge)
    assert fmt_wear(False, 0) == "—"
    assert fmt_wear(False, 5) == "—"


def test_pack_age_years():
    today = date(2026, 8, 15)
    assert pack_age_years("2018-07-05", today) == 8       # birthday passed
    assert pack_age_years("2018-12-25", today) == 7       # birthday not yet
    assert pack_age_years("2026-08-15", today) == 0       # today
    assert pack_age_years("2027-01-01", today) == 0       # future clamps to 0


def test_pack_age_years_missing_or_bad():
    today = date(2026, 8, 15)
    assert pack_age_years(None, today) is None
    assert pack_age_years("", today) is None
    assert pack_age_years("not-a-date", today) is None

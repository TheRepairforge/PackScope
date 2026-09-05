"""Temperature unit formatting (the Settings temperature-unit preference).

Values are stored/decoded in Celsius everywhere; only the DISPLAY converts.
``fmt_temp`` formats an absolute temperature; ``fmt_delta`` a difference (a
spread), where °F scales by 9/5 with NO offset.
"""

from __future__ import annotations


def fmt_temp(celsius: float, unit: str = "C") -> str:
    if unit == "F":
        return f"{celsius * 9 / 5 + 32:.0f} °F"
    return f"{celsius:.0f} °C"


def fmt_delta(celsius_delta: float, unit: str = "C") -> str:
    if unit == "F":
        return f"{celsius_delta * 9 / 5:.0f} °F"
    return f"{celsius_delta:.0f} °C"


def fmt_wear(ext_valid: bool, count: int) -> str:
    """Format a BMS wear counter (over-discharge / over-load) as a count of events,
    e.g. ``"1×"`` = "protection tripped once". ``"—"`` when the extended D4 read did
    not come back (over the bridge TESTMODE may not persist, so ``ext_valid`` can be
    False). The protection THRESHOLD is deliberately NOT shown here — it is a static
    BMS config value, not a wear signal, and it confused the reading; it stays in the
    History technical inspector. Mirrors the device Health page's event counters."""
    return f"{count}×" if ext_valid else "—"


def pack_age_years(iso_date, today) -> "int | None":
    """Whole years between an ISO 'YYYY-MM-DD' production date and ``today`` (a
    ``datetime.date``). ``None`` if the date is missing or unparseable. ``today`` is
    passed in (not read here) so the function stays pure and testable."""
    if not iso_date:
        return None
    try:
        y, m, d = (int(x) for x in iso_date.split("-"))
    except (ValueError, AttributeError):
        return None
    years = today.year - y - ((today.month, today.day) < (m, d))
    return max(0, years)


def human_dt(iso: str) -> str:
    """ISO '2026-08-06T10:00:00' -> a human '10:00 on 2026-08-06'."""
    if not iso:
        return ""
    if "T" in iso:
        d, t = iso.split("T", 1)
        return f"{t[:5]} on {d}"
    return iso


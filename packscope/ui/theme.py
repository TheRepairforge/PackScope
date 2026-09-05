"""Colors and helpers for the UI — a swappable palette (dark default, light option).

All colour names are module globals set by ``apply(mode)``. UI code reads
``theme.X`` at widget-creation time, so switching mode + rebuilding the screens
re-themes everything. The verdict/cell helpers read the current globals at call
time, so they follow the active palette too.
"""

from __future__ import annotations

from ..models import (
    CELL_V_CRIT,
    CELL_V_MIN,
    DIFF_BAD,
    DIFF_WARN,
    Verdict,
)

FONT_FAMILY = "Segoe UI"
MONO_FAMILY = "Consolas"

# Four deliberate surface levels: page < sidebar < card < inner section.
_DARK = dict(
    BG="#0B1017", SIDEBAR="#111A24", PANEL="#151E29", PANEL2="#1B2735",
    RAISED="#243240", BORDER="#223040", BORDER2="#2E3E50",
    TEXT="#F1F5F9", MUTED="#8A9AAF", DIM="#5C6675",
    ACCENT="#22C7E8", ACCENT_HOVER="#45D6F2", ACCENT_DIM="#115A6B", ACCENT_INK="#04202A",
    MAKITA_TEAL="#00A99D",
    GREEN="#2AC27E", GREEN_BG="#10251C", AMBER="#F2B84B", AMBER_BG="#251E10",
    ORANGE="#F26622", ORANGE_BG="#25160E", RED="#F05D5E", RED_BG="#251314",
)
_LIGHT = dict(
    BG="#EEF1F4", SIDEBAR="#E3E8EE", PANEL="#FFFFFF", PANEL2="#E4EAF1",
    RAISED="#D5DEE8", BORDER="#D3DAE2", BORDER2="#B7C1CC",
    TEXT="#1C2733", MUTED="#556172", DIM="#7E8B99",
    ACCENT="#0E9AB8", ACCENT_HOVER="#12AACB", ACCENT_DIM="#5FB8CC", ACCENT_INK="#FFFFFF",
    MAKITA_TEAL="#00897E",
    GREEN="#1A8F5A", GREEN_BG="#E6F5EC", AMBER="#B9860C", AMBER_BG="#F7F0DC",
    ORANGE="#D1561A", ORANGE_BG="#FBEADF", RED="#C23B3B", RED_BG="#FBE9E9",
)
_PALETTES = {"dark": _DARK, "light": _LIGHT}
mode = "dark"


def apply(new_mode: str) -> None:
    """Set the active palette. UI must be rebuilt afterwards to take effect."""
    global mode
    mode = new_mode if new_mode in _PALETTES else "dark"
    globals().update(_PALETTES[mode])


apply("dark")   # default


def verdict_color(v: Verdict) -> str:
    return {Verdict.HEALTHY: GREEN, Verdict.REPAIRABLE: AMBER,
            Verdict.SUSPECT: ORANGE, Verdict.REAL_FAULT: RED}.get(v, DIM)


def verdict_bg(v: Verdict) -> str:
    return {Verdict.HEALTHY: GREEN_BG, Verdict.REPAIRABLE: AMBER_BG,
            Verdict.SUSPECT: ORANGE_BG, Verdict.REAL_FAULT: RED_BG}.get(v, PANEL2)


def cell_color(v: float, mn: float, diff: float) -> str:
    """Bar color for a cell, mirroring the firmware/mockup rules."""
    if v < CELL_V_MIN or v < CELL_V_CRIT:
        return RED
    if abs(v - mn) < 1e-6 and diff > DIFF_WARN:
        return RED if diff > DIFF_BAD else AMBER
    return GREEN

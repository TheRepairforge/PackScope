"""Verdict + hardware-fault classification, ported 1:1 from PocketOBI.ino.

Keeping this identical to the firmware is the whole point: the desk app must
predict exactly what the on-device tool predicts. Mirrors thermistorFault()/
thermistorSuspect()/findHardwareFault()/computeVerdict()/verdictText() and the
staged Repair-wizard diagnosis (drawWizardDiag) — same thresholds, same wording.

Five-state verdict (firmware enum Verdict):
  HEALTHY (green) · REPAIRABLE=UNLOCK (yellow, false lock) · SUSPECT (orange, soft
  empirical hint: latched marker or sensor spread) · REAL_FAULT=HARDWARE FIX (red,
  confirmed hardware fault) · UNKNOWN (no pack).
"""

from __future__ import annotations

from typing import Optional, Tuple

from . import i18n
from .decode import LF_CS0, LF_CS1, LF_CS2, LF_N34, lock_causes
from .models import (
    CELL_V_DEAD,
    CELL_V_MIN,
    CELL_V_SENSE,
    DIFF_BAD,
    DIFF_WARN,
    TEMP_MAX_PLAUS,
    TEMP_MIN_PLAUS,
    TEMP_SPREAD_BAD,
    TEMP_WARM_C,
    HwFault,
    Reading,
    Verdict,
)


# ---------------------------------------------------------------------------
# Temperature / thermistor (firmware: tempImplausible / thermistorFault /
# thermistorSuspect).
# ---------------------------------------------------------------------------
def temp_implausible(t: float) -> bool:
    return t < TEMP_MIN_PLAUS or t > TEMP_MAX_PLAUS


def thermistor_fault(r: Reading) -> bool:
    """CONFIRMED thermistor fault: a sensor pinned OUTSIDE the plausible window
    (validated on dead-NTC packs, ~ -30 C). Red verdict, gates the unlock.
    Not applicable to F0513. The board sensor is only present on the D7 path; on a
    single-sensor read temp_mosfet is a sentinel and must not be tested."""
    if r.is_f0513:
        return False
    return temp_implausible(r.temp_cell) or \
        (r.board_temp_valid and temp_implausible(r.temp_mosfet))


def thermistor_suspect(r: Reading) -> bool:
    """SUSPECTED thermistor issue: both sensors in range but disagreeing by more
    than TEMP_SPREAD_BAD. Empirical/unproven -> soft orange SUSPECT signal only,
    does NOT gate the unlock. A pinned sensor is a fault, not a suspicion."""
    if r.is_f0513:
        return False
    if not r.board_temp_valid:      # single sensor -> nothing to compare against
        return False
    if temp_implausible(r.temp_cell) or temp_implausible(r.temp_mosfet):
        return False
    return abs(r.temp_mosfet - r.temp_cell) > TEMP_SPREAD_BAD


# ---------------------------------------------------------------------------
# Hardware fault classification (firmware: findHardwareFault).
# ---------------------------------------------------------------------------
def find_hardware_fault(r: Reading) -> Tuple[HwFault, int, Optional[str]]:
    """Stage-1 hardware fault, evaluated BEFORE the lock state. Feasibility-first:
    returns the FIRST fault as ``(fault, group, action)`` (1-based cell index, 0
    if not cell-specific). Only a CONFIRMED (pinned) thermistor fault counts here."""
    is_f0513 = r.is_f0513

    if not is_f0513 and r.pack_voltage > 10.0:
        for i in range(5):
            if r.cell[i] < CELL_V_SENSE:
                return HwFault.SENSE_WIRE, i + 1, f"Resolder sense wire on group {i + 1}"

    # Weak / dead group: a cell genuinely below the dead floor (but not a broken sense
    # line). The [CELL_V_DEAD, CELL_V_MIN) band is a recoverable over-discharge, not a
    # hardware fault, so it does NOT land here and does NOT block the unlock.
    for i in range(5):
        if CELL_V_SENSE <= r.cell[i] < CELL_V_DEAD:
            return HwFault.WEAK_CELL, i + 1, f"Measure group {i + 1} with a DMM"

    if r.cell_diff > DIFF_BAD:
        lo, mn = 0, 9.0
        for i in range(5):
            if 0.1 < r.cell[i] < mn:
                mn, lo = r.cell[i], i
        return HwFault.IMBALANCE, lo + 1, f"Group {lo + 1} low: slow-charge, recheck"

    if thermistor_fault(r):
        # Wording matches the firmware S_ACT_THERM: on a single at-rest read we can
        # only suggest a check, not conclude "replace" (a pinned probe can be a dead
        # NTC OR a genuinely hot pack just off a tool).
        return HwFault.THERMISTOR, 0, "Re-read cold, then check NTC"

    return HwFault.NONE, 0, None


# ---------------------------------------------------------------------------
# Verdict (firmware: computeVerdict) — order matters.
# ---------------------------------------------------------------------------
def compute_verdict(r: Reading) -> Verdict:
    if not r.valid:
        return Verdict.UNKNOWN
    # Defence in depth: a reading with no plausible live data (all-FF /
    # zero cells) must never read as healthy. On the Desk `valid` is set by the STATIC
    # decode, so it can be True before a live read — the dead-cell tests skip a 0.0 V
    # cell, so without this a static-only pack would fall through to HEALTHY.
    if r.pack_voltage < 5.0:
        return Verdict.UNKNOWN

    red = r.cell_diff > DIFF_BAD
    for i in range(5):
        if 0.1 < r.cell[i] < CELL_V_DEAD:      # genuinely dead cell (< 2.0 V)
            red = True
    if thermistor_fault(r):                    # pinned sensor = confirmed fault
        red = True
    if red:
        return Verdict.REAL_FAULT

    # Soft / empirical signals -> orange hint, never a firm red fault.
    if r.latched_fault:                        # latched marker (D6, reverse-engineered)
        return Verdict.SUSPECT
    if r.charger_locked or r.locked:
        return Verdict.REPAIRABLE
    # Recoverable over-discharge: a cell below the healthy minimum but above the dead
    # floor, with no imbalance (that would have gone red above). Not a fault - it charges
    # back up - but not healthy either. Orange: a uniform ~2.2 V is recoverable.
    for i in range(5):
        if 0.1 < r.cell[i] < CELL_V_MIN:
            return Verdict.SUSPECT
    if thermistor_suspect(r):                   # sensors disagree (empirical)
        return Verdict.SUSPECT
    return Verdict.HEALTHY


_VERDICT_LABEL = {
    Verdict.HEALTHY: "HEALTHY",
    Verdict.REPAIRABLE: "UNLOCK",
    Verdict.SUSPECT: "POSSIBLE HW FIX",
    Verdict.REAL_FAULT: "HARDWARE FIX",
    Verdict.UNKNOWN: "NO PACK",
}


def verdict_label(v: Verdict) -> str:
    """On-screen wording (English canonical), matching the firmware (verdictText).
    UI code should prefer ``i18n.t(verdict_key(v))`` for the translated word; this
    stays English for tests, the health card, and any non-localised caller."""
    return _VERDICT_LABEL.get(v, "NO PACK")


# Firmware STRTAB key per verdict, so the UI can translate the verdict word via
# i18n while keeping it sourced from the firmware catalog (no wording gap with the
# device). EN values in the catalog match _VERDICT_LABEL exactly.
_VERDICT_KEY = {
    Verdict.HEALTHY: "S_HEALTHY",
    Verdict.REPAIRABLE: "S_UNLOCK",
    Verdict.SUSPECT: "S_SUSPECT_HW",
    Verdict.REAL_FAULT: "S_HARDWARE_FIX",
    Verdict.UNKNOWN: "S_NO_PACK",
}


def verdict_key(v: Verdict) -> str:
    return _VERDICT_KEY.get(v, "S_NO_PACK")


def cell_spread_grade(diff: float) -> tuple:
    """Cosmetic grade word + colour-key for the cell-spread metric. Bound to the
    firmware thresholds (DIFF_WARN / DIFF_BAD) so it can never disagree with the
    verdict; the <0.05 'excellent' is a purely cosmetic sub-level of 'balanced'."""
    if diff >= DIFF_BAD:
        return "CRITICAL", "red"
    if diff >= DIFF_WARN:
        return "WARNING", "amber"
    if diff >= 0.05:
        return "GOOD", "green"
    return "EXCELLENT", "green"


def health_band(pct: int) -> str:
    """Colour band ('green'/'amber'/'red') for OUR cycle-based health estimate
    (health_est_pct = 100 - cycles/8.96). This is our own wear estimate, NOT the
    Makita SOH gauge — we don't reproduce Makita's proprietary SOH. Bands: green >= 80,
    amber 50-79, red < 50."""
    if pct >= 80:
        return "green"
    if pct >= 50:
        return "amber"
    return "red"


# ---------------------------------------------------------------------------
# Staged diagnosis (firmware: drawWizardDiag) — checklist + finding + hint.
# ---------------------------------------------------------------------------
def lock_causes_text(mask: int) -> str:
    parts = []
    if mask & LF_N34:
        parts.append("N34")
    if mask & LF_CS0:
        parts.append("CS0")
    if mask & LF_CS1:
        parts.append("CS1")
    if mask & LF_CS2:
        parts.append("CS2")
    return " ".join(parts)


def _latched_why(r: Reading) -> str:
    if r.od_event_count:
        return i18n.t("DESK_DIAG_WHY_OD")
    if r.ol_event_count:
        return i18n.t("DESK_DIAG_WHY_OL")
    if r.health_est_pct < 50:
        return i18n.t("DESK_DIAG_WHY_WEAR")
    return i18n.t("DESK_DIAG_WHY_UNCLEAR")


def _temp_pinned_finding(r: Reading, recently_used: bool) -> dict:
    """Finding for a CONFIRMED (pinned) thermistor fault, naming the probe(s).
    Cell probe = sensor 1 (offset 14); board probe = sensor 2 (offset 16)."""
    pinned = []
    if temp_implausible(r.temp_cell):
        pinned.append(("cell", r.temp_cell))
    if temp_implausible(r.temp_mosfet):
        pinned.append(("board", r.temp_mosfet))
    if len(pinned) == 2:
        name = i18n.t("DESK_DIAG_PROBE_BOTH")
        probe_word = i18n.t("DESK_DIAG_PROBE_CELL_W")   # matches the old name.split()[0]
        obs = i18n.t("DESK_DIAG_THERM_OBS_BOTH", tc=r.temp_cell, tm=r.temp_mosfet)
    else:
        probe, val = pinned[0]
        is_cell = probe == "cell"
        name = i18n.t("DESK_DIAG_PROBE_CELL" if is_cell else "DESK_DIAG_PROBE_BOARD")
        other_name = i18n.t("DESK_DIAG_PROBE_BOARD" if is_cell else "DESK_DIAG_PROBE_CELL")
        other_v = r.temp_mosfet if is_cell else r.temp_cell
        probe_word = i18n.t("DESK_DIAG_PROBE_CELL_W" if is_cell else "DESK_DIAG_PROBE_BOARD_W")
        obs = i18n.t("DESK_DIAG_THERM_OBS_ONE", name=name, val=val,
                     other_name=other_name, other_v=other_v)
    cause = i18n.t("DESK_DIAG_THERM_CAUSE_RU" if recently_used else "DESK_DIAG_THERM_CAUSE",
                   probe=probe_word)
    check = i18n.t("DESK_DIAG_THERM_CHECK_RU" if recently_used else "DESK_DIAG_THERM_CHECK",
                   name=name)
    return {"color": "red", "title": i18n.t("DESK_DIAG_THERM_TITLE"),
            "observation": obs, "cause": cause, "check": check}


def _temp_gap_finding(r: Reading, recently_used: bool) -> dict:
    gap = abs(r.temp_mosfet - r.temp_cell)
    obs = i18n.t("DESK_DIAG_GAP_OBS", tc=r.temp_cell, tm=r.temp_mosfet, gap=gap)
    cause = i18n.t("DESK_DIAG_GAP_CAUSE_RU" if recently_used else "DESK_DIAG_GAP_CAUSE")
    check = i18n.t("DESK_DIAG_GAP_CHECK_RU" if recently_used else "DESK_DIAG_GAP_CHECK")
    return {"color": "orange", "title": i18n.t("DESK_DIAG_GAP_TITLE"),
            "observation": obs, "cause": cause, "check": check}


def diagnose(r: Reading, recently_used: bool = False) -> dict:
    """Full staged diagnosis mirroring the on-device Repair wizard, but evidence-
    based: every finding is Observation / likely Cause / what to Check — never a
    bare conclusion. ``recently_used`` (pack just charged or worked) softens the
    temperature findings. Cell probe = sensor 1, board probe = sensor 2.
    """
    v = compute_verdict(r)
    causes = 0 if (r.is_f0513 or len(r.msg) < 32) else lock_causes(r.msg)
    hw, grp, _ = find_hardware_fault(r)
    therm_state = 1 if thermistor_fault(r) else (2 if thermistor_suspect(r) else 0)

    if hw == HwFault.SENSE_WIRE:
        f = {"color": "red", "title": i18n.t("DESK_DIAG_SENSE_TITLE", grp=grp),
             "observation": i18n.t("DESK_DIAG_SENSE_OBS", grp=grp, pv=r.pack_voltage),
             "cause": i18n.t("DESK_DIAG_SENSE_CAUSE"),
             "check": i18n.t("DESK_DIAG_SENSE_CHECK", grp=grp)}
    elif hw == HwFault.WEAK_CELL:
        f = {"color": "red", "title": i18n.t("DESK_DIAG_WEAK_TITLE", grp=grp),
             "observation": i18n.t("DESK_DIAG_WEAK_OBS", grp=grp, val=r.cell[grp - 1]),
             "cause": i18n.t("DESK_DIAG_WEAK_CAUSE"),
             "check": i18n.t("DESK_DIAG_WEAK_CHECK", grp=grp, vmin=CELL_V_DEAD)}
    elif hw == HwFault.IMBALANCE:
        f = {"color": "red", "title": i18n.t("DESK_DIAG_IMB_TITLE"),
             "observation": i18n.t("DESK_DIAG_IMB_OBS", diff=r.cell_diff, grp=grp),
             "cause": i18n.t("DESK_DIAG_IMB_CAUSE"),
             "check": i18n.t("DESK_DIAG_IMB_CHECK", grp=grp)}
    elif hw == HwFault.THERMISTOR:
        f = _temp_pinned_finding(r, recently_used)
    elif r.latched_fault:
        f = {"color": "orange", "title": i18n.t("DESK_DIAG_LATCHED_TITLE"),
             "observation": i18n.t("DESK_DIAG_LATCHED_OBS", why=_latched_why(r)),
             "cause": i18n.t("DESK_DIAG_LATCHED_CAUSE"),
             "check": i18n.t("DESK_DIAG_LATCHED_CHECK")}
    elif not causes and not r.locked:
        if thermistor_suspect(r):
            f = _temp_gap_finding(r, recently_used)
        else:
            f = {"color": "green", "title": i18n.t("DESK_DIAG_NOFAULT_TITLE"),
                 "observation": i18n.t("DESK_DIAG_NOFAULT_OBS"),
                 "cause": i18n.t("DESK_DIAG_NOFAULT_CAUSE"),
                 "check": i18n.t("DESK_DIAG_NOFAULT_CHECK")}
    else:
        f = {"color": "green", "title": i18n.t("DESK_DIAG_FALSELOCK_TITLE"),
             "observation": i18n.t("DESK_DIAG_FALSELOCK_OBS"),
             "cause": i18n.t("DESK_DIAG_FALSELOCK_CAUSE"),
             "check": i18n.t("DESK_DIAG_FALSELOCK_CHECK")}

    # Additive advisory: a plausibly-warm probe (not a fault).
    info = ""
    if not r.is_f0513 and therm_state == 0:
        hi = max(r.temp_cell, r.temp_mosfet)
        if hi > TEMP_WARM_C:
            info = i18n.t("DESK_DIAG_WARM_RU" if recently_used else "DESK_DIAG_WARM", hi=hi)

    if hw != HwFault.NONE:
        gate_hint = i18n.t("DESK_DIAG_GATE_FIXHW")
    elif causes:
        gate_hint = i18n.t("DESK_DIAG_GATE_UNLOCK")
    else:
        gate_hint = i18n.t("DESK_DIAG_GATE_NOTHING")

    return {
        "verdict": v,
        "charger_lock": lock_causes_text(causes),   # "" if none
        "latched": r.latched_fault,
        "thermistor_state": therm_state,            # 0 ok / 1 fault / 2 suspect
        "hw_fault": hw,
        "hw_group": grp,
        "title": f["title"],
        "color": f["color"],                        # 'red' / 'orange' / 'green'
        "observation": f["observation"],
        "cause": f["cause"],
        "check": f["check"],
        "info": info,                               # "" if none
        "gate_hint": gate_hint,
    }


def verdict_reason(r: Reading) -> str:
    """One-line reason (the likely cause) for the Live banner."""
    return diagnose(r)["cause"]


def verdict_detail_text(r: Reading) -> str:
    """Fuller detail for the DB verdict_detail column (kept for later analysis).

    Forced to ENGLISH regardless of the UI language, so stored data stays stable and
    language-independent (matching the health card / CSV, also English)."""
    prev = i18n.current()
    i18n.set_language("en")
    try:
        d = diagnose(r)
        return f"{d['title']} | {d['observation']} | {d['cause']} | {d['check']}"
    finally:
        i18n.set_language(prev)

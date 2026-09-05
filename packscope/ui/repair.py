"""Repair wizard: Read -> Classify -> Unlock -> Re-read & confirm.

Drives the same flow as the on-device Repair wizard, remotely through the bridge,
logging every step to the DB (a repair_sessions row linking the before/after
readings + the outcome). The verdict shown is ALWAYS compute_verdict() — no
parallel logic — and it gates the Unlock step.
"""

from __future__ import annotations

import customtkinter as ctk

from .. import db as dbmod
from .. import protocol
from ..i18n import t
from ..models import HwFault, Verdict
from ..verdict import compute_verdict, diagnose, verdict_key
from . import theme
from .components import StatusBadge, StepIndicator


def _find_color(key):
    return {"red": theme.RED, "orange": theme.ORANGE,
            "green": theme.GREEN}.get(key, theme.TEXT)


def _card(master):
    return ctk.CTkFrame(master, fg_color=theme.PANEL, corner_radius=12)


class RepairFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.app = app
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.step = 1
        self.before = None
        self.after = None
        self.verdict_before = Verdict.UNKNOWN
        self.session_id = None
        self.before_id = None
        self.recently_used = ctk.BooleanVar(value=False)   # pack just charged/used?

        # graphical stepper (labels resolved now; the whole frame is rebuilt on a
        # language switch, so they re-translate)
        steps = [t("DESK_RPR_STEP_READ"), t("DESK_RPR_STEP_CLASSIFY"),
                 t("DESK_RPR_STEP_UNLOCK"), t("DESK_RPR_STEP_CONFIRM")]
        self.stepper = StepIndicator(self, app, steps)
        self.stepper.grid(row=0, column=0, sticky="w", padx=24, pady=(18, 8))

        self.status = ctk.CTkLabel(self, text="", font=app.f_small,
                                   text_color=theme.MUTED, justify="left",
                                   wraplength=760)
        self.status.grid(row=1, column=0, sticky="w", padx=24, pady=(2, 6))

        # Scrollable so the action buttons are always reachable regardless of how
        # tall a step's content gets (issue #2).
        self.content = ctk.CTkScrollableFrame(self, fg_color=theme.PANEL,
                                              corner_radius=12, label_text="")
        self.content.grid(row=2, column=0, sticky="nsew", padx=24, pady=(4, 16))
        self.content.grid_columnconfigure(0, weight=1)

        self._render()

    # ---------------------------------------------------------------- helpers
    def on_show(self):
        # A fresh visit starts a fresh wizard — never show a previous pack's data
        # (issue #1). An in-progress unlock is rare enough to restart cleanly.
        self._reset()

    def _update_indicator(self):
        self.stepper.set_current(self.step - 1)

    def _clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _summary(self, r):
        v = compute_verdict(r)
        lock = t("DESK_RPR_LOCKED") if (r.locked or r.charger_locked) else t("DESK_RPR_UNLOCKED")
        temp = ("" if not r.board_temp_valid   # single-sensor read: no 2nd temp to spread against
                else f"  ·  {t('DESK_TEMP_SPREAD')} {abs(r.temp_mosfet - r.temp_cell):.0f} °C")
        return (f"{r.model}  ·  {r.pack_voltage:.2f} V  ·  {t('DESK_CELL_SPREAD')} "
                f"{r.cell_diff:.2f} V{temp}  ·  {lock}  ·  {t(verdict_key(v))}")

    def _need_bridge(self):
        if self.app.bridge is None:
            self.status.configure(text=t("DESK_NOT_CONNECTED"), text_color=theme.AMBER)
            return False
        return True

    def _render(self):
        self._update_indicator()
        self._clear_content()
        {1: self._step_read, 2: self._step_classify,
         3: self._step_unlock, 4: self._step_confirm}[self.step]()

    # ------------------------------------------------------------------ step 1
    def _step_read(self):
        ctk.CTkLabel(self.content, text=t("DESK_RPR_S1_TITLE"), font=self.app.f_title,
                     text_color=theme.TEXT).grid(row=0, column=0, sticky="w",
                                                 padx=16, pady=(14, 4))
        ctk.CTkLabel(self.content, text=t("DESK_RPR_S1_DESC"),
                     font=self.app.f_body, text_color=theme.MUTED).grid(
            row=1, column=0, sticky="w", padx=16)
        btn = ctk.CTkButton(self.content, text=t("DESK_READ_PACK"), font=self.app.f_body,
                            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                            text_color=theme.ACCENT_INK, command=self._do_read)
        btn.grid(row=2, column=0, sticky="w", padx=16, pady=16)

    def _do_read(self):
        if not self._need_bridge():
            return
        self.status.configure(text=t("DESK_READING_PACK"), text_color=theme.MUTED)

        def done(r):
            if not r.valid:
                self.status.configure(text=t("DESK_NO_PACK_DETECTED"), text_color=theme.AMBER)
                return
            self.before = r
            self.verdict_before = compute_verdict(r)
            self.before_id = dbmod.insert_reading(self.app.conn, r,
                                                  fw_version=self.app.fw_version)
            self.session_id = dbmod.create_repair_session(
                self.app.conn, r.serial_no, self.before_id, self.verdict_before.value)
            self.status.configure(text=t("DESK_RPR_BASELINE", self._summary(r)),
                                  text_color=theme.GREEN)
            self.step = 2
            self._render()

        def err(exc):
            self.status.configure(text=t("DESK_READ_FAIL", exc), text_color=theme.RED)

        self.app.run_async(lambda: protocol.read_all(self.app.bridge), done, err)

    # ------------------------------------------------------------------ step 2
    def _chk_row(self, parent, row, label, value, kind):
        ctk.CTkLabel(parent, text=label, font=self.app.f_small,
                     text_color=theme.MUTED).grid(row=row, column=0, sticky="w",
                                                  padx=(14, 0), pady=6)
        StatusBadge(parent, self.app, value.upper(), kind).grid(
            row=row, column=1, sticky="e", padx=(0, 14), pady=6)

    def _finding_line(self, parent, row, label, text):
        # width fits the longest label across languages (e.g. FR "Cause probable",
        # ES "Causa probable") so the label never collides with the value column.
        ctk.CTkLabel(parent, text=label, font=self.app.f_label,
                     text_color=theme.DIM, width=115, anchor="w").grid(
            row=row, column=0, sticky="nw", padx=(0, 8), pady=2)
        ctk.CTkLabel(parent, text=text, font=self.app.f_small, text_color=theme.TEXT,
                     justify="left", wraplength=640, anchor="w").grid(
            row=row, column=1, sticky="w", pady=2)

    def _step_classify(self):
        r = self.before
        d = diagnose(r, self.recently_used.get())
        v = d["verdict"]
        col = theme.verdict_color(v)
        content = self.content
        content.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(content, text=t("DESK_RPR_S2_TITLE"), font=self.app.f_title,
                     text_color=theme.TEXT).grid(row=0, column=0, columnspan=2,
                                                 sticky="w", padx=16, pady=(14, 4))

        # verdict banner
        banner = ctk.CTkFrame(content, fg_color=theme.verdict_bg(v), corner_radius=10,
                              border_width=1, border_color=col)
        banner.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=8)
        banner.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(banner, text=t(verdict_key(v)), font=self.app.f_body,
                     text_color=col).grid(row=0, column=0, sticky="w", padx=14, pady=10)

        # context toggle: was the pack just charged / used?
        ctk.CTkCheckBox(content, text=t("DESK_RPR_RECENTLY_USED"),
                        variable=self.recently_used, font=self.app.f_small,
                        command=self._render, fg_color=theme.ACCENT_DIM).grid(
            row=2, column=0, columnspan=2, sticky="w", padx=16, pady=(2, 6))

        # raw-signal checklist (labels + values reuse the firmware S_* catalog)
        chk = ctk.CTkFrame(content, fg_color=theme.PANEL2, corner_radius=10)
        chk.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=6)
        chk.grid_columnconfigure(1, weight=1)
        self._chk_row(chk, 0, t("S_CHARGER_LOCK"), d["charger_lock"] or t("S_NONE"),
                      "amber" if d["charger_lock"] else "green")
        self._chk_row(chk, 1, t("S_LATCHED_FAULT"), t("S_YES") if d["latched"] else t("S_NONE"),
                      "orange" if d["latched"] else "green")
        th = {0: (t("S_OKV"), "green"), 1: (t("S_FAULTV"), "red"),
              2: ("?", "orange")}[d["thermistor_state"]]
        self._chk_row(chk, 2, t("S_THERMISTOR"), th[0], th[1])
        cell_fault = d["hw_fault"] in (HwFault.SENSE_WIRE, HwFault.WEAK_CELL,
                                       HwFault.IMBALANCE)
        self._chk_row(chk, 3, t("S_CELLS"), f"G{d['hw_group']}" if cell_fault else t("S_OKV"),
                      "red" if cell_fault else "green")

        # finding: title + Observation / Likely cause / Check
        fcol = _find_color(d["color"])
        ctk.CTkLabel(content, text=d["title"], font=self.app.f_body,
                     text_color=fcol).grid(row=4, column=0, columnspan=2, sticky="w",
                                           padx=16, pady=(8, 2))
        lines = ctk.CTkFrame(content, fg_color="transparent")
        lines.grid(row=5, column=0, columnspan=2, sticky="ew", padx=16)
        lines.grid_columnconfigure(1, weight=1)
        self._finding_line(lines, 0, t("DESK_RPR_OBSERVATION"), d["observation"])
        self._finding_line(lines, 1, t("DESK_RPR_CAUSE"), d["cause"])
        self._finding_line(lines, 2, t("DESK_RPR_CHECK"), d["check"])
        if d["info"]:
            ctk.CTkLabel(content, text="ℹ  " + d["info"], font=self.app.f_small,
                         text_color=theme.MUTED, justify="left", wraplength=720).grid(
                row=6, column=0, columnspan=2, sticky="w", padx=16, pady=(6, 0))

        # gate: a hardware fault must be fixed first (feasibility-first). A soft
        # SUSPECT (latched / spread) does NOT block. No lock at all -> nothing to do.
        self._gate_hw = d["hw_fault"] != HwFault.NONE
        self._gate_has_lock = bool(d["charger_lock"]) or r.locked
        self.override_var = ctk.BooleanVar(value=False)
        row = 7
        if self._gate_hw:
            ctk.CTkCheckBox(content, text=t("DESK_RPR_OVERRIDE"),
                            variable=self.override_var, font=self.app.f_small,
                            command=self._refresh_next, fg_color=theme.RED,
                            hover_color=theme.RED).grid(row=row, column=0, columnspan=2,
                                                        sticky="w", padx=16, pady=(8, 4))
            row += 1
        elif not self._gate_has_lock:
            ctk.CTkLabel(content, text=d["gate_hint"], font=self.app.f_small,
                         text_color=theme.MUTED).grid(row=row, column=0, columnspan=2,
                                                      sticky="w", padx=16, pady=(8, 4))
            row += 1

        self.next_btn = ctk.CTkButton(
            content, text=t("DESK_RPR_PROCEED"), font=self.app.f_body,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.ACCENT_INK, command=self._to_unlock)
        self.next_btn.grid(row=row, column=0, sticky="w", padx=16, pady=14)
        ctk.CTkButton(content, text=t("DESK_RPR_START_OVER"), font=self.app.f_body,
                      fg_color=theme.PANEL2, hover_color=theme.RAISED,
                      command=self._reset).grid(row=row, column=1, sticky="e",
                                                padx=16, pady=14)
        self._refresh_next()

    def _refresh_next(self):
        if self._gate_hw:
            allow = self.override_var.get()
        else:
            allow = self._gate_has_lock
        self.next_btn.configure(state="normal" if allow else "disabled")

    def _to_unlock(self):
        self.step = 3
        self._render()

    # ------------------------------------------------------------------ step 3
    def _step_unlock(self):
        ctk.CTkLabel(self.content, text=t("DESK_RPR_S3_TITLE"), font=self.app.f_title,
                     text_color=theme.TEXT).grid(row=0, column=0, sticky="w",
                                                 padx=16, pady=(14, 4))
        ctk.CTkLabel(self.content, justify="left", wraplength=720, font=self.app.f_small,
                     text_color=theme.MUTED, text=t("DESK_RPR_S3_DESC")).grid(
            row=1, column=0, sticky="w", padx=16, pady=(0, 8))
        self.unlock_btn = ctk.CTkButton(
            self.content, text=t("DESK_RPR_UNLOCK_NOW"), font=self.app.f_body, fg_color=theme.AMBER,
            hover_color="#f0c95a", text_color="#2a2312", command=self._do_unlock)
        self.unlock_btn.grid(row=2, column=0, sticky="w", padx=16, pady=14)

    def _do_unlock(self):
        if not self._need_bridge():
            return
        self.unlock_btn.configure(state="disabled", text=t("DESK_RPR_UNLOCKING"))
        self.status.configure(text=t("DESK_RPR_WRITING"), text_color=theme.MUTED)

        def done(after):
            self.after = after
            # Colour the status by the AFTER verdict, not "unlock ran OK".
            self.status.configure(text=t("DESK_RPR_UNLOCK_DONE", self._summary(after)),
                                  text_color=theme.verdict_color(compute_verdict(after)))
            self.step = 4
            self._render()

        def err(exc):
            self.unlock_btn.configure(state="normal", text=t("DESK_RPR_UNLOCK_NOW"))
            self.status.configure(text=t("DESK_RPR_UNLOCK_FAILED", exc), text_color=theme.RED)

        self.app.run_async(lambda: protocol.unlock(self.app.bridge), done, err)

    # ------------------------------------------------------------------ step 4
    def _step_confirm(self):
        before, after = self.before, self.after
        av = compute_verdict(after)
        lock_cleared = not (after.locked or after.charger_locked)
        ctk.CTkLabel(self.content, text=t("DESK_RPR_S4_TITLE"), font=self.app.f_title,
                     text_color=theme.TEXT).grid(row=0, column=0, sticky="w",
                                                 padx=16, pady=(14, 4))

        grid = ctk.CTkFrame(self.content, fg_color="transparent")
        grid.grid(row=1, column=0, sticky="ew", padx=16, pady=6)
        ctk.CTkLabel(grid, text=t("S_BEFORE"), font=self.app.f_label,
                     text_color=theme.DIM).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(grid, text=self._summary(before), font=self.app.f_small,
                     text_color=theme.TEXT).grid(row=1, column=0, sticky="w", pady=(0, 8))
        ctk.CTkLabel(grid, text=t("S_AFTER"), font=self.app.f_label,
                     text_color=theme.DIM).grid(row=2, column=0, sticky="w")
        ctk.CTkLabel(grid, text=self._summary(after), font=self.app.f_small,
                     text_color=theme.TEXT).grid(row=3, column=0, sticky="w")

        # The RESULT reflects the AFTER verdict, not just the lock bit. Clearing the
        # lock nybble on a genuinely faulty pack is NOT a repair — say so, in colour.
        if av == Verdict.HEALTHY:
            res_msg = t("DESK_RPR_RES_HEALTHY")
        elif av == Verdict.REAL_FAULT:
            res_msg = t("DESK_RPR_RES_REALFAULT")
        elif av == Verdict.SUSPECT:
            res_msg = t("DESK_RPR_RES_SUSPECT")
        elif not lock_cleared:
            res_msg = t("DESK_RPR_RES_STILLLOCKED")
        else:
            res_msg = t("DESK_RPR_RES_UNLOCKED")
        ctk.CTkLabel(self.content, text=res_msg, font=self.app.f_body,
                     text_color=theme.verdict_color(av), justify="left",
                     wraplength=740).grid(row=2, column=0, columnspan=2, sticky="w",
                                          padx=16, pady=(8, 4))

        ctk.CTkLabel(self.content, text=t("DESK_RPR_HOLD_Q"),
                     font=self.app.f_small, text_color=theme.MUTED).grid(
            row=3, column=0, sticky="w", padx=16, pady=(8, 2))
        # Segmented button shows translated labels but maps back to stable keys.
        self._held_map = {t("DESK_RPR_HELD"): True, t("DESK_RPR_RELOCKED"): False,
                          t("DESK_RPR_UNKNOWN"): None}
        self.held_var = ctk.StringVar(value=t("DESK_RPR_UNKNOWN"))
        seg = ctk.CTkSegmentedButton(self.content, values=list(self._held_map),
                                     variable=self.held_var, font=self.app.f_small,
                                     fg_color=theme.PANEL2, unselected_color=theme.PANEL2,
                                     selected_color=theme.ACCENT_DIM, text_color=theme.TEXT)
        seg.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 8))

        self.note_entry = ctk.CTkEntry(self.content, width=420, font=self.app.f_small,
                                       placeholder_text=t("DESK_RPR_NOTES"),
                                       fg_color=theme.PANEL2, border_color=theme.BORDER2)
        self.note_entry.grid(row=5, column=0, sticky="w", padx=16, pady=(0, 10))

        self._unlocked_ok = lock_cleared
        ctk.CTkButton(self.content, text=t("DESK_RPR_SAVE_SESSION"), font=self.app.f_body,
                      fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                      text_color=theme.ACCENT_INK, command=self._save).grid(
            row=6, column=0, sticky="w", padx=16, pady=(0, 14))
        ctk.CTkButton(self.content, text=t("DESK_RPR_START_OVER"), font=self.app.f_body,
                      fg_color=theme.PANEL2, hover_color=theme.RAISED,
                      command=self._reset).grid(row=6, column=0, sticky="e",
                                                padx=16, pady=(0, 14))

    def _save(self):
        after_id = dbmod.insert_reading(self.app.conn, self.after,
                                        fw_version=self.app.fw_version,
                                        wizard_session_id=self.session_id)
        override = bool(getattr(self, "_gate_hw", False)) and self.override_var.get()
        dbmod.finish_repair_session(
            self.app.conn, self.session_id, after_reading_id=after_id,
            override_used=override, unlocked_ok=self._unlocked_ok,
            held=self._held_map.get(self.held_var.get()), notes=self.note_entry.get())
        self.status.configure(text=t("DESK_RPR_SAVED"), text_color=theme.GREEN)
        self._reset()

    def _reset(self):
        self.step = 1
        self.before = self.after = None
        self.verdict_before = Verdict.UNKNOWN
        self.session_id = self.before_id = None
        self.status.configure(text="")
        self._render()

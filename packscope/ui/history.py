"""Batteries screen: a pack is an entity tracked over time.

Left: pack list (identity + verdict badge), filterable by family / status / tag /
search. Right: pack detail — identity header (editable), stats, verdict-evolution
strip, a switchable trend, repair sessions (with held/re-locked ground truth), and
the readings table (click a row -> full reading dump). Demo data can be loaded to
explore all of this without hardware.
"""

from __future__ import annotations

import json
import tkinter as tk
import webbrowser
from tkinter import filedialog

import customtkinter as ctk

from .. import csvexport
from .. import db as dbmod
from .. import decode
from .. import demo_history
from .. import healthcard
from .. import report
from ..i18n import t
from ..models import Verdict
from ..units import fmt_temp, human_dt
from ..verdict import verdict_key
from . import theme
from .components import (
    Metric, SectionHeader, StatusBadge, VerdictStrip, divider, verdict_kind,
)

# Logical keys — STABLE, never translated (used by _metric_series / DB status).
# Their display labels are translated per-instance (self._metric_labels / _status_*).
_METRICS = ["Pack V", "Cell spread", "Temp spread", "Cycles"]
_STATUS_KEYS = ["", "to_diagnose", "repaired", "parts", "scrap"]
_STATUS_STRID = {"to_diagnose": "DESK_HIST_ST_TODIAG", "repaired": "DESK_HIST_ST_REPAIRED",
                 "parts": "DESK_HIST_ST_PARTS", "scrap": "DESK_HIST_ST_SCRAP"}


class TrendCanvas(tk.Canvas):
    """A tiny line chart of one metric over time."""

    def __init__(self, master):
        super().__init__(master, bg=theme.PANEL, highlightthickness=0, bd=0, height=130)
        self.values = []
        self.unit = ""
        self.bind("<Configure>", lambda e: self._draw())

    def set_series(self, values, unit=""):
        self.values = list(values)
        self.unit = unit
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20 or h < 20 or not self.values:
            return
        pad = 20
        lo, hi = min(self.values), max(self.values)
        rng = (hi - lo) or 1.0
        n = len(self.values)
        step = (w - 2 * pad) / max(1, n - 1)
        pts = [(pad + i * step, h - pad - (v - lo) / rng * (h - 2 * pad))
               for i, v in enumerate(self.values)]
        if len(pts) >= 2:
            self.create_line(*[c for p in pts for c in p], fill=theme.ACCENT,
                             width=2, smooth=True)
        for x, y in pts:
            self.create_oval(x - 3, y - 3, x + 3, y + 3, fill=theme.ACCENT, outline="")
        self.create_text(pad, 11, text=f"{hi:g} {self.unit}", fill=theme.MUTED,
                         anchor="w", font=(theme.MONO_FAMILY, 10))
        self.create_text(pad, h - 9, text=f"{lo:g} {self.unit}", fill=theme.MUTED,
                         anchor="w", font=(theme.MONO_FAMILY, 10))


def _metric_series(hist, metric):
    vals = []
    for r in hist:
        if metric == "Pack V":
            vals.append(round((r["pack_voltage_mv"] or 0) / 1000.0, 2))
        elif metric == "Cell spread":
            try:
                cv = json.loads(r["cell_voltages_mv"] or "[]")
            except (json.JSONDecodeError, TypeError):
                cv = []
            cv = [c / 1000.0 for c in cv if c]
            vals.append(round(max(cv) - min(cv), 2) if cv else 0.0)
        elif metric == "Temp spread":
            t1, t2 = r["temp1_c"], r["temp2_c"]
            vals.append(round(abs((t2 or 0) - (t1 or 0)), 1) if t1 is not None else 0.0)
        else:
            vals.append(r["cycle_count"] or 0)
    unit = {"Pack V": "V", "Cell spread": "V", "Temp spread": "°C", "Cycles": ""}[metric]
    return vals, unit


class HistoryFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.app = app
        self.selected_serial = None
        self._hist = []
        self._metric = "Pack V"

        # Translated display <-> stable-key maps (rebuilt on a language switch).
        self._status_labels = {"": "—"}
        self._status_labels.update({k: t(_STATUS_STRID[k]) for k in _STATUS_STRID})
        self._status_label_to_key = {v: k for k, v in self._status_labels.items()}
        self._status_filter = {t("DESK_HIST_ALL_STATUS"): None}
        self._status_filter.update({t(_STATUS_STRID[k]): k for k in _STATUS_STRID})
        self._metric_labels = {
            "Pack V": t("DESK_HIST_M_PACKV"), "Cell spread": t("DESK_HIST_M_CELLSPREAD"),
            "Temp spread": t("DESK_HIST_M_TEMPSPREAD"), "Cycles": t("DESK_HIST_M_CYCLES")}
        self._metric_key = {v: k for k, v in self._metric_labels.items()}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- filters ---
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 8))
        self.family = ctk.CTkSegmentedButton(
            top, values=["ALL", "LXT", "XGT", "CXT"], font=app.f_small,
            fg_color=theme.PANEL, selected_color=theme.ACCENT_DIM, text_color=theme.TEXT,
            unselected_color=theme.PANEL, command=lambda _=None: self.refresh())
        self.family.set("ALL")
        self.family.grid(row=0, column=0)
        self.status_f = ctk.CTkOptionMenu(
            top, values=list(self._status_filter.keys()), font=app.f_small, width=130,
            fg_color=theme.PANEL2, button_color=theme.BORDER2, text_color=theme.TEXT,
            dropdown_fg_color=theme.PANEL2, dropdown_text_color=theme.TEXT,
            command=lambda _=None: self.refresh())
        self.status_f.grid(row=0, column=1, padx=8)
        self.search = ctk.CTkEntry(top, width=200, font=app.f_small, text_color=theme.TEXT,
                                   placeholder_text=t("DESK_HIST_SEARCH_PH"),
                                   fg_color=theme.PANEL2, border_color=theme.BORDER2)
        self.search.grid(row=0, column=2)
        self.search.bind("<KeyRelease>", lambda e: self.refresh())
        self.demo_btn = ctk.CTkButton(top, text=t("DESK_HIST_LOAD_DEMO"), font=app.f_small,
                                      fg_color=theme.PANEL2, hover_color=theme.RAISED,
                                      text_color=theme.TEXT, command=self._toggle_demo)
        self.demo_btn.grid(row=0, column=4, padx=(8, 0))
        top.grid_columnconfigure(3, weight=1)

        # --- body: list | detail ---
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=8)
        body.grid_columnconfigure(0, weight=34, uniform="hist")
        body.grid_columnconfigure(1, weight=66, uniform="hist")
        body.grid_rowconfigure(0, weight=1)

        self.list = ctk.CTkScrollableFrame(body, fg_color=theme.PANEL, corner_radius=12,
                                           label_text="")
        self.list.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.list.grid_columnconfigure(0, weight=1)

        self.detail = ctk.CTkScrollableFrame(body, fg_color=theme.PANEL, corner_radius=12,
                                             label_text="")
        self.detail.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.detail.grid_columnconfigure(0, weight=1)

        # --- export bar ---
        exp = ctk.CTkFrame(self, fg_color="transparent")
        exp.grid(row=2, column=0, sticky="ew", padx=24, pady=(4, 16))
        ctk.CTkButton(exp, text=t("DESK_HIST_EXPORT_CSV"), font=app.f_body, fg_color=theme.PANEL2,
                      hover_color=theme.RAISED, text_color=theme.TEXT,
                      command=self._export_csv).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(exp, text=t("DESK_HIST_EXPORT_REPORT"), font=app.f_body,
                      fg_color=theme.PANEL2, hover_color=theme.RAISED, text_color=theme.TEXT,
                      command=self._export_report).grid(row=0, column=1)
        self.exp_status = ctk.CTkLabel(exp, text="", font=app.f_small, text_color=theme.MUTED)
        self.exp_status.grid(row=0, column=2, padx=12)

        self._show_placeholder()

    # ------------------------------------------------------------- list
    def on_show(self):
        self.refresh()

    def _toggle_demo(self):
        if dbmod.has_demo(self.app.conn):
            dbmod.clear_demo(self.app.conn)
        else:
            demo_history.seed(self.app.conn)
        self.refresh()

    def refresh(self):
        self.demo_btn.configure(text=t("DESK_HIST_CLEAR_DEMO") if dbmod.has_demo(self.app.conn)
                                else t("DESK_HIST_LOAD_DEMO"))
        rows = dbmod.list_batteries(self.app.conn, family=self.family.get(),
                                    search=self.search.get(),
                                    status=self._status_filter.get(self.status_f.get()))
        for w in self.list.winfo_children():
            w.destroy()
        if not rows:
            ctk.CTkLabel(self.list, text=t("DESK_HIST_NO_BATTERIES"),
                         font=self.app.f_small, text_color=theme.DIM,
                         justify="left").grid(row=0, column=0, padx=14, pady=14, sticky="w")
            return
        for i, row in enumerate(rows):
            self._battery_card(i, row)

    def _battery_card(self, i, row):
        v = Verdict(row["verdict"]) if row["verdict"] else Verdict.UNKNOWN
        card = ctk.CTkFrame(self.list, fg_color=theme.PANEL2, corner_radius=10)
        card.grid(row=i, column=0, sticky="ew", padx=8, pady=4)
        card.grid_columnconfigure(0, weight=1)
        title = row["alias"] or row["model"] or "?"
        if len(title) > 22:
            title = title[:21] + "…"
        ctk.CTkLabel(card, text=title, font=self.app.f_body, text_color=theme.TEXT,
                     anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=(9, 0))
        ctk.CTkLabel(card, text=row["serial_no"], font=self.app.f_mono,
                     text_color=theme.MUTED, anchor="w").grid(
            row=1, column=0, sticky="w", padx=12, pady=(0, 9))
        StatusBadge(card, self.app, t(verdict_key(v)), verdict_kind(v)).grid(
            row=0, column=1, rowspan=2, padx=(0, 10))
        for wdg in card.winfo_children() + [card]:
            wdg.bind("<Button-1>", lambda e, s=row["serial_no"]: self._select(s))

    # ------------------------------------------------------------- detail
    def _clear_detail(self):
        for w in self.detail.winfo_children():
            w.destroy()

    def _show_placeholder(self):
        self._clear_detail()
        ctk.CTkLabel(self.detail, text=t("DESK_HIST_SELECT_BATTERY"), font=self.app.f_model,
                     text_color=theme.MUTED).grid(row=0, column=0, padx=18, pady=18, sticky="w")

    def _select(self, serial):
        self.selected_serial = serial
        self._hist = dbmod.get_history(self.app.conn, serial)
        if not self._hist:
            return
        self._render_detail()

    def _render_detail(self):
        self._clear_detail()
        d = self.detail
        hist = self._hist
        latest = hist[-1]
        bat = dbmod.get_battery(self.app.conn, self.selected_serial)
        v = Verdict(latest["verdict"]) if latest["verdict"] else Verdict.UNKNOWN
        r = 0

        # identity header
        head = ctk.CTkFrame(d, fg_color="transparent")
        head.grid(row=r, column=0, sticky="ew", padx=16, pady=(16, 0)); r += 1
        head.grid_columnconfigure(0, weight=1)
        title = (bat["alias"] if bat and bat["alias"] else latest["model"]) or "?"
        ctk.CTkLabel(head, text=title, font=self.app.f_model,
                     text_color=theme.TEXT).grid(row=0, column=0, sticky="w")
        StatusBadge(head, self.app, t(verdict_key(v)), verdict_kind(v)).grid(
            row=0, column=1, sticky="e")
        ctk.CTkLabel(d, text=f"{latest['model']} · S/N {self.selected_serial}",
                     font=self.app.f_mono, text_color=theme.MUTED).grid(
            row=r, column=0, sticky="w", padx=16); r += 1

        owner = (bat["owner"] if bat else "") or "—"
        status = self._status_labels.get((bat["status"] if bat else "") or "", "—")
        tags = ", ".join(dbmod.battery_tags(bat)) if bat else ""
        meta = (f"{t('DESK_HIST_OWNER')}: {owner}   ·   {t('DESK_HIST_STATUS')}: {status}"
                + (f"   ·   {tags}" if tags else ""))
        ctk.CTkLabel(d, text=meta, font=self.app.f_small, text_color=theme.MUTED).grid(
            row=r, column=0, sticky="w", padx=16, pady=(4, 0)); r += 1
        acts = ctk.CTkFrame(d, fg_color="transparent")
        acts.grid(row=r, column=0, sticky="w", padx=16, pady=(8, 4)); r += 1
        ctk.CTkButton(acts, text=t("DESK_HIST_EDIT_IDENTITY"), font=self.app.f_small, height=28,
                      fg_color="transparent", border_width=1, border_color=theme.BORDER2,
                      hover_color=theme.PANEL2, text_color=theme.TEXT,
                      command=self._edit_identity).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(acts, text=t("DESK_HIST_COMPARE"), font=self.app.f_small, height=28,
                      fg_color="transparent", border_width=1, border_color=theme.BORDER2,
                      hover_color=theme.PANEL2, text_color=theme.TEXT,
                      command=self._compare,
                      state=("normal" if len(hist) >= 2 else "disabled")).grid(
            row=0, column=1, padx=(0, 8))
        ctk.CTkButton(acts, text=t("DESK_HIST_HEALTH_CARD"), font=self.app.f_small, height=28,
                      fg_color="transparent", border_width=1, border_color=theme.BORDER2,
                      hover_color=theme.PANEL2, text_color=theme.TEXT,
                      command=self._export_health_card).grid(row=0, column=2)

        divider(d).grid(row=r, column=0, sticky="ew", padx=16, pady=10); r += 1

        # stats
        stats = ctk.CTkFrame(d, fg_color="transparent")
        stats.grid(row=r, column=0, sticky="ew", padx=16); r += 1
        for c in range(3):
            stats.grid_columnconfigure(c, weight=1, uniform="s")
        n_rep = len(dbmod.get_repair_sessions(self.app.conn, self.selected_serial))
        cap = latest["capacity_ah"] or 0.0
        cells = [(t("S_CAPACITY"), f"{cap:.1f} Ah"), (t("DESK_HIST_READINGS"), str(len(hist))),
                 (t("DESK_HIST_REPAIRS"), str(n_rep)), (t("DESK_HIST_FIRST_SEEN"), hist[0]["read_at"][:10]),
                 (t("DESK_HIST_LAST_SEEN"), latest["read_at"][:10]),
                 (t("DESK_CYCLES"), str(latest["cycle_count"] or 0))]
        for i, (k, val) in enumerate(cells):
            m = Metric(stats, self.app, k)
            m.set(val)
            m.grid(row=i // 3, column=i % 3, sticky="ew", pady=(0, 10), padx=(0, 10))

        # verdict evolution
        SectionHeader(d, self.app, t("DESK_HIST_VERDICT_TIME")).grid(row=r, column=0, sticky="w",
                                                             padx=16, pady=(4, 4)); r += 1
        strip = VerdictStrip(d, self.app)
        strip.grid(row=r, column=0, sticky="w", padx=16); r += 1
        strip.set([Verdict(x) if x else Verdict.UNKNOWN for _, x in
                   dbmod.verdict_series(self.app.conn, self.selected_serial)])

        # trend
        SectionHeader(d, self.app, t("DESK_HIST_TREND")).grid(row=r, column=0, sticky="w",
                                                 padx=16, pady=(12, 4)); r += 1
        self.metric_sel = ctk.CTkSegmentedButton(
            d, values=[self._metric_labels[m] for m in _METRICS], font=self.app.f_small,
            fg_color=theme.PANEL2, selected_color=theme.ACCENT_DIM, text_color=theme.TEXT,
            unselected_color=theme.PANEL2, command=self._on_metric)
        self.metric_sel.set(self._metric_labels[self._metric])
        self.metric_sel.grid(row=r, column=0, sticky="w", padx=16); r += 1
        self.trend = TrendCanvas(d)
        self.trend.grid(row=r, column=0, sticky="ew", padx=14, pady=(6, 6)); r += 1
        self._draw_trend()

        # repairs
        SectionHeader(d, self.app, t("DESK_HIST_REPAIRS")).grid(row=r, column=0, sticky="w",
                                                   padx=16, pady=(10, 4)); r += 1
        reps = dbmod.get_repair_sessions(self.app.conn, self.selected_serial)
        if not reps:
            ctk.CTkLabel(d, text=t("DESK_HIST_NO_REPAIRS"), font=self.app.f_small,
                         text_color=theme.DIM).grid(row=r, column=0, sticky="w",
                                                    padx=16); r += 1
        else:
            for rep in reps:
                r = self._repair_row(d, r, rep)

        # readings table
        SectionHeader(d, self.app, t("DESK_HIST_READINGS")).grid(row=r, column=0, sticky="w",
                                                    padx=16, pady=(12, 4)); r += 1
        for rd in reversed(hist):
            r = self._reading_row(d, r, rd)
        ctk.CTkFrame(d, fg_color="transparent", height=8).grid(row=r, column=0)

    def _repair_row(self, d, r, rep):
        held = rep["held"]
        kind = "green" if held == 1 else ("red" if held == 0 else "muted")
        txt = (t("DESK_RPR_HELD") if held == 1
               else t("DESK_RPR_RELOCKED") if held == 0 else t("DESK_RPR_UNKNOWN"))
        row = ctk.CTkFrame(d, fg_color=theme.PANEL2, corner_radius=8)
        row.grid(row=r, column=0, sticky="ew", padx=16, pady=3)
        row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(row, text=f"{human_dt(rep['started_at'])} · {rep['verdict_before']} "
                               f"→ {t('DESK_HIST_UNLOCK_ACTION')}",
                     font=self.app.f_small, text_color=theme.TEXT, anchor="w").grid(
            row=0, column=0, sticky="w", padx=10, pady=6)
        StatusBadge(row, self.app, txt.upper(), kind).grid(row=0, column=1, padx=10)
        return r + 1

    def _reading_row(self, d, r, rd):
        v = Verdict(rd["verdict"]) if rd["verdict"] else Verdict.UNKNOWN
        row = ctk.CTkFrame(d, fg_color="transparent")
        row.grid(row=r, column=0, sticky="ew", padx=16, pady=1)
        row.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(row, text=human_dt(rd["read_at"]), font=self.app.f_mono,
                     text_color=theme.MUTED, width=150, anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row, text=f"{(rd['pack_voltage_mv'] or 0)/1000:.2f} V",
                     font=self.app.f_small, text_color=theme.TEXT, width=70,
                     anchor="w").grid(row=0, column=1, sticky="w", padx=8)
        StatusBadge(row, self.app, t(verdict_key(v)), verdict_kind(v)).grid(
            row=0, column=3, sticky="e")
        for wdg in row.winfo_children() + [row]:
            wdg.bind("<Button-1>", lambda e, rid=rd["id"]: self._open_reading(rid))
        return r + 1

    def _on_metric(self, metric_label):
        self._metric = self._metric_key.get(metric_label, "Pack V")
        self._draw_trend()

    def _draw_trend(self):
        vals, unit = _metric_series(self._hist, self._metric)
        self.trend.set_series(vals, unit)

    # ------------------------------------------------------------- dialogs
    def _edit_identity(self):
        serial = self.selected_serial
        bat = dbmod.get_battery(self.app.conn, serial)
        win = ctk.CTkToplevel(self)
        win.title(t("DESK_HIST_EDIT_TITLE"))
        win.configure(fg_color=theme.BG)
        win.geometry("380x430")
        win.transient(self.winfo_toplevel())

        def field(label, r, val=""):
            ctk.CTkLabel(win, text=label, font=self.app.f_small,
                         text_color=theme.MUTED).grid(row=r, column=0, sticky="w",
                                                      padx=18, pady=(10, 0))
            e = ctk.CTkEntry(win, width=320, font=self.app.f_body, fg_color=theme.PANEL2,
                             border_color=theme.BORDER2)
            e.insert(0, val or "")
            e.grid(row=r + 1, column=0, padx=18)
            return e
        win.grid_columnconfigure(0, weight=1)
        e_alias = field(t("DESK_HIST_F_ALIAS"), 0, bat["alias"] if bat else "")
        e_owner = field(t("DESK_HIST_F_OWNER"), 2, bat["owner"] if bat else "")
        ctk.CTkLabel(win, text=t("DESK_HIST_STATUS"), font=self.app.f_small,
                     text_color=theme.MUTED).grid(row=4, column=0, sticky="w", padx=18, pady=(10, 0))
        st = ctk.CTkOptionMenu(win, values=list(self._status_labels.values()),
                               font=self.app.f_body, fg_color=theme.PANEL2,
                               button_color=theme.BORDER2, text_color=theme.TEXT,
                               dropdown_fg_color=theme.PANEL2, dropdown_text_color=theme.TEXT)
        st.set(self._status_labels.get((bat["status"] if bat else "") or "", "—"))
        st.grid(row=5, column=0, sticky="w", padx=18)
        e_tags = field(t("DESK_HIST_F_TAGS"), 6,
                       ", ".join(dbmod.battery_tags(bat)) if bat else "")

        def save():
            label_to_key = self._status_label_to_key
            tags = [x.strip() for x in e_tags.get().split(",") if x.strip()]
            dbmod.upsert_battery(self.app.conn, serial, alias=e_alias.get(),
                                 owner=e_owner.get(), status=label_to_key.get(st.get(), ""),
                                 tags=tags)
            win.destroy()
            self.refresh()
            self._select(serial)
        ctk.CTkButton(win, text=t("DESK_HIST_SAVE"), font=self.app.f_body, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, text_color=theme.ACCENT_INK,
                      command=save).grid(row=8, column=0, sticky="w", padx=18, pady=18)

    def _open_reading(self, reading_id):
        rd = dbmod.get_reading(self.app.conn, reading_id)
        if not rd:
            return
        win = ctk.CTkToplevel(self)
        win.title(f"Reading #{reading_id}")
        win.configure(fg_color=theme.BG)
        win.geometry("560x560")
        win.transient(self.winfo_toplevel())
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(0, weight=1)
        box = ctk.CTkTextbox(win, font=self.app.f_mono, fg_color=theme.PANEL,
                             text_color=theme.TEXT, border_width=0)
        box.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        try:
            cells = json.loads(rd["cell_voltages_mv"] or "[]")
        except (json.JSONDecodeError, TypeError):
            cells = []
        try:
            rc = json.loads(rd["gamme_data_json"] or "{}")
        except (json.JSONDecodeError, TypeError):
            rc = {}
        lines = [
            f"Model        {rd['model']}",
            f"S/N          {rd['serial_no']}",
            f"Read at      {human_dt(rd['read_at'])}",
            f"Verdict      {rd['verdict']}",
            f"Detail       {rd['verdict_detail']}",
            "",
            f"Pack         {(rd['pack_voltage_mv'] or 0)/1000:.2f} V",
            f"Cells (mV)   {cells}",
            f"Temp cell    {rd['temp1_c']} °C  (fault={rd['temp1_fault']})"
            if rd['temp1_c'] is not None else "Temp cell    —",
            f"Temp board   {rd['temp2_c']} °C  (fault={rd['temp2_fault']})"
            if rd['temp2_c'] is not None else "Temp board   —",
            f"Capacity     {rd['capacity_ah']} Ah",
            f"Cycles       {rd['cycle_count']}",
            f"Locked       {rd['locked']}   ChargerLock {rd['charger_locked']}",
            f"Fault 58D/309 {rc.get('fault_marker_58d')} / {rc.get('fault_marker_309')}",
            f"Over-disch   {rc.get('od_event_count') if rc.get('ext_valid') else '—'} evt"
            f"   threshold {rc.get('overdischarge_pct')}%",
            f"Over-load    {rc.get('ol_event_count') if rc.get('ext_valid') else '—'} evt"
            f"   threshold {rc.get('overload_pct')}%",
            f"SOC raw      {rc.get('soc_raw')}   (ext_valid={rc.get('ext_valid')})",
            f"Produced     {rd['production_date']}   Assembled {rd['assembly_date']}",
            f"FW           {rd['fw_version']}",
            f"Note         {rd['user_note']}",
            "",
            "Raw frame:",
            rd["raw_frame_hex"] or "",
        ]
        box.insert("1.0", "\n".join(lines))
        box.configure(state="disabled")

    def _compare(self):
        hist = self._hist
        if len(hist) < 2:
            return
        win = ctk.CTkToplevel(self)
        win.title(t("DESK_HIST_CMP_TITLE"))
        win.configure(fg_color=theme.BG)
        win.geometry("700x600")
        win.transient(self.winfo_toplevel())
        win.grid_columnconfigure(0, weight=1)
        win.grid_rowconfigure(2, weight=1)

        labels = [f"{i + 1}. {human_dt(r['read_at'])}  ({r['verdict']})"
                  for i, r in enumerate(hist)]
        picker = ctk.CTkFrame(win, fg_color="transparent")
        picker.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        sel_a = ctk.CTkOptionMenu(picker, values=labels, font=self.app.f_small, width=300,
                                  fg_color=theme.PANEL2, button_color=theme.BORDER2,
                                  text_color=theme.TEXT, dropdown_fg_color=theme.PANEL2,
                                  dropdown_text_color=theme.TEXT)
        sel_a.set(labels[0])
        sel_a.grid(row=0, column=0, padx=(0, 8))
        sel_b = ctk.CTkOptionMenu(picker, values=labels, font=self.app.f_small, width=300,
                                  fg_color=theme.PANEL2, button_color=theme.BORDER2,
                                  text_color=theme.TEXT, dropdown_fg_color=theme.PANEL2,
                                  dropdown_text_color=theme.TEXT)
        sel_b.set(labels[-1])
        sel_b.grid(row=0, column=1)

        content = ctk.CTkFrame(win, fg_color="transparent")
        content.grid(row=1, column=0, sticky="ew", padx=16)
        content.grid_columnconfigure((1, 2), weight=1, uniform="cmp")
        diffbox = ctk.CTkTextbox(win, font=self.app.f_mono, fg_color=theme.PANEL,
                                 text_color=theme.TEXT, border_width=0)
        diffbox.grid(row=2, column=0, sticky="nsew", padx=16, pady=12)

        def render(_=None):
            for w in content.winfo_children():
                w.destroy()
            ra, rb = hist[labels.index(sel_a.get())], hist[labels.index(sel_b.get())]
            ma, mb = self._row_metrics(ra), self._row_metrics(rb)
            ctk.CTkLabel(content, text="", font=self.app.f_small).grid(row=0, column=0)
            ctk.CTkLabel(content, text="A", font=self.app.f_small,
                         text_color=theme.MUTED).grid(row=0, column=1, sticky="w")
            ctk.CTkLabel(content, text="B", font=self.app.f_small,
                         text_color=theme.MUTED).grid(row=0, column=2, sticky="w")
            for i, k in enumerate(ma, 1):
                diff = ma[k] != mb[k]
                col = theme.ACCENT if diff else theme.TEXT
                ctk.CTkLabel(content, text=k, font=self.app.f_small,
                             text_color=theme.MUTED).grid(row=i, column=0, sticky="w", pady=2)
                ctk.CTkLabel(content, text=ma[k], font=self.app.f_small,
                             text_color=col).grid(row=i, column=1, sticky="w")
                ctk.CTkLabel(content, text=mb[k], font=self.app.f_small,
                             text_color=col).grid(row=i, column=2, sticky="w")
            # frame diff
            fa, fb = self._msg_bytes(ra), self._msg_bytes(rb)
            diffbox.configure(state="normal")
            diffbox.delete("1.0", "end")
            diffbox.insert("end", "FRAME DIFF (static 32-byte message)\n\n")
            if len(fa) >= 32 and len(fb) >= 32:
                diffs = decode.frame_diff(fa, fb)
                if not diffs:
                    diffbox.insert("end", "Frames identical.\n")
                for n, byte, old, new, lab in diffs:
                    diffbox.insert("end",
                                   f"nybble {n:>2} (byte {byte:>2})  {old:X} -> {new:X}"
                                   f"   {lab}\n")
            else:
                diffbox.insert("end", "No raw frame stored for one of these readings.\n")
            diffbox.configure(state="disabled")

        sel_a.configure(command=render)
        sel_b.configure(command=render)
        render()

    def _row_metrics(self, r):
        try:
            cv = [c / 1000.0 for c in json.loads(r["cell_voltages_mv"] or "[]") if c]
        except (json.JSONDecodeError, TypeError):
            cv = []
        spread = (max(cv) - min(cv)) if cv else 0.0
        t1, t2 = r["temp1_c"], r["temp2_c"]
        unit = self.app.settings.temp_unit
        temp = (f"{fmt_temp(t1, unit)} / {fmt_temp(t2, unit)}"
                if t1 is not None and t2 is not None else "—")
        yes, no = t("S_YES"), t("DESK_HIST_NO")
        return {
            t("DESK_HIST_ROW_VERDICT"): (r["verdict"] or "").replace("_", " "),
            t("DESK_HIST_ROW_PACKV"): f"{(r['pack_voltage_mv'] or 0) / 1000:.2f} V",
            t("DESK_HIST_ROW_CELLSPREAD"): f"{spread:.2f} V",
            t("DESK_HIST_ROW_TEMP"): temp,
            t("DESK_HIST_ROW_LOCKED"): yes if r["locked"] else no,
            t("DESK_HIST_ROW_CHGLOCK"): yes if r["charger_locked"] else no,
        }

    @staticmethod
    def _msg_bytes(r):
        try:
            raw = json.loads(r["raw_frame_hex"] or "{}")
            return bytes.fromhex(raw.get("msg", ""))
        except (json.JSONDecodeError, TypeError, ValueError):
            return b""

    def _export_health_card(self):
        if not self.selected_serial:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".html", filetypes=[("HTML", "*.html")],
            initialfile=f"health_{self.selected_serial}.html")
        if not path:
            return
        p = healthcard.export_health_card(self.app.conn, self.selected_serial, path,
                                          unit=self.app.settings.temp_unit)
        self.exp_status.configure(text=t("DESK_HIST_HEALTH_EXPORTED"),
                                  text_color=theme.GREEN)
        try:
            webbrowser.open(p.as_uri())
        except Exception:
            pass

    # ----------------------------------------------------------- export
    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile="pocketobi_readings.csv")
        if not path:
            return
        n = csvexport.export_csv(self.app.conn, path,
                                 column_set=self.app.settings.csv_columns)
        self.exp_status.configure(text=t("DESK_HIST_CSV_EXPORTED", n), text_color=theme.GREEN)

    def _export_report(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")],
            initialfile="pocketobi_report.json")
        if not path:
            return
        n = report.export_report_json(self.app.conn, path)
        self.exp_status.configure(
            text=t("DESK_HIST_REPORT_EXPORTED", n),
            text_color=theme.GREEN)

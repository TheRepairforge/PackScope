"""Live read screen — restyled: dominant hero + metric grid + graphical cells +
compact verdict banner. Composition over copy-paste (see components.py)."""

from __future__ import annotations

from datetime import date
import tkinter as tk

import customtkinter as ctk

from .. import db as dbmod
from .. import protocol
from ..i18n import t
from ..models import (
    CELL_V_MAX,
    CELL_V_MIN,
    Reading,
    TEMP_MAX_PLAUS,
    TEMP_MIN_PLAUS,
)
from ..units import fmt_delta, fmt_temp, fmt_wear, pack_age_years
from ..verdict import (
    cell_spread_grade,
    compute_verdict,
    health_band,
    thermistor_fault,
    thermistor_suspect,
    verdict_key,
    verdict_reason,
)
from . import theme
from .components import (
    Metric, SectionHeader, StatusBadge, VerdictBanner,
    color_of, divider, vdivider, verdict_kind,
)


def _implausible(t):
    return t < TEMP_MIN_PLAUS or t > TEMP_MAX_PLAUS


def _blend(h1, h2, t):
    """Linear blend of two #rrggbb colours (t=0 -> h1, t=1 -> h2)."""
    a = [int(h1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(h2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


class CellsCanvas(tk.Canvas):
    """Five vertical cell bars (value on top, C1..C5 below). Scale 2.5-4.2 V on
    purpose, so a weak group is visually obvious (a 0-based scale would hide it)."""

    def __init__(self, master, app):
        super().__init__(master, bg=theme.PANEL, highlightthickness=0, bd=0)
        self.app = app
        self.reading: Reading | None = None
        self.bind("<Configure>", lambda e: self._draw())

    def set_reading(self, r):
        self.reading = r
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 20 or h < 20:
            return
        cells = self.reading.cell if self.reading else [0] * 5
        mn = min([c for c in cells if c > 0.1], default=0)
        diff = (max(cells) - mn) if mn else 0
        top_pad, bot_pad = 26, 24
        n = len(cells)
        slot = w / n
        bar_w = min(46, slot * 0.5)
        t_top, t_bot = top_pad, h - bot_pad
        t_h = max(1, t_bot - t_top)
        for i, v in enumerate(cells):
            cx = slot * (i + 0.5)
            x0, x1 = cx - bar_w / 2, cx + bar_w / 2
            self.create_rectangle(x0, t_top, x1, t_bot, fill=theme.PANEL2, outline="")
            if v > 0.1:
                frac = max(0.04, min(1.0, (v - CELL_V_MIN) / (CELL_V_MAX - CELL_V_MIN)))
                col = theme.cell_color(v, mn, diff)
                top_y = t_bot - t_h * frac
                # vertical gradient (lighter at the top -> slightly darker at the base)
                c_top, c_bot = _blend(col, "#ffffff", 0.30), _blend(col, "#000000", 0.12)
                hh = t_bot - top_y
                steps = max(1, int(hh / 2))
                for s in range(steps):
                    yy0 = top_y + hh * s / steps
                    c = _blend(c_top, c_bot, s / max(1, steps - 1))
                    self.create_rectangle(x0, yy0, x1, top_y + hh * (s + 1) / steps,
                                          fill=c, outline="")
                self.create_text(cx, t_top - 12, text=f"{v:.2f}", fill=theme.TEXT,
                                 font=(theme.MONO_FAMILY, 11))
            self.create_text(cx, t_bot + 12, text=f"C{i + 1}", fill=theme.MUTED,
                             font=(theme.FONT_FAMILY, 11))


class LiveReadFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.app = app
        self.reading: Reading | None = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # action row
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 10))
        self.read_btn = ctk.CTkButton(top, text=t("DESK_READ_PACK"), font=app.f_body, height=38,
                                      corner_radius=8, fg_color=theme.ACCENT,
                                      hover_color=theme.ACCENT_HOVER,
                                      text_color=theme.ACCENT_INK, command=self._read)
        self.read_btn.grid(row=0, column=0)
        self.status = ctk.CTkLabel(top, text=t("DESK_CONNECT_FIRST_HINT"),
                                   font=app.f_small, text_color=theme.MUTED,
                                   justify="left", wraplength=560)
        self.status.grid(row=0, column=1, padx=14, sticky="w")

        # hero card (single card, no border; contrast via surfaces)
        card = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=12)
        card.grid(row=1, column=0, sticky="nsew", padx=24, pady=6)
        card.grid_columnconfigure(0, weight=92, uniform="hero")
        card.grid_columnconfigure(2, weight=108, uniform="hero")
        card.grid_rowconfigure(0, weight=1)
        vdivider(card).grid(row=0, column=1, sticky="ns", pady=18)

        self._build_hero(card)
        self._build_cells(card)

        # verdict banner
        self.banner = VerdictBanner(self, app)
        self.banner.grid(row=2, column=0, sticky="ew", padx=24, pady=(8, 6))

        # actions
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 16))
        self.save_btn = ctk.CTkButton(actions, text=t("DESK_SAVE_READING"), font=app.f_body,
                                      height=36, corner_radius=8, fg_color="transparent",
                                      border_width=1, border_color=theme.BORDER2,
                                      hover_color=theme.PANEL, text_color=theme.TEXT,
                                      command=self._save, state="disabled")
        self.save_btn.grid(row=0, column=0)

    def _build_hero(self, card):
        app = self.app
        hero = ctk.CTkFrame(card, fg_color="transparent")
        hero.grid(row=0, column=0, sticky="nsew", padx=(20, 16), pady=14)
        hero.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(hero, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew")
        head.grid_columnconfigure(0, weight=1)
        self.l_model = ctk.CTkLabel(head, text="—", font=app.f_model,
                                    text_color=theme.TEXT, anchor="w")
        self.l_model.grid(row=0, column=0, sticky="w")
        self.badge = StatusBadge(head, app, t("S_NO_PACK"), "muted")
        self.badge.grid(row=0, column=1, sticky="e")
        self.l_sn = ctk.CTkLabel(hero, text=f"{t('S_SN')} —", font=app.f_mono,
                                 text_color=theme.MUTED, anchor="w")
        self.l_sn.grid(row=1, column=0, sticky="w", pady=(2, 0))
        # Production date (+ age) — identity info, right under the S/N and in the
        # same mono style. A plain proxy for how old the pack is.
        self.l_produced = ctk.CTkLabel(hero, text="", font=app.f_mono,
                                       text_color=theme.MUTED, anchor="w")
        self.l_produced.grid(row=2, column=0, sticky="w", pady=(1, 0))

        self.l_packv = ctk.CTkLabel(hero, text="—", font=app.f_packv,
                                    text_color=theme.TEXT, anchor="w")
        self.l_packv.grid(row=3, column=0, sticky="w", pady=(8, 0))
        sub = ctk.CTkFrame(hero, fg_color="transparent")
        sub.grid(row=4, column=0, sticky="w")
        SectionHeader(sub, app, t("DESK_PACK_VOLTAGE")).grid(row=0, column=0, sticky="w")
        self.l_nominal = ctk.CTkLabel(sub, text="", font=app.f_small,
                                      text_color=theme.DIM, anchor="w")
        self.l_nominal.grid(row=0, column=1, sticky="w", padx=(10, 0))

        # Our OWN cycle-based health estimate (NOT the Makita SOH gauge, which we
        # don't fake): a 3-colour bar + %. Distinct axis from the verdict badge
        # (repairability): a pack can be worn yet still HEALTHY.
        hb = ctk.CTkFrame(hero, fg_color="transparent")
        hb.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        hb.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(hb, text=t("DESK_HEALTH_EST"), font=app.f_small,
                     text_color=theme.MUTED, anchor="w").grid(row=0, column=0, sticky="w")
        self.health_bar = ctk.CTkProgressBar(hb, height=10, corner_radius=5)
        self.health_bar.set(0)
        self.health_bar.grid(row=0, column=1, sticky="ew", padx=10)
        self.health_pct = ctk.CTkLabel(hb, text="—", font=app.f_body, text_color=theme.MUTED)
        self.health_pct.grid(row=0, column=2, sticky="e")

        divider(hero).grid(row=6, column=0, sticky="ew", pady=10)

        grid = ctk.CTkFrame(hero, fg_color="transparent")
        grid.grid(row=7, column=0, sticky="ew")
        grid.grid_columnconfigure(0, weight=1, uniform="m")
        grid.grid_columnconfigure(1, weight=1, uniform="m")
        grid.grid_columnconfigure(2, weight=1, uniform="m")
        self.m_cycles = Metric(grid, app, t("DESK_CYCLES"))
        # BMS wear counters — same S_ labels as the device Health page (no gap).
        self.m_od = Metric(grid, app, t("S_OVERDISCHARGE"))
        self.m_ol = Metric(grid, app, t("S_OVERLOAD"))
        self.m_tcell = Metric(grid, app, t("DESK_CELL_TEMP"))
        self.m_tboard = Metric(grid, app, t("DESK_BOARD_TEMP"))
        self.m_tspread = Metric(grid, app, t("DESK_TEMP_SPREAD"))
        # Row 0 = usage/wear, Row 1 = temperature. Capacity moved to the header
        # (it is a spec, not a health metric); cell spread moved next to the bars.
        placement = [(self.m_cycles, 0, 0), (self.m_od, 0, 1), (self.m_ol, 0, 2),
                     (self.m_tcell, 1, 0), (self.m_tboard, 1, 1), (self.m_tspread, 1, 2)]
        for m, rr, cc in placement:
            m.grid(row=rr, column=cc, sticky="ew",
                   pady=(0, 8) if rr < 1 else 0, padx=(0, 10))

    def _build_cells(self, card):
        cells = ctk.CTkFrame(card, fg_color="transparent")
        cells.grid(row=0, column=2, sticky="nsew", padx=(16, 20), pady=18)
        cells.grid_columnconfigure(0, weight=1)
        cells.grid_rowconfigure(1, weight=1)
        hdr = ctk.CTkFrame(cells, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)
        SectionHeader(hdr, self.app, t("DESK_CELL_VOLTAGES")).grid(row=0, column=0, sticky="w")
        # Cell balance (Δ = max-min) lives with the bars it summarises, coloured by scale.
        self.l_cspread = ctk.CTkLabel(hdr, text="—", font=self.app.f_small,
                                      text_color=theme.MUTED, anchor="e")
        self.l_cspread.grid(row=0, column=1, sticky="e")
        self.cells = CellsCanvas(cells, self.app)
        self.cells.grid(row=1, column=0, sticky="nsew", pady=(6, 0))

    # ------------------------------------------------------------- actions
    def _read(self):
        if self.app.bridge is None:
            self.status.configure(text=t("DESK_NOT_CONNECTED"),
                                  text_color=theme.AMBER)
            return
        self.read_btn.configure(state="disabled", text=t("DESK_READING"))
        self.status.configure(text=t("DESK_READING_PACK"), text_color=theme.MUTED)

        def done(r):
            self.read_btn.configure(state="normal", text=t("DESK_READ_PACK"))
            if not r.valid:
                self.status.configure(text=t("DESK_NO_PACK_DETECTED"), text_color=theme.AMBER)
                return
            self.render(r)
            self.status.configure(text=t("DESK_READ_OK"), text_color=theme.GREEN)

        def err(exc):
            self.read_btn.configure(state="normal", text=t("DESK_READ_PACK"))
            msg = str(exc).lower()
            if "timeout" in msg or "got 0" in msg:
                text = t("DESK_READ_FAIL_BRIDGE")
            else:
                text = t("DESK_READ_FAIL", exc)
            self.status.configure(text=text, text_color=theme.RED)

        self.app.run_async(lambda: protocol.read_all(self.app.bridge), done, err)

    def _save(self):
        if not (self.reading and self.reading.valid):
            return
        try:
            rid = dbmod.insert_reading(self.app.conn, self.reading,
                                       fw_version=self.app.fw_version)
        except Exception as exc:  # noqa: BLE001
            self.status.configure(text=t("DESK_SAVE_FAIL", exc), text_color=theme.RED)
            return
        self.status.configure(text=t("DESK_SAVED_READING", rid),
                              text_color=theme.GREEN)

    # -------------------------------------------------------------- render
    def render(self, r: Reading):
        self.reading = r
        v = compute_verdict(r)
        self.l_model.configure(text=r.model or "—")
        self.badge.set(t(verdict_key(v)), verdict_kind(v))
        self.l_sn.configure(text=f"{t('S_SN')} {r.serial_no or '—'}")
        self.l_packv.configure(text=f"{r.pack_voltage:.2f} V")
        cells_n = len(r.cell)
        cap = f"  ·  {r.capacity_ah:.1f} Ah" if r.capacity_ah else ""
        self.l_nominal.configure(text=t("DESK_NOMINAL", cells_n) + cap)

        # Our health estimate (cycle-based). F0513 packs report no cycle data.
        if r.is_f0513:
            self.health_bar.set(0)
            self.health_bar.configure(progress_color=theme.MUTED)
            self.health_pct.configure(text="—", text_color=theme.MUTED)
        else:
            hp = r.health_est_pct
            hcol = color_of(health_band(hp))
            self.health_bar.set(hp / 100)
            self.health_bar.configure(progress_color=hcol)
            self.health_pct.configure(text=f"{hp}%", text_color=hcol)

        self.m_cycles.set(str(r.charge_count))

        # temperatures (cell / board), each coloured by its own plausibility
        unit = self.app.settings.temp_unit
        tc_col = theme.RED if (not r.is_f0513 and _implausible(r.temp_cell)) else theme.TEXT
        self.m_tcell.set(fmt_temp(r.temp_cell, unit), tc_col)
        if not r.board_temp_valid:      # single-sensor read (F0513 or D7 fallback): no 2nd temp
            self.m_tboard.set("—", theme.MUTED)
            self.m_tspread.set("—", theme.MUTED)
        else:
            tb_col = theme.RED if _implausible(r.temp_mosfet) else theme.TEXT
            self.m_tboard.set(fmt_temp(r.temp_mosfet, unit), tb_col)
            ts_col = (theme.RED if thermistor_fault(r) else
                      theme.ORANGE if thermistor_suspect(r) else theme.TEXT)
            self.m_tspread.set(fmt_delta(abs(r.temp_mosfet - r.temp_cell), unit), ts_col)

        # Cell balance next to the bars: Δ = max-min, coloured by scale.
        _, gkind = cell_spread_grade(r.cell_diff)
        self.l_cspread.configure(text=f"Δ {r.cell_diff:.2f} V", text_color=color_of(gkind))

        # Over-discharge / over-load: event count as "N×" ("how many times the
        # protection tripped"). "—" when the extended read didn't survive the bridge;
        # a non-zero count is a neutral wear signal (not a fault), 0 is clean. The
        # protection threshold is intentionally not shown here (it's static config).
        for m, ev in ((self.m_od, r.od_event_count), (self.m_ol, r.ol_event_count)):
            col = theme.MUTED if not r.ext_valid else (theme.TEXT if ev else theme.GREEN)
            m.set(fmt_wear(r.ext_valid, ev), col)

        # Production date (+ age in whole years) under the S/N, same mono style.
        prod = r.mfg_date_iso()
        if prod:
            age = pack_age_years(prod, date.today())
            txt = f"{t('S_PRODUCED')} {prod}"
            if age is not None:
                txt += f"  ({t('DESK_AGE_YEARS', age)})"
        else:
            txt = ""
        self.l_produced.configure(text=txt)

        self.cells.set_reading(r)
        self.banner.show(v, t(verdict_key(v)), verdict_reason(r))
        self.save_btn.configure(state="normal")

    def on_show(self):
        pass

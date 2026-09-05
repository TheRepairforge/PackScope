"""Settings screen — display/connection/data preferences, persisted via config."""

from __future__ import annotations

import customtkinter as ctk

from .. import config
from .. import db as dbmod
from .. import i18n
from ..i18n import t
from . import theme
from .components import SectionHeader, divider

# Temperature symbols are universal — not translated. Appearance/CSV display
# labels ARE translated, so their display<->code maps are built per instance
# (below) from i18n.t() at construction time.
_UNIT = {"°C": "C", "°F": "F"}
_UNIT_INV = {v: k for k, v in _UNIT.items()}
_LANG = {"EN": "en", "FR": "fr", "DE": "de", "ES": "es"}
_LANG_INV = {v: k for k, v in _LANG.items()}


def _card(master):
    return ctk.CTkFrame(master, fg_color=theme.PANEL, corner_radius=12)


class SettingsFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.app = app
        self.grid_columnconfigure(0, weight=1)

        # Translated display <-> stored code maps (rebuilt on a language switch).
        self._appear = {t("DESK_SET_DARK"): "dark", t("DESK_SET_LIGHT"): "light"}
        self._appear_inv = {v: k for k, v in self._appear.items()}
        self._csv = {t("DESK_SET_CSV_MAKITA"): "makita", t("DESK_SET_CSV_FULL"): "full"}
        self._csv_inv = {v: k for k, v in self._csv.items()}

        card = _card(self)
        card.grid(row=0, column=0, sticky="nw", padx=24, pady=18)
        card.grid_columnconfigure(0, weight=1)
        self._r = 0

        self._header(card, t("DESK_SET_DISPLAY"))
        self.seg_appear = ctk.CTkSegmentedButton(
            self._line(card, t("DESK_SET_APPEARANCE")), values=list(self._appear),
            font=app.f_small, fg_color=theme.PANEL2, selected_color=theme.ACCENT_DIM, text_color=theme.TEXT,
            unselected_color=theme.PANEL2,
            command=lambda v: self.after(10, lambda: self.app.apply_appearance(self._appear[v])))
        self.seg_appear.grid(row=0, column=1, sticky="e")
        self.seg_lang = ctk.CTkSegmentedButton(
            self._line(card, t("S_LANGUAGE")), values=list(_LANG),
            font=app.f_small, fg_color=theme.PANEL2, selected_color=theme.ACCENT_DIM, text_color=theme.TEXT,
            unselected_color=theme.PANEL2,
            command=lambda v: self.after(10, lambda: self.app.apply_language(_LANG[v])))
        self.seg_lang.grid(row=0, column=1, sticky="e")
        self.seg_unit = ctk.CTkSegmentedButton(
            self._line(card, t("DESK_SET_TEMP_UNIT")), values=list(_UNIT),
            font=app.f_small, fg_color=theme.PANEL2, selected_color=theme.ACCENT_DIM, text_color=theme.TEXT,
            unselected_color=theme.PANEL2)
        self.seg_unit.grid(row=0, column=1, sticky="e")
        self.seg_csv = ctk.CTkSegmentedButton(
            self._line(card, t("DESK_SET_CSV_COLS")), values=list(self._csv),
            font=app.f_small, fg_color=theme.PANEL2, selected_color=theme.ACCENT_DIM, text_color=theme.TEXT,
            unselected_color=theme.PANEL2)
        self.seg_csv.grid(row=0, column=1, sticky="e")

        self._divider(card)
        self._header(card, t("DESK_SET_CONNECTION"))
        self.port = ctk.CTkEntry(self._line(card, t("DESK_SET_DEFAULT_PORT")), width=260,
                                 font=app.f_body, fg_color=theme.PANEL2,
                                 border_color=theme.BORDER2, text_color=theme.TEXT,
                                 placeholder_text=t("DESK_SET_PORT_PH"))
        self.port.grid(row=0, column=1, sticky="e")

        self._divider(card)
        self._header(card, t("DESK_SET_DATA"))
        self.db_lbl = ctk.CTkLabel(card, text="", font=app.f_small, text_color=theme.MUTED,
                                   wraplength=620, justify="left", anchor="w")
        self.db_lbl.grid(row=self._next(), column=0, sticky="w", padx=18, pady=(0, 2))
        ctk.CTkButton(card, text=t("DESK_SET_CLEAR"), font=app.f_small, height=30,
                      fg_color="transparent", border_width=1, border_color=theme.RED,
                      hover_color=theme.RED_BG, text_color=theme.RED,
                      command=self._clear).grid(row=self._next(), column=0, sticky="w",
                                                padx=18, pady=(4, 8))

        self._divider(card)
        bar = ctk.CTkFrame(card, fg_color="transparent")
        bar.grid(row=self._next(), column=0, sticky="w", padx=18, pady=(0, 16))
        ctk.CTkButton(bar, text=t("DESK_SET_SAVE"), font=app.f_body, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, text_color=theme.ACCENT_INK,
                      command=self._save).grid(row=0, column=0)
        self.status = ctk.CTkLabel(bar, text="", font=app.f_small, text_color=theme.MUTED)
        self.status.grid(row=0, column=1, padx=12)

    # --- layout helpers ---
    def _next(self):
        r = self._r
        self._r += 1
        return r

    def _header(self, card, text):
        SectionHeader(card, self.app, text).grid(row=self._next(), column=0, sticky="w",
                                                 padx=18, pady=(14, 6))

    def _divider(self, card):
        divider(card).grid(row=self._next(), column=0, sticky="ew", padx=18, pady=12)

    def _line(self, card, label):
        line = ctk.CTkFrame(card, fg_color="transparent")
        line.grid(row=self._next(), column=0, sticky="ew", padx=18, pady=4)
        line.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(line, text=label, font=self.app.f_body,
                     text_color=theme.TEXT).grid(row=0, column=0, sticky="w")
        return line

    # --- behaviour ---
    def on_show(self):
        s = self.app.settings
        self.seg_appear.set(self._appear_inv.get(s.appearance, t("DESK_SET_DARK")))
        self.seg_lang.set(_LANG_INV.get(i18n.current(), "EN"))
        self.seg_unit.set(_UNIT_INV.get(s.temp_unit, "°C"))
        self.seg_csv.set(self._csv_inv.get(s.csv_columns, t("DESK_SET_CSV_FULL")))
        self.port.delete(0, "end")
        self.port.insert(0, s.serial_port or "")
        self.db_lbl.configure(text=t("DESK_SET_DB_FILE", s.resolved_db_path()))
        self.status.configure(text="")

    def _save(self):
        s = self.app.settings
        s.temp_unit = _UNIT.get(self.seg_unit.get(), "C")
        s.csv_columns = self._csv.get(self.seg_csv.get(), "full")
        s.serial_port = self.port.get().strip()
        config.save_settings(s)
        self.status.configure(text=t("DESK_SET_SAVED"), text_color=theme.GREEN)

    def _clear(self):
        win = ctk.CTkToplevel(self)
        win.title(t("DESK_SET_CLEAR_TITLE"))
        win.configure(fg_color=theme.BG)
        win.geometry("400x170")
        win.transient(self.winfo_toplevel())
        ctk.CTkLabel(win, text=t("DESK_SET_CLEAR_MSG"), font=self.app.f_body,
                     text_color=theme.TEXT, justify="left").grid(
            row=0, column=0, columnspan=2, padx=20, pady=(22, 16), sticky="w")

        def do():
            dbmod.clear_history(self.app.conn)
            win.destroy()
            self.status.configure(text=t("DESK_SET_CLEARED"), text_color=theme.AMBER)
        ctk.CTkButton(win, text=t("DESK_SET_CLEAR_YES"), font=self.app.f_body, fg_color=theme.RED,
                      hover_color="#d64c4d", text_color="#ffffff", command=do).grid(
            row=1, column=0, padx=(20, 8), pady=8, sticky="w")
        ctk.CTkButton(win, text=t("DESK_SET_CANCEL"), font=self.app.f_body, fg_color=theme.PANEL2,
                      hover_color=theme.RAISED, text_color=theme.TEXT,
                      command=win.destroy).grid(
            row=1, column=1, pady=8, sticky="w")

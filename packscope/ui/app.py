"""Main application window: sidebar nav + top bar + the three screens."""

from __future__ import annotations

import threading
from typing import Callable, Optional

import customtkinter as ctk

from .. import __version__
from .. import i18n
from ..bridge import BridgeClient
from ..config import Settings, load_settings
from .. import db as dbmod
from . import theme
from . import assets
from .about import AboutFrame
from .connect import ConnectFrame
from .history import HistoryFrame
from .liveread import LiveReadFrame
from .repair import RepairFrame
from .settings import SettingsFrame

# (key, i18n label key, glyph). Repair/Settings/About reuse the firmware keys so
# their wording matches the device; Connect/Live/Batteries are Desk-only (DESK_*).
# Labels are resolved via i18n.t() at build time, so apply_language re-translates them.
NAV = [
    ("connect", "DESK_NAV_CONNECT", "⌗"),   # plug-ish glyph
    ("live", "DESK_NAV_LIVE", "■"),
    ("repair", "S_REPAIR", "✚"),
    ("history", "DESK_NAV_BATTERIES", "≣"),
    ("settings", "S_SETTINGS", "⚙"),
    ("about", "S_ABOUT", "ⓘ"),
]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PackScope")
        self.geometry("1040x720")
        self.minsize(940, 660)

        # --- shared state ---
        self.settings: Settings = load_settings()
        self.conn = dbmod.connect(self.settings.resolved_db_path())
        self.bridge: Optional[BridgeClient] = None
        self.device_gamme: Optional[int] = None   # family id from the bridge contract
        self.fw_version: str = ""
        self.connection_label: str = ""     # "COM7" or "Demo"
        self._current = "connect"

        i18n.set_language(self.settings.language)
        theme.apply(self.settings.appearance)
        ctk.set_appearance_mode("light" if theme.mode == "light" else "dark")
        self.configure(fg_color=theme.BG)

        # --- fonts (need the root to exist) ---
        self.f_brand = ctk.CTkFont(theme.FONT_FAMILY, 15, "bold")
        self.f_nav = ctk.CTkFont(theme.FONT_FAMILY, 14)
        self.f_title = ctk.CTkFont(theme.FONT_FAMILY, 16, "bold")
        self.f_body = ctk.CTkFont(theme.FONT_FAMILY, 13)
        self.f_small = ctk.CTkFont(theme.FONT_FAMILY, 12)
        self.f_label = ctk.CTkFont(theme.FONT_FAMILY, 11)
        self.f_mono = ctk.CTkFont(theme.MONO_FAMILY, 12)
        self.f_badge = ctk.CTkFont(theme.FONT_FAMILY, 11, "bold")
        self.f_model = ctk.CTkFont(theme.FONT_FAMILY, 22, "bold")
        self.f_packv = ctk.CTkFont(theme.FONT_FAMILY, 42, "bold")
        self.f_stat = ctk.CTkFont(theme.FONT_FAMILY, 17, "bold")

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_sidebar()
        self._build_topbar()
        self.screens = {
            "connect": ConnectFrame(self, self),
            "live": LiveReadFrame(self, self),
            "repair": RepairFrame(self, self),
            "history": HistoryFrame(self, self),
            "settings": SettingsFrame(self, self),
            "about": AboutFrame(self, self),
        }
        for s in self.screens.values():
            s.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
        self.show_screen(self._current)
        if self.bridge is not None and self.connection_label:
            self.set_connected(self.connection_label, self.fw_version)

    def apply_appearance(self, new_mode: str):
        """Switch light/dark: persist, re-theme, and rebuild the UI in place."""
        if new_mode == theme.mode:
            return
        self.settings.appearance = new_mode
        from .. import config
        config.save_settings(self.settings)
        theme.apply(new_mode)
        ctk.set_appearance_mode("light" if theme.mode == "light" else "dark")
        self.configure(fg_color=theme.BG)
        for w in list(self.grid_slaves()):
            w.destroy()
        self._build_ui()

    def apply_language(self, new_lang: str):
        """Switch UI language: persist, set i18n, and rebuild the UI in place
        (same mechanism as apply_appearance)."""
        if new_lang == i18n.current():
            return
        self.settings.language = new_lang
        from .. import config
        config.save_settings(self.settings)
        i18n.set_language(new_lang)
        for w in list(self.grid_slaves()):
            w.destroy()
        self._build_ui()

    # ------------------------------------------------------------------ nav
    def _build_sidebar(self):
        side = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=theme.SIDEBAR)
        side.grid(row=0, column=0, rowspan=2, sticky="nsew")
        side.grid_propagate(False)
        side.grid_rowconfigure(99, weight=1)
        side.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkFrame(side, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=14, pady=(16, 18))
        logo_img = assets.load("pocketobi_icon.png", 28, tint=theme.MAKITA_TEAL)
        if logo_img is not None:
            logo = ctk.CTkLabel(brand, text="", image=logo_img)
        else:
            logo = ctk.CTkLabel(brand, text="P", width=30, height=30, corner_radius=8,
                                fg_color=theme.ACCENT_DIM, text_color=theme.ACCENT_INK,
                                font=self.f_brand)
        logo.grid(row=0, column=0, padx=(0, 10))
        ctk.CTkLabel(brand, text="PackScope", font=self.f_brand,
                     text_color=theme.TEXT).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(brand, text="The Repair Forge", font=self.f_label,
                     text_color=theme.DIM).grid(row=1, column=1, sticky="w")

        self.nav_buttons = {}
        self.nav_bars = {}
        for i, (key, label_key, glyph) in enumerate(NAV):
            rowf = ctk.CTkFrame(side, fg_color="transparent")
            rowf.grid(row=1 + i, column=0, sticky="ew", padx=(0, 10), pady=3)
            rowf.grid_columnconfigure(1, weight=1)
            bar = ctk.CTkFrame(rowf, width=3, height=22, corner_radius=2,
                               fg_color="transparent")
            bar.grid(row=0, column=0, padx=(7, 8))
            btn = ctk.CTkButton(
                rowf, text=f" {glyph}   {i18n.t(label_key)}", anchor="w", height=42,
                corner_radius=8, font=self.f_nav, fg_color="transparent",
                hover_color=theme.PANEL, text_color=theme.MUTED,
                command=lambda k=key: self.show_screen(k),
            )
            btn.grid(row=0, column=1, sticky="ew")
            self.nav_buttons[key] = btn
            self.nav_bars[key] = bar

        self.side_status = ctk.CTkLabel(side, text="●  " + i18n.t("DESK_STATUS_NOT_CONNECTED"),
                                        font=self.f_small, text_color=theme.DIM)
        self.side_status.grid(row=100, column=0, sticky="w", padx=18, pady=14)

    def _build_topbar(self):
        top = ctk.CTkFrame(self, height=56, corner_radius=0, fg_color=theme.BG)
        top.grid(row=0, column=1, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        self.top_title = ctk.CTkLabel(top, text=i18n.t("DESK_NAV_CONNECT"), font=self.f_title,
                                      text_color=theme.TEXT)
        self.top_title.grid(row=0, column=0, sticky="w", padx=20, pady=14)
        self.top_chip = ctk.CTkLabel(top, text="●  " + i18n.t("DESK_STATUS_DISCONNECTED"), font=self.f_small,
                                     fg_color=theme.PANEL2, corner_radius=20,
                                     text_color=theme.MUTED, padx=12, pady=5)
        self.top_chip.grid(row=0, column=1, sticky="e", padx=20)
        ctk.CTkFrame(self, height=1, fg_color=theme.BORDER, corner_radius=0)\
            .grid(row=0, column=1, sticky="sew")

    def show_screen(self, key: str):
        self._current = key
        for k, btn in self.nav_buttons.items():
            on = k == key
            btn.configure(fg_color=theme.PANEL if on else "transparent",
                          text_color=theme.TEXT if on else theme.MUTED)
            self.nav_bars[k].configure(fg_color=theme.ACCENT if on else "transparent")
        for k, s in self.screens.items():
            (s.tkraise() if k == key else None)
        self.top_title.configure(text=i18n.t(dict((n[0], n[1]) for n in NAV)[key]))
        if hasattr(self.screens[key], "on_show"):
            self.screens[key].on_show()

    # --------------------------------------------------------------- status
    def set_connected(self, label: str, fw_version: str = ""):
        self.connection_label = label
        self.fw_version = fw_version
        txt = f"●  {label}" + (f" · fw {fw_version}" if fw_version else "")
        self.top_chip.configure(text=txt, text_color=theme.GREEN)
        self.side_status.configure(text=f"●  {label}", text_color=theme.GREEN)

    def set_disconnected(self):
        self.bridge = None
        self.connection_label = ""
        self.top_chip.configure(text="●  " + i18n.t("DESK_STATUS_DISCONNECTED"), text_color=theme.MUTED)
        self.side_status.configure(text="●  " + i18n.t("DESK_STATUS_NOT_CONNECTED"), text_color=theme.DIM)

    # ---------------------------------------------------------------- async
    def run_async(self, fn: Callable, on_done: Callable,
                  on_error: Optional[Callable] = None):
        """Run ``fn`` off the UI thread; deliver result/error on the UI thread."""
        def worker():
            try:
                res = fn()
            except Exception as exc:  # noqa: BLE001 - surfaced to the UI
                self.after(0, lambda e=exc: (on_error or self._default_error)(e))
                return
            self.after(0, lambda: on_done(res))

        threading.Thread(target=worker, daemon=True).start()

    def _default_error(self, exc: Exception):
        print("error:", exc)

    def destroy(self):  # noqa: D401 - close DB on exit
        try:
            self.conn.close()
        except Exception:
            pass
        super().destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

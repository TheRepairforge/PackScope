"""About screen — version, credits, links."""

from __future__ import annotations

import webbrowser

import customtkinter as ctk

from .. import __version__
from . import assets, theme
from .components import SectionHeader, divider

_YOUTUBE = "https://www.youtube.com/channel/UCQL_-pcIEkrDPyljl3QPzcw"
_GITHUB = "https://github.com/TheRepairforge/PocketOBI"

_CREDITS = (
    "Built on the Open Battery Information project by Martin Jansson (MIT) — the "
    "protocol groundwork PocketOBI reuses. Decode/verdict logic is a 1:1 port of the "
    "PocketOBI firmware. Protocol facts also draw on the rosvall, drakosha (MIT), "
    "synrais and m5din reverse-engineering work, used clean-room (facts, not code)."
)


class AboutFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.app = app
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=12)
        card.grid(row=0, column=0, sticky="nw", padx=24, pady=18)
        card.grid_columnconfigure(0, weight=1)

        self._egg_n = 0
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        logo_img = assets.load("pocketobi_icon.png", 40, tint=theme.MAKITA_TEAL)
        if logo_img is not None:
            self.logo_lbl = ctk.CTkLabel(head, text="", image=logo_img)
        else:
            self.logo_lbl = ctk.CTkLabel(head, text="P", width=34, height=34,
                                         corner_radius=9, fg_color=theme.ACCENT_DIM,
                                         text_color=theme.ACCENT_INK, font=app.f_brand)
        self.logo_lbl.grid(row=0, column=0, rowspan=3, padx=(0, 14))
        self.logo_lbl.bind("<Button-1>", self._egg)
        ctk.CTkLabel(head, text="PackScope", font=app.f_model,
                     text_color=theme.TEXT).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(head, text="The Repair Forge", font=app.f_small,
                     text_color=theme.MUTED).grid(row=1, column=1, sticky="w")
        ctk.CTkLabel(head, text="No guru meditation required.", font=app.f_small,
                     text_color=theme.MAKITA_TEAL).grid(row=2, column=1, sticky="w")
        # Repair Forge brand logo (shown when assets/repair_forge.png is present).
        rf = assets.load("repair_forge.png", 40, crop=True)
        if rf is not None:
            chip = ctk.CTkFrame(head, fg_color="#ffffff", corner_radius=10)
            chip.grid(row=0, column=2, rowspan=2, padx=(24, 0))
            ctk.CTkLabel(chip, text="", image=rf).grid(row=0, column=0, padx=12, pady=8)

        self.ver = ctk.CTkLabel(card, text="", font=app.f_body, text_color=theme.MUTED)
        self.ver.grid(row=1, column=0, sticky="w", padx=20, pady=(6, 2))
        ctk.CTkLabel(card, text="Standalone reader/diagnostic companion for Makita LXT "
                     "battery packs, over a PocketOBI USB-serial bridge.",
                     font=app.f_small, text_color=theme.MUTED, wraplength=560,
                     justify="left").grid(row=2, column=0, sticky="w", padx=20)

        divider(card).grid(row=3, column=0, sticky="ew", padx=20, pady=12)
        SectionHeader(card, app, "Credits").grid(row=4, column=0, sticky="w", padx=20)
        ctk.CTkLabel(card, text=_CREDITS, font=app.f_small, text_color=theme.TEXT,
                     wraplength=560, justify="left").grid(row=5, column=0, sticky="w",
                                                          padx=20, pady=(4, 0))

        divider(card).grid(row=6, column=0, sticky="ew", padx=20, pady=12)
        links = ctk.CTkFrame(card, fg_color="transparent")
        links.grid(row=7, column=0, sticky="w", padx=20, pady=(0, 18))
        ctk.CTkButton(links, text="YouTube — The Repair Forge", font=app.f_small, height=30,
                      fg_color="transparent", border_width=1, border_color=theme.BORDER2,
                      hover_color=theme.PANEL2, text_color=theme.TEXT,
                      command=lambda: webbrowser.open(_YOUTUBE)).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(links, text="GitHub — PocketOBI", font=app.f_small, height=30,
                      fg_color="transparent", border_width=1, border_color=theme.BORDER2,
                      hover_color=theme.PANEL2, text_color=theme.TEXT,
                      command=lambda: webbrowser.open(_GITHUB)).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(links, text="Check for updates", font=app.f_small, height=30,
                      fg_color="transparent", border_width=1, border_color=theme.BORDER2,
                      hover_color=theme.PANEL2, text_color=theme.TEXT,
                      command=lambda: webbrowser.open(_GITHUB + "/releases")).grid(
            row=0, column=2)

        self.egg = ctk.CTkLabel(card, text="", font=app.f_small,
                                text_color=theme.MAKITA_TEAL, anchor="w")
        self.egg.grid(row=8, column=0, sticky="w", padx=20, pady=(0, 16))

    _EGG = [
        "Guru Meditation Error 0x0BADCAFE: none found. Carry on.",
        "No batteries were harmed during the development of this software.",
        "No bugs to be found — only intentional features.",
        "Software Failure. Press left mouse button to continue.",          # Amiga
        "Guru Meditation #00000003.00C0FFEE — insert coffee to continue.",  # Amiga
        "Amiga would be proud. (RIP, old friend.)",
        "Percussive maintenance: strongly discouraged.",
        "Have you tried a slow charge and a cup of coffee?",
        "Forged with solder smoke and too much reverse-engineering.",
        "If found bricked: reflash gently, apologise sincerely.",
    ]

    def _egg(self, _=None):
        self._egg_n += 1
        if self._egg_n >= 5:
            self.egg.configure(text="⚡ " + self._EGG[(self._egg_n - 5) % len(self._EGG)])

    def on_show(self):
        fw = self.app.fw_version
        fw_txt = f"   ·   bridge fw {fw}" if fw and fw not in ("0.0", "demo") else ""
        self.ver.configure(text=f"Version {__version__}{fw_txt}")

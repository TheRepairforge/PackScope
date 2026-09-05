"""Small reusable UI components, so screens are composition, not copy-paste.

All pure CustomTkinter. Colour "kinds" are semantic keys (green/amber/orange/red/
accent/muted) mapped to the theme, so a badge is styled the same everywhere.
"""

from __future__ import annotations

import customtkinter as ctk

from ..i18n import t
from ..models import Verdict
from . import theme

_VERDICT_KIND = {
    Verdict.HEALTHY: "green", Verdict.REPAIRABLE: "amber",
    Verdict.SUSPECT: "orange", Verdict.REAL_FAULT: "red", Verdict.UNKNOWN: "muted",
}


def verdict_kind(v: Verdict) -> str:
    return _VERDICT_KIND.get(v, "muted")

def _fg(kind: str) -> str:
    # Resolved at CALL time so badges follow the active (light/dark) palette.
    return {"green": theme.GREEN, "amber": theme.AMBER, "orange": theme.ORANGE,
            "red": theme.RED, "accent": theme.ACCENT, "muted": theme.MUTED,
            "text": theme.TEXT}.get(kind, theme.MUTED)


def _bg(kind: str) -> str:
    return {"green": theme.GREEN_BG, "amber": theme.AMBER_BG, "orange": theme.ORANGE_BG,
            "red": theme.RED_BG, "accent": theme.ACCENT_DIM, "muted": theme.PANEL2,
            "text": theme.PANEL2}.get(kind, theme.PANEL2)


def color_of(kind: str) -> str:
    return _fg(kind)


class SectionHeader(ctk.CTkLabel):
    """Small uppercase eyebrow label (instrument feel)."""

    def __init__(self, master, app, text):
        super().__init__(master, text=text.upper(), font=app.f_label,
                         text_color=theme.DIM, anchor="w")


def divider(master, color=None):
    return ctk.CTkFrame(master, height=1, fg_color=color or theme.BORDER)


def vdivider(master, color=None):
    return ctk.CTkFrame(master, width=1, fg_color=color or theme.BORDER)


class StatusBadge(ctk.CTkLabel):
    """A compact rounded pill: tinted background + same-hue text."""

    def __init__(self, master, app, text="", kind="muted"):
        self._app = app
        super().__init__(master, text=text, font=app.f_badge, corner_radius=6,
                         padx=9, pady=3)
        self.set(text, kind)

    def set(self, text, kind="muted"):
        self.configure(text=text, text_color=_fg(kind), fg_color=_bg(kind))


class Metric(ctk.CTkFrame):
    """A labelled value (small muted label above, bold value below) with an
    optional trailing badge (e.g. a grade word)."""

    def __init__(self, master, app, label):
        super().__init__(master, fg_color="transparent")
        self._app = app
        ctk.CTkLabel(self, text=label, font=app.f_small, text_color=theme.MUTED,
                     anchor="w").grid(row=0, column=0, sticky="w")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=1, column=0, sticky="w", pady=(1, 0))
        self.value = ctk.CTkLabel(row, text="—", font=app.f_stat,
                                  text_color=theme.TEXT)
        self.value.pack(side="left")
        self.badge = StatusBadge(row, app, "", "muted")

    def set(self, value, color=None, badge=None, badge_kind="muted"):
        self.value.configure(text=value, text_color=color or theme.TEXT)
        if badge:
            self.badge.set(badge, badge_kind)
            self.badge.pack(side="left", padx=(8, 0))
        else:
            self.badge.pack_forget()


class VerdictStrip(ctk.CTkFrame):
    """A row of small colour cells, one per reading (oldest left) — the pack's
    verdict evolution at a glance."""

    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self._app = app
        self._cells = []

    def set(self, verdicts):
        for c in self._cells:
            c.destroy()
        self._cells = []
        for i, v in enumerate(verdicts[-48:]):
            lab = ctk.CTkLabel(self, text="", width=12, height=18, corner_radius=3,
                               fg_color=theme.verdict_color(v))
            lab.grid(row=0, column=i, padx=1)
            self._cells.append(lab)
        if not verdicts:
            lab = ctk.CTkLabel(self, text=t("DESK_NO_READINGS"), font=self._app.f_small,
                               text_color=theme.DIM)
            lab.grid(row=0, column=0)
            self._cells.append(lab)


class StepIndicator(ctk.CTkFrame):
    """A graphical stepper: done (accent + check) / active (accent + number) /
    future (muted + number), joined by a progress line."""

    def __init__(self, master, app, steps):
        super().__init__(master, fg_color="transparent")
        self._app = app
        self.steps = list(steps)
        self.circles = []
        self.labels = []
        self.lines = []
        n = len(self.steps)
        for c in range(2 * n - 1):
            self.grid_columnconfigure(c, weight=(1 if c % 2 else 0))
        for i, name in enumerate(self.steps):
            circ = ctk.CTkLabel(self, text="", width=26, height=26, corner_radius=13,
                                font=app.f_badge, fg_color=theme.PANEL2,
                                text_color=theme.MUTED)
            circ.grid(row=0, column=2 * i, padx=2)
            lab = ctk.CTkLabel(self, text=name, font=app.f_small, text_color=theme.MUTED)
            lab.grid(row=1, column=2 * i, padx=2, pady=(4, 0))
            self.circles.append(circ)
            self.labels.append(lab)
            if i < n - 1:
                ln = ctk.CTkFrame(self, height=2, fg_color=theme.BORDER)
                ln.grid(row=0, column=2 * i + 1, sticky="ew", padx=4)
                self.lines.append(ln)

    def set_current(self, idx):
        for i, circ in enumerate(self.circles):
            if i < idx:
                circ.configure(fg_color=theme.ACCENT, text_color=theme.ACCENT_INK, text="✓")
                self.labels[i].configure(text_color=theme.MUTED)
            elif i == idx:
                circ.configure(fg_color=theme.ACCENT, text_color=theme.ACCENT_INK,
                               text=str(i + 1))
                self.labels[i].configure(text_color=theme.TEXT)
            else:
                circ.configure(fg_color=theme.PANEL2, text_color=theme.MUTED,
                               text=str(i + 1))
                self.labels[i].configure(text_color=theme.MUTED)
        for j, ln in enumerate(self.lines):
            ln.configure(fg_color=theme.ACCENT if j < idx else theme.BORDER)


class VerdictBanner(ctk.CTkFrame):
    """Compact verdict banner: small dot + coloured label + muted detail."""

    def __init__(self, master, app):
        super().__init__(master, corner_radius=10, fg_color=theme.PANEL2)
        self._app = app
        self.grid_columnconfigure(1, weight=1)
        self.dot = ctk.CTkLabel(self, text="", width=20, height=20, corner_radius=10,
                                fg_color=theme.DIM)
        self.dot.grid(row=0, column=0, rowspan=2, padx=(16, 12), pady=12)
        self.title = ctk.CTkLabel(self, text=t("DESK_NO_READING"), font=app.f_body,
                                  text_color=theme.MUTED, anchor="w")
        self.title.grid(row=0, column=1, sticky="sw", pady=(12, 0))
        self.detail = ctk.CTkLabel(self, text="", font=app.f_small,
                                   text_color=theme.MUTED, anchor="w",
                                   justify="left", wraplength=680)
        self.detail.grid(row=1, column=1, sticky="nw", pady=(0, 12))

    def show(self, verdict, label, detail):
        col = theme.verdict_color(verdict)
        self.configure(fg_color=theme.verdict_bg(verdict))
        self.dot.configure(fg_color=col)
        self.title.configure(text=label, text_color=col)
        self.detail.configure(text=detail, text_color=theme.TEXT)

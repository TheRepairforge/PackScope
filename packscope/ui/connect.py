"""Connect screen: pick a serial port and connect to the PocketOBI bridge,
or start a demo bridge to explore the app without hardware."""

from __future__ import annotations

import time

import customtkinter as ctk

from .. import protocol
from ..bridge import BridgeError, SerialBridge, list_serial_ports
from ..demo import DEMO_PACKS
from ..i18n import t
from . import theme


def _card(master):
    return ctk.CTkFrame(master, fg_color=theme.PANEL, corner_radius=12)


class ConnectFrame(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG, corner_radius=0)
        self.app = app
        self.grid_columnconfigure(0, weight=1)

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.grid(row=0, column=0, sticky="nw", padx=20, pady=18)

        # --- real bridge ---
        card = _card(wrap)
        card.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(card, text=t("DESK_CONN_TITLE"), font=app.f_label,
                     text_color=theme.DIM).grid(row=0, column=0, columnspan=2,
                                                 sticky="w", padx=16, pady=(14, 10))

        ctk.CTkLabel(card, text=t("DESK_CONN_PORT"), font=app.f_small,
                     text_color=theme.MUTED).grid(row=1, column=0, sticky="w",
                                                   padx=16, pady=(0, 2))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=2, column=0, columnspan=2, sticky="w", padx=16)
        self.port = ctk.CTkComboBox(row, width=300, font=app.f_body,
                                    values=list_serial_ports() or [t("DESK_CONN_NO_PORTS")],
                                    fg_color=theme.PANEL2, border_color=theme.BORDER2,
                                    button_color=theme.BORDER2, text_color=theme.TEXT,
                                    dropdown_fg_color=theme.PANEL2,
                                    dropdown_text_color=theme.TEXT)
        self.port.grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(row, text="↻", width=36, font=app.f_body, text_color=theme.TEXT,
                      fg_color=theme.PANEL2, hover_color=theme.RAISED,
                      command=self._refresh).grid(row=0, column=1)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=3, column=0, columnspan=2, sticky="w", padx=16, pady=14)
        self.connect_btn = ctk.CTkButton(
            btns, text=t("DESK_NAV_CONNECT"), font=app.f_body, fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER, text_color=theme.ACCENT_INK,
            command=self._connect)
        self.connect_btn.grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(btns, text=t("DESK_CONN_DISCONNECT"), font=app.f_body, text_color=theme.TEXT,
                      fg_color=theme.PANEL2, hover_color=theme.RAISED,
                      command=self._disconnect).grid(row=0, column=1)

        self.status = ctk.CTkLabel(card, text=t("DESK_CONN_NOT_CONNECTED"), font=app.f_small,
                                   text_color=theme.MUTED, justify="left",
                                   wraplength=440)
        self.status.grid(row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 4))
        ctk.CTkLabel(card, justify="left", font=app.f_small, text_color=theme.DIM,
                     text=t("DESK_CONN_TIP")).grid(
            row=5, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 14))

        # --- demo ---
        demo = _card(wrap)
        demo.grid(row=1, column=0, sticky="w", pady=(14, 0))
        ctk.CTkLabel(demo, text=t("DESK_CONN_DEMO_TITLE"), font=app.f_label,
                     text_color=theme.DIM).grid(row=0, column=0, columnspan=2,
                                                sticky="w", padx=16, pady=(14, 10))
        self.demo_pick = ctk.CTkOptionMenu(
            demo, width=260, font=app.f_body, values=list(DEMO_PACKS.keys()),
            fg_color=theme.PANEL2, button_color=theme.BORDER2, text_color=theme.TEXT,
            dropdown_fg_color=theme.PANEL2, dropdown_text_color=theme.TEXT)
        self.demo_pick.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 14))
        ctk.CTkButton(demo, text=t("DESK_CONN_USE_DEMO"), font=app.f_body, text_color=theme.TEXT,
                      fg_color=theme.PANEL2, hover_color=theme.RAISED,
                      command=self._use_demo).grid(row=1, column=1, padx=8, pady=(0, 14))

    def _refresh(self):
        ports = list_serial_ports() or [t("DESK_CONN_NO_PORTS")]
        self.port.configure(values=ports)
        self.port.set(ports[0])

    def _connect(self):
        port = self.port.get()
        if not port or port.startswith("("):
            self.status.configure(text=t("DESK_CONN_PICK_PORT"), text_color=theme.AMBER)
            return
        self.connect_btn.configure(state="disabled", text=t("DESK_CONN_CONNECTING"))
        self.status.configure(text=t("DESK_CONN_OPENING", port), text_color=theme.MUTED)

        def work():
            # Open without resetting the ESP32, wait for boot, retry the handshake
            # a few times (the device may reboot once on connect).
            bridge = SerialBridge(port, boot_delay=1.2)
            last = None
            for _ in range(6):
                try:
                    ver = protocol.read_version(bridge)
                    # Contract probe: [version, gamme, cell_count]. All-None = legacy
                    # firmware (predates the 0x02 opcode); a v1 firmware reports only
                    # the version. Never raises — a mismatch is a warning, not a
                    # connection failure.
                    contract = protocol.read_contract(bridge)
                    return bridge, ver, contract
                except BridgeError as exc:
                    last = exc
                    time.sleep(0.5)
            try:
                bridge.close()
            except Exception:
                pass
            raise last or BridgeError("no response")

        def done(res):
            bridge, ver, contract = res
            proto = contract.protocol
            # Device-reported family id: routes decoding by what the device says
            # instead of guessing from the model string, once a second gamme's
            # decoder exists. None on a v1 firmware -> fall back to inference.
            self.app.device_gamme = contract.gamme
            self.app.bridge = bridge
            fw = f"{ver[1]}.{ver[2]}"
            # Some firmware builds report 0.0 on the version query — don't surface a
            # meaningless "fw 0.0"; just show a connected bridge.
            shown = "" if fw == "0.0" else fw
            self.app.set_connected(port, shown)
            self.connect_btn.configure(state="normal", text=t("DESK_NAV_CONNECT"))
            msg = t("DESK_CONN_CONNECTED") if not shown else t("DESK_CONN_CONNECTED_FW", shown)
            # Non-blocking compatibility banner: warn (never block) when the
            # firmware's contract version doesn't match the one this Desk mirrors.
            if proto != protocol.EXPECTED_PROTOCOL:
                if proto is None:
                    warn = t("DESK_CONN_WARN_LEGACY")
                else:
                    warn = t("DESK_CONN_WARN_MISMATCH", proto, protocol.EXPECTED_PROTOCOL)
                self.status.configure(text=msg + "\n" + warn, text_color=theme.AMBER)
            else:
                self.status.configure(text=msg, text_color=theme.GREEN)

        def err(exc):
            self.connect_btn.configure(state="normal", text=t("DESK_NAV_CONNECT"))
            msg = str(exc).lower()
            if any(k in msg for k in ("could not open", "access is denied",
                                      "permission", "filenotfound")):
                text = t("DESK_CONN_ERR_OPEN", port)
            else:
                text = t("DESK_CONN_ERR_NORESP")
            self.status.configure(text=text, text_color=theme.RED)

        self.app.run_async(work, done, err)

    def _use_demo(self):
        name = self.demo_pick.get()
        self.app.bridge = DEMO_PACKS[name]()
        self.app.set_connected(f"Demo · {name}", "demo")
        self.status.configure(text=t("DESK_CONN_DEMO_ACTIVE", name), text_color=theme.GREEN)

    def _disconnect(self):
        if self.app.bridge is not None:
            try:
                self.app.bridge.close()
            except Exception:
                pass
        self.app.set_disconnected()
        self.status.configure(text=t("DESK_CONN_DISCONNECTED"), text_color=theme.MUTED)

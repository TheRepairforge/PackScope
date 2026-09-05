# PackScope

Companion PC app for [PocketOBI](https://github.com/TheRepairforge/PocketOBI) — the standalone Makita LXT
battery reader by The Repair Forge. PackScope reads a pack **through a
PocketOBI unit in USB-serial bridge mode**, reuses the firmware's own
decode/verdict logic (ported to Python), and historizes every reading locally
in SQLite.

It replaces Martin Jansson's original PC tool (which no longer decodes the
newer zones PocketOBI reads) and aims for baseline parity with Makita's own
"Battery Checker Management System" — plus PocketOBI's differentiator: a
fault-classification / unlock-viability **verdict** neither of those tools has.

Base protocol work: [Open Battery Information](https://github.com/mnh-jansson/open-battery-information)
by Martin Jansson (MIT).

## Status — v1.0.0 (first public release)

| Module | State |
|---|---|
| `models` / `decode` / `verdict` | ✅ ported 1:1 from firmware |
| `bridge` (serial + fake) / `protocol` | ✅ |
| `db` / `config` | ✅ SQLite export-ready + `%APPDATA%` |
| `csvexport` / `report` | ✅ CSV (Makita-compat + full) + manual JSON export |
| UI (Connect / Live read / History) | ✅ CustomTkinter, device dark+teal look |
| Repair wizard (Read/Classify/Unlock/Confirm) | ✅ gated flow, DB-logged sessions |

104 tests green. Validated on real hardware (BL1860B healthy, BL1850B latched real
fault). Settings/About screens ✅. Multi-platform PyInstaller builds (Windows/Linux/macOS) ship via GitHub Actions on each release tag.

## Run it

Windows: just double-click **`PackScope.bat`** — on first run it creates the
virtual environment and installs the dependencies, then launches the app. Later
runs start it directly.

Manually / other OS:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# .venv/bin/python -m pip install -r requirements.txt      # Linux/Mac
.venv/Scripts/python run.py
```

No PocketOBI unit to hand? On the Connect screen pick a demo pack and click
"Use demo bridge" to explore the whole app offline.

```bash
.venv/Scripts/python -m pytest -q     # run the tests
```

## Layout

```
packscope/
  models.py      Reading dataclass + diagnostic thresholds (mirror of firmware)
  decode.py      pure frame decode (static / live / extended), ported from PocketOBI.ino
  verdict.py     verdict + hardware-fault classification, ported from PocketOBI.ino
  bridge.py      USB-serial <-> firmware (ArduinoOBI binary framing)
  protocol.py    command constants + transactions over the bridge
  db.py          sqlite3 historization (export-ready)
  config.py      app-data paths + settings
  csvexport.py   CSV export (Makita-compat + PocketOBI extras)
  report.py      manual JSON report export (channel B, opt-in anonymize)
  demo.py        canned FakeBridge packs for offline use
  ui/            CustomTkinter screens (app / connect / liveread / history / theme)
tests/           pytest suite (decode, verdict, protocol, db, config, export, demo)
```

## Design notes

- **Decode source of truth is the firmware**, not `makita_lxt.py`: temperature
  is decoded as **1/10 K** (`T_C = raw/10 - 273.15`), and a sensor pinned near
  raw 2430 (≈ -30 °C) is flagged as a faulty thermistor, not a real reading.
- **Verdict is identical to the on-device logic** so a repair decision on the
  PC matches the standalone tool: `HEALTHY` / `REPAIRABLE` (false lock an unlock
  clears) / `REAL_FAULT` (genuine hardware issue, unlock won't hold).
- **No phone-home.** History is local SQLite. Sharing is manual only (a future
  "Export report (JSON)" you paste where you choose). The DB is kept
  export-ready so this stays a small addition.

## License

PackScope is licensed under the **PolyForm Noncommercial License 1.0.0** — free to use,
modify and share for any **noncommercial** purpose. Commercial use requires a separate
license. See [LICENSE](LICENSE). The upstream Open Battery Information project it builds on
remains under the MIT license.

---

```
 ___         _    ___
| _ \__ _ __| |__/ __| __ ___ _ __  ___
|  _/ _` / _| / /\__ \/ _/ _ \ '_ \/ -_)
|_| \__,_\__|_\_\|___/\__\___/ .__/\___|
                             |_|
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
         . Know before you throw .
=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
```

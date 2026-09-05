"""SQLite historization for PackScope.

One row per reading, indexed by serial number (the ROM ID). A battery's history
is just ``WHERE serial_no = ? ORDER BY read_at``. The schema is deliberately
GAMME-AGNOSTIC (DECISIONS D8): the columns are the universal core, and everything
gamme-specific lives in one JSON column, so adding a gamme (Milwaukee, XGT) never
means a schema migration.
  * common core: timestamp, ``gamme``, model, serial, pack/cell voltages,
    temperatures, verdict — universal across every gamme.
  * ``gamme_data_json`` — the single bucket for gamme-specific values: today the
    Makita raw D4/D6 counters and the two fault markers (``fault_marker_58d`` /
    ``fault_marker_309``); Milwaukee counters and XGT registers will join them
    here. The proprietary computed ``over_discharge_pct`` / ``over_load_pct``
    columns are intentionally not stored — we don't fabricate Makita's percentages.
  * ``raw_frame_hex`` is ALWAYS filled (model + live + ROM + message payloads),
    so any row can be re-decoded later if the decode logic improves.

``gamme`` is derived from the model today (:func:`model_family`); once the bridge
contract carries a family id it will be reported by the device.
``wizard_session_id`` is reserved for the phase-2 Repair wizard.

The DB is kept "export-ready" on purpose: a future manual JSON report (never an
automatic phone-home) is just a query away.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .models import Reading, valid_ymd
from .verdict import compute_verdict, temp_implausible, verdict_detail_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_no TEXT NOT NULL,
    model TEXT,
    gamme TEXT,
    command_version TEXT,
    read_at TEXT NOT NULL,
    cycle_count INTEGER,
    pack_voltage_mv INTEGER,
    cell_voltages_mv TEXT,
    temp1_c REAL, temp1_fault INTEGER,
    temp2_c REAL, temp2_fault INTEGER,
    locked INTEGER,
    charger_locked INTEGER,
    error_code INTEGER,
    capacity_ah REAL,
    battery_type INTEGER,
    production_date TEXT,
    assembly_date TEXT,
    gamme_data_json TEXT,
    verdict TEXT,
    verdict_detail TEXT,
    fw_version TEXT,
    user_note TEXT,
    wizard_session_id INTEGER,
    raw_frame_hex TEXT,
    is_demo INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_serial ON readings(serial_no);
CREATE INDEX IF NOT EXISTS idx_read_at ON readings(read_at);
-- idx_gamme is created in _migrate(), AFTER the gamme column is ensured (an
-- existing pre-D8 table has no gamme column yet when this script runs).

CREATE TABLE IF NOT EXISTS repair_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_no TEXT NOT NULL,
    started_at TEXT NOT NULL,
    before_reading_id INTEGER,
    after_reading_id INTEGER,
    verdict_before TEXT,
    override_used INTEGER,
    unlocked_ok INTEGER,          -- lock cleared on the post-unlock re-read
    held INTEGER,                 -- user-confirmed it held after charging (nullable)
    notes TEXT,
    is_demo INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_repair_serial ON repair_sessions(serial_no);

-- One row per physical pack (identity/metadata), keyed by ROM-ID serial.
CREATE TABLE IF NOT EXISTS batteries (
    serial_no TEXT PRIMARY KEY,
    alias TEXT,
    owner TEXT,                   -- "mine" / a customer name / ""
    status TEXT,                  -- to_diagnose / repaired / parts / scrap / ""
    tags TEXT,                    -- JSON array of free tags
    notes TEXT,
    created_at TEXT,
    is_demo INTEGER DEFAULT 0
);
"""

# Columns added after v1 of the schema; ensured on existing DBs by _migrate().
# `gamme` / `gamme_data_json` arrived with the gamme-agnostic refactor (D8).
_MIGRATIONS = {
    "readings": [("is_demo", "INTEGER DEFAULT 0"),
                 ("gamme", "TEXT"),
                 ("gamme_data_json", "TEXT")],
    "repair_sessions": [("is_demo", "INTEGER DEFAULT 0")],
}


def _migrate(conn: sqlite3.Connection) -> None:
    for table, cols in _MIGRATIONS.items():
        existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        for name, decl in cols:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
    # Back-fill `gamme` on rows that predate the column (derived from the model,
    # same rule as at insert). Done in SQL to avoid loading every row.
    conn.execute(
        "UPDATE readings SET gamme = CASE "
        "WHEN upper(model) LIKE 'BL%' THEN 'LXT' ELSE 'OTHER' END "
        "WHERE gamme IS NULL"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gamme ON readings(gamme)")
    conn.commit()


def model_family(model: str) -> str:
    """Coarse family tab classification (ALL/LXT/XGT/CXT/Ni-MH)."""
    if not model:
        return "OTHER"
    m = model.upper()
    if m.startswith("BL"):
        return "LXT"        # Makita 18V LXT packs (what PocketOBI reads today)
    return "OTHER"


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open (creating if needed) the readings DB. ``:memory:`` supported via
    passing ``Path(":memory:")`` — but prefer ``connect_memory()`` for tests."""
    if db_path is None:
        from .config import default_db_path
        db_path = default_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)
    return conn


def connect_memory() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)
    return conn


def _raw_frame_hex(r: Reading) -> str:
    return json.dumps({
        "rom": r.rom_id.hex(),
        "msg": r.msg.hex(),
        "model": r.raw_model.hex(),
        "live": r.raw_live.hex(),
    })


def _gamme_data_json(r: Reading) -> str:
    """The single gamme-specific JSON bucket (D8). Makita today: raw D4/D6
    counters + the two fault markers. Other gammes add their own keys here."""
    return json.dumps({
        "soc_raw": r.soc_raw,
        "od_event_count": r.od_event_count,
        "ol_event_count": r.ol_event_count,
        "od_wear_pct": r.od_wear_pct,
        "ol_wear_pct": r.ol_wear_pct,
        "overload_pct": r.overload_pct,
        "overdischarge_pct": r.overdischarge_pct,
        "health_est_pct": r.health_est_pct,
        "ext_valid": r.ext_valid,
        "fault_marker_58d": r.fault_marker_a,
        "fault_marker_309": r.fault_marker_b,
    })


def insert_reading(conn: sqlite3.Connection, r: Reading, *,
                   fw_version: str = "", user_note: str = "",
                   wizard_session_id: Optional[int] = None,
                   read_at: Optional[str] = None, is_demo: bool = False) -> int:
    """Insert one Reading, computing the verdict at store time. Returns row id."""
    if not r.valid:
        raise ValueError("refusing to store an invalid Reading")

    read_at = read_at or datetime.now().isoformat(timespec="seconds")
    verdict = compute_verdict(r).value
    detail = verdict_detail_text(r)
    gamme = model_family(r.model)   # derived until the bridge reports it

    cells_mv = [int(round(c * 1000)) for c in r.cell]
    t1_fault = 1 if (not r.is_f0513 and temp_implausible(r.temp_cell)) else 0
    # temp_mosfet is only valid on the two-sensor D7 path; a single-sensor read leaves it a
    # sentinel, so gate it on board_temp_valid, not is_f0513 (mirror firmware thermistorFault).
    t2_fault = 1 if (r.board_temp_valid and temp_implausible(r.temp_mosfet)) else 0

    prod_date = r.mfg_date_iso()
    asm_date = None
    if r.ext_valid and r.asm_year:
        asm_y = 2000 + r.asm_year
        asm_date = (f"{asm_y:04d}-{r.asm_month:02d}-{r.asm_day:02d}"
                    if valid_ymd(asm_y, r.asm_month, r.asm_day) else "?")  # not 2255-255-255

    cur = conn.execute(
        """
        INSERT INTO readings (
            serial_no, model, gamme, command_version, read_at, cycle_count,
            pack_voltage_mv, cell_voltages_mv, temp1_c, temp1_fault,
            temp2_c, temp2_fault, locked, charger_locked, error_code,
            capacity_ah, battery_type, production_date, assembly_date,
            gamme_data_json,
            verdict, verdict_detail, fw_version, user_note,
            wizard_session_id, raw_frame_hex, is_demo
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            r.serial_no, r.model, gamme, r.command_version, read_at, r.charge_count,
            int(round(r.pack_voltage * 1000)), json.dumps(cells_mv),
            r.temp_cell, t1_fault, r.temp_mosfet, t2_fault,
            1 if r.locked else 0, 1 if r.charger_locked else 0, r.error_code,
            r.capacity_ah, r.battery_type, prod_date, asm_date,
            _gamme_data_json(r),
            verdict, detail, fw_version, user_note,
            wizard_session_id, _raw_frame_hex(r), 1 if is_demo else 0,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_batteries(conn: sqlite3.Connection, *, family: Optional[str] = None,
                   search: str = "", status: Optional[str] = None,
                   tag: str = "") -> List[sqlite3.Row]:
    """One row per battery (latest reading + its identity metadata), newest first.

    ``family`` filters by model family; ``status`` by workflow status; ``tag`` by a
    free tag; ``search`` matches serial_no / model / alias / note (case-insensitive).
    Each row also carries n_readings and the battery meta (alias/owner/status/tags).
    """
    rows = conn.execute(
        """
        SELECT r.*, g.n AS n_readings,
               b.alias AS alias, b.owner AS owner, b.status AS status, b.tags AS tags
        FROM readings r
        JOIN (
            SELECT serial_no, MAX(read_at) AS mx, COUNT(*) AS n
            FROM readings GROUP BY serial_no
        ) g ON r.serial_no = g.serial_no AND r.read_at = g.mx
        LEFT JOIN batteries b ON b.serial_no = r.serial_no
        ORDER BY r.read_at DESC
        """
    ).fetchall()

    result = []
    s = search.strip().lower()
    for row in rows:
        if family and family != "ALL" and (row["gamme"] or "") != family:
            continue
        if status and (row["status"] or "") != status:
            continue
        if tag:
            try:
                tags = json.loads(row["tags"] or "[]")
            except (json.JSONDecodeError, TypeError):
                tags = []
            if tag not in tags:
                continue
        if s and s not in (row["serial_no"] or "").lower() \
                and s not in (row["model"] or "").lower() \
                and s not in (row["alias"] or "").lower() \
                and s not in (row["owner"] or "").lower() \
                and s not in (row["user_note"] or "").lower():
            continue
        result.append(row)
    return result


def verdict_series(conn: sqlite3.Connection, serial_no: str) -> List[tuple]:
    """(read_at, verdict) oldest first — for the verdict-evolution strip."""
    return [(r["read_at"], r["verdict"]) for r in conn.execute(
        "SELECT read_at, verdict FROM readings WHERE serial_no = ? ORDER BY read_at ASC",
        (serial_no,))]


# ------------------------------------------------------------- battery identity
_BATTERY_FIELDS = ("alias", "owner", "status", "tags", "notes")


def get_battery(conn: sqlite3.Connection, serial_no: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM batteries WHERE serial_no = ?", (serial_no,)).fetchone()


def upsert_battery(conn: sqlite3.Connection, serial_no: str, *,
                   is_demo: bool = False, **fields) -> None:
    """Create or update a battery's identity metadata. ``tags`` may be a list
    (stored as JSON) or a JSON string. Only known fields are written."""
    if "tags" in fields and isinstance(fields["tags"], (list, tuple)):
        fields["tags"] = json.dumps(list(fields["tags"]))
    existing = get_battery(conn, serial_no)
    if existing is None:
        cols = ["serial_no", "created_at", "is_demo"] + [f for f in _BATTERY_FIELDS if f in fields]
        vals = [serial_no, datetime.now().isoformat(timespec="seconds"),
                1 if is_demo else 0] + [fields[f] for f in _BATTERY_FIELDS if f in fields]
        conn.execute(f"INSERT INTO batteries ({','.join(cols)}) "
                     f"VALUES ({','.join('?' * len(cols))})", vals)
    else:
        sets = [f for f in _BATTERY_FIELDS if f in fields]
        if sets:
            conn.execute(f"UPDATE batteries SET {','.join(f + '=?' for f in sets)} "
                         "WHERE serial_no=?", [fields[f] for f in sets] + [serial_no])
    conn.commit()


def battery_tags(row) -> list:
    """Decode a battery row's tags JSON to a list (safe)."""
    try:
        return json.loads(row["tags"] or "[]")
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


def battery_count(conn: sqlite3.Connection, serial_no: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM readings WHERE serial_no = ?", (serial_no,)
    ).fetchone()[0]


def get_history(conn: sqlite3.Connection, serial_no: str) -> List[sqlite3.Row]:
    """All readings for one battery, oldest first (for trend charts)."""
    return conn.execute(
        "SELECT * FROM readings WHERE serial_no = ? ORDER BY read_at ASC",
        (serial_no,),
    ).fetchall()


def get_reading(conn: sqlite3.Connection, reading_id: int) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM readings WHERE id = ?", (reading_id,)
    ).fetchone()


def set_user_note(conn: sqlite3.Connection, reading_id: int, note: str) -> None:
    conn.execute("UPDATE readings SET user_note = ? WHERE id = ?", (note, reading_id))
    conn.commit()


def clear_history(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM readings")
    conn.execute("DELETE FROM repair_sessions")
    conn.execute("DELETE FROM batteries")
    conn.commit()


def clear_demo(conn: sqlite3.Connection) -> None:
    """Remove only the demo dataset (is_demo=1), leaving real data intact."""
    conn.execute("DELETE FROM readings WHERE is_demo = 1")
    conn.execute("DELETE FROM repair_sessions WHERE is_demo = 1")
    conn.execute("DELETE FROM batteries WHERE is_demo = 1")
    conn.commit()


def has_demo(conn: sqlite3.Connection) -> bool:
    return conn.execute(
        "SELECT 1 FROM batteries WHERE is_demo = 1 LIMIT 1").fetchone() is not None


# --------------------------------------------------------------- repair sessions
def create_repair_session(conn: sqlite3.Connection, serial_no: str,
                          before_reading_id: int, verdict_before: str,
                          started_at: Optional[str] = None,
                          is_demo: bool = False) -> int:
    started_at = started_at or datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """INSERT INTO repair_sessions
           (serial_no, started_at, before_reading_id, verdict_before, is_demo)
           VALUES (?,?,?,?,?)""",
        (serial_no, started_at, before_reading_id, verdict_before, 1 if is_demo else 0),
    )
    conn.commit()
    return int(cur.lastrowid)


def finish_repair_session(conn: sqlite3.Connection, session_id: int, *,
                          after_reading_id: Optional[int] = None,
                          override_used: bool = False,
                          unlocked_ok: Optional[bool] = None,
                          held: Optional[bool] = None, notes: str = "") -> None:
    conn.execute(
        """UPDATE repair_sessions SET after_reading_id=?, override_used=?,
           unlocked_ok=?, held=?, notes=? WHERE id=?""",
        (after_reading_id, 1 if override_used else 0,
         None if unlocked_ok is None else (1 if unlocked_ok else 0),
         None if held is None else (1 if held else 0), notes, session_id),
    )
    conn.commit()


def get_repair_sessions(conn: sqlite3.Connection,
                        serial_no: Optional[str] = None) -> List[sqlite3.Row]:
    if serial_no:
        return conn.execute(
            "SELECT * FROM repair_sessions WHERE serial_no=? ORDER BY started_at DESC",
            (serial_no,)).fetchall()
    return conn.execute(
        "SELECT * FROM repair_sessions ORDER BY started_at DESC").fetchall()

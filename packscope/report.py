"""Manual report export (channel B) — the ONLY sharing mechanism.

There is no phone-home. This module just serializes selected readings to a JSON
file the user can choose to paste into a form or a GitHub issue. It keeps
``raw_frame_hex`` so a shared reading can be re-decoded later to improve the
decode/verdict logic — the whole point of collecting them.

Anonymization is OPT-IN and off by default: because the export is manual, the
user already controls what leaves the machine. When enabled, the real serial is
replaced by ``sha256(serial + seed)[:16]`` (a stable per-user pseudonym), and
the seed itself is never included.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

REPORT_VERSION = 1


def _pseudonym(serial: str, seed: str) -> str:
    return hashlib.sha256((serial + seed).encode("utf-8")).hexdigest()[:16]


def _row_to_dict(row: sqlite3.Row, *, anonymize: bool, seed: str) -> dict:
    d = {k: row[k] for k in row.keys()}
    d.pop("id", None)
    if anonymize:
        d["serial_no"] = _pseudonym(row["serial_no"] or "", seed)
    return d


def build_report(rows: Sequence[sqlite3.Row], *, anonymize: bool = False,
                 seed: str = "", generated_at: Optional[str] = None) -> dict:
    """Build the report payload (a dict with metadata + a list of readings)."""
    if anonymize and not seed:
        raise ValueError("anonymize=True requires a seed")
    return {
        "report_version": REPORT_VERSION,
        "generated_at": generated_at or datetime.now().isoformat(timespec="seconds"),
        "anonymized": anonymize,
        "count": len(rows),
        "readings": [_row_to_dict(r, anonymize=anonymize, seed=seed) for r in rows],
    }


def _fetch(conn: sqlite3.Connection,
           rows: Optional[Sequence[sqlite3.Row]]) -> List[sqlite3.Row]:
    if rows is not None:
        return list(rows)
    return conn.execute("SELECT * FROM readings ORDER BY read_at ASC").fetchall()


def export_report_json(conn: sqlite3.Connection, path, *,
                       rows: Optional[Sequence[sqlite3.Row]] = None,
                       anonymize: bool = False, seed: str = "") -> int:
    """Write a report JSON to ``path``. Returns the number of readings written."""
    data = _fetch(conn, rows)
    payload = build_report(data, anonymize=anonymize, seed=seed)
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return len(data)

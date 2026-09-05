"""CSV export.

Two column sets:
  * "makita" — baseline parity with Makita's Battery Checker CSV columns. The
    proprietary COMPUTED fields Makita has and we deliberately don't fabricate
    (Life/SOH, Over Discharge %, Over Load %, the Abnormal flags) are emitted as
    empty columns, so the file lines up with theirs without inventing values.
  * "full"   — the makita columns plus PocketOBI's own added value (verdict +
    reason, charger-lock, raw counters, fault markers, temps + fault flags).
"""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Sequence

MAKITA_COLUMNS = [
    "User", "Dealer", "Date", "Model", "Serial No.", "Cycle",
    "Capacity (Ah)", "Pack V (mV)", "Life", "Over Discharge (%)",
    "Over Load (%)", "Battery Abnormal", "Cell Abnormal", "Circuit Abnormal",
] + [f"Cell V{i} (mV)" for i in range(1, 11)] + [
    "Remarks", "Battery Temperature (C)",
]

FULL_EXTRA_COLUMNS = [
    "Command Version", "Verdict", "Verdict Detail", "Locked", "Charger Locked",
    "Error Code", "Temp1 (C)", "Temp1 Fault", "Temp2 (C)", "Temp2 Fault",
    "SOC raw", "OverDischarge events", "OverLoad events",
    "Fault Marker 58D", "Fault Marker 309", "Production Date", "Assembly Date",
    "FW Version", "Read At",
]


def _cells(row: sqlite3.Row) -> List[int]:
    try:
        cells = json.loads(row["cell_voltages_mv"] or "[]")
    except (json.JSONDecodeError, TypeError):
        cells = []
    cells = list(cells)[:10]
    return cells + [""] * (10 - len(cells))


def _makita_row(row: sqlite3.Row) -> list:
    return [
        "",                              # User (free field, not captured yet)
        "",                              # Dealer
        row["production_date"] or "",    # Date (production)
        row["model"] or "",
        row["serial_no"] or "",
        row["cycle_count"] if row["cycle_count"] is not None else "",
        row["capacity_ah"] if row["capacity_ah"] is not None else "",
        row["pack_voltage_mv"] if row["pack_voltage_mv"] is not None else "",
        "",                              # Life / SOH (Makita computed — not faked)
        "",                              # Over Discharge % (computed — not faked)
        "",                              # Over Load % (computed — not faked)
        "",                              # Battery Abnormal (computed — not faked)
        "",                              # Cell Abnormal
        "",                              # Circuit Abnormal
        *_cells(row),
        row["user_note"] or "",          # Remarks
        row["temp1_c"] if row["temp1_c"] is not None else "",
    ]


def _full_extra(row: sqlite3.Row) -> list:
    try:
        rc = json.loads(row["gamme_data_json"] or "{}")
    except (json.JSONDecodeError, TypeError):
        rc = {}
    return [
        row["command_version"] or "",
        row["verdict"] or "",
        row["verdict_detail"] or "",
        row["locked"], row["charger_locked"],
        row["error_code"],
        row["temp1_c"], row["temp1_fault"],
        row["temp2_c"], row["temp2_fault"],
        rc.get("soc_raw", ""), rc.get("od_event_count", ""),
        rc.get("ol_event_count", ""),
        rc.get("fault_marker_58d", ""), rc.get("fault_marker_309", ""),
        row["production_date"] or "", row["assembly_date"] or "",
        row["fw_version"] or "", row["read_at"] or "",
    ]


def _fetch(conn: sqlite3.Connection,
           rows: Optional[Sequence[sqlite3.Row]]) -> Sequence[sqlite3.Row]:
    if rows is not None:
        return rows
    return conn.execute("SELECT * FROM readings ORDER BY read_at ASC").fetchall()


def export_csv(conn: sqlite3.Connection, path, *, column_set: str = "full",
               rows: Optional[Sequence[sqlite3.Row]] = None) -> int:
    """Write readings to ``path`` as CSV. Returns the number of rows written."""
    data = _fetch(conn, rows)
    full = column_set == "full"
    header = MAKITA_COLUMNS + (FULL_EXTRA_COLUMNS if full else [])

    # utf-8-sig (BOM) so Excel — notably on non-English Windows — reads accents
    # correctly. The column HEADERS stay English (stable for external parsers).
    with open(Path(path), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in data:
            line = _makita_row(row)
            if full:
                line += _full_extra(row)
            w.writerow(line)
    return len(data)

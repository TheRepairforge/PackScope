"""CSV + JSON report export tests."""

import csv
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packscope import csvexport, db, protocol, report
from tests.test_db import healthy_bridge


def _seed(conn):
    db.insert_reading(conn, protocol.read_all(healthy_bridge()),
                      fw_version="0.9.6", user_note="pack A")


def test_csv_makita_columns(tmp_path):
    conn = db.connect_memory()
    _seed(conn)
    path = tmp_path / "out.csv"
    n = csvexport.export_csv(conn, path, column_set="makita")
    assert n == 1

    with open(path, newline="", encoding="utf-8-sig") as f:   # BOM for Excel
        rows = list(csv.reader(f))
    assert rows[0] == csvexport.MAKITA_COLUMNS
    header = rows[0]
    rec = dict(zip(header, rows[1]))
    assert rec["Model"] == "BL1860B"
    assert rec["Serial No."] == "1807050214BC4E37"
    assert rec["Pack V (mV)"] == "20457"
    assert rec["Cell V1 (mV)"] == "4096"
    assert rec["Life"] == ""                      # proprietary computed -> blank


def test_csv_full_has_verdict(tmp_path):
    conn = db.connect_memory()
    _seed(conn)
    path = tmp_path / "full.csv"
    csvexport.export_csv(conn, path, column_set="full")
    with open(path, newline="", encoding="utf-8-sig") as f:   # BOM for Excel
        rows = list(csv.reader(f))
    header = rows[0]
    assert "Verdict" in header
    rec = dict(zip(header, rows[1]))
    assert rec["Verdict"] == "HEALTHY"


def test_report_json_plain(tmp_path):
    conn = db.connect_memory()
    _seed(conn)
    path = tmp_path / "report.json"
    n = report.export_report_json(conn, path)
    assert n == 1
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["count"] == 1
    assert payload["anonymized"] is False
    reading = payload["readings"][0]
    assert reading["serial_no"] == "1807050214BC4E37"
    assert "raw_frame_hex" in reading         # kept for future re-decode
    assert "id" not in reading


def test_report_json_anonymized(tmp_path):
    conn = db.connect_memory()
    _seed(conn)
    path = tmp_path / "anon.json"
    report.export_report_json(conn, path, anonymize=True, seed="my-seed")
    payload = json.loads(path.read_text(encoding="utf-8"))
    reading = payload["readings"][0]
    assert reading["serial_no"] != "1807050214BC4E37"
    assert len(reading["serial_no"]) == 16
    assert payload["anonymized"] is True


def test_report_anonymize_requires_seed():
    with pytest.raises(ValueError):
        report.build_report([], anonymize=True, seed="")

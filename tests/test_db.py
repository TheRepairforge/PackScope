"""DB tests: insert / history / list / re-decodable raw frame."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packscope import db, decode, protocol
from packscope.bridge import FakeBridge
from packscope.models import Reading, Verdict


def healthy_bridge(model=b"BL1860B", serial="1807050214BC4E37"):
    b = FakeBridge()
    b.add(protocol.MODEL_CMD, model + b"\x00" * (16 - len(model)))
    live = bytearray(29)
    live[0:2] = bytes([0xE9, 0x4F])                 # 20457 mV
    for i in range(5):
        live[2 + 2 * i:4 + 2 * i] = bytes([0x00, 0x10])  # 4096 mV
    live[14:16] = bytes([0xED, 0x0B])               # 3053
    live[16:18] = bytes([0xF5, 0x0B])               # 3061
    b.add(protocol.READ_DATA_CMD, bytes(live))
    b.add(protocol.READ_MSG_CMD, bytes.fromhex(serial) + bytes(32))
    return b


def test_insert_and_get():
    conn = db.connect_memory()
    r = protocol.read_all(healthy_bridge())
    rid = db.insert_reading(conn, r, fw_version="0.9.6", user_note="bench pack")

    row = db.get_reading(conn, rid)
    assert row["serial_no"] == "1807050214BC4E37"
    assert row["model"] == "BL1860B"
    assert row["verdict"] == Verdict.HEALTHY.value
    assert row["pack_voltage_mv"] == 20457
    assert json.loads(row["cell_voltages_mv"]) == [4096] * 5
    assert row["fw_version"] == "0.9.6"
    assert row["user_note"] == "bench pack"
    assert row["production_date"] == "2024-07-05"
    # Gamme-agnostic schema (D8): family is a core column, gamme-specific values
    # (incl. the fault markers) live in the one JSON bucket.
    assert row["gamme"] == "LXT"
    gd = json.loads(row["gamme_data_json"])
    assert "fault_marker_58d" in gd and "fault_marker_309" in gd
    assert "soc_raw" in gd


def test_raw_frame_is_redecodable():
    conn = db.connect_memory()
    r = protocol.read_all(healthy_bridge())
    rid = db.insert_reading(conn, r)
    row = db.get_reading(conn, rid)

    raw = json.loads(row["raw_frame_hex"])
    # Re-decode the live payload straight from the stored hex.
    r2 = Reading()
    decode.apply_live_standard(r2, bytes.fromhex(raw["live"]))
    assert r2.pack_voltage == pytest.approx(20.457, abs=1e-3)
    assert bytes.fromhex(raw["rom"]).hex().upper() == "1807050214BC4E37"


def test_history_and_list():
    conn = db.connect_memory()
    r = protocol.read_all(healthy_bridge())
    db.insert_reading(conn, r, read_at="2026-08-01T10:00:00")
    db.insert_reading(conn, r, read_at="2026-08-05T10:00:00")

    hist = db.get_history(conn, "1807050214BC4E37")
    assert len(hist) == 2
    assert hist[0]["read_at"] < hist[1]["read_at"]          # oldest first
    assert db.battery_count(conn, "1807050214BC4E37") == 2

    batteries = db.list_batteries(conn)
    assert len(batteries) == 1                              # one battery, latest row
    assert batteries[0]["read_at"] == "2026-08-05T10:00:00"


def test_list_family_and_search():
    conn = db.connect_memory()
    db.insert_reading(conn, protocol.read_all(healthy_bridge()))
    db.insert_reading(
        conn,
        protocol.read_all(healthy_bridge(model=b"BL1850B", serial="1809150211AA0102")),
        user_note="locked one",
    )

    assert len(db.list_batteries(conn, family="LXT")) == 2
    assert len(db.list_batteries(conn, family="OTHER")) == 0
    assert len(db.list_batteries(conn, search="1850")) == 1
    assert len(db.list_batteries(conn, search="locked")) == 1


def test_clear_and_invalid():
    conn = db.connect_memory()
    db.insert_reading(conn, protocol.read_all(healthy_bridge()))
    db.clear_history(conn)
    assert db.list_batteries(conn) == []

    with pytest.raises(ValueError):
        db.insert_reading(conn, Reading())          # invalid -> refused

"""Pack-identity metadata, demo seeder, verdict series, filters, demo isolation."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packscope import db as dbmod, demo_history, protocol
from packscope.demo import healthy


def test_seed_creates_batteries_and_is_idempotent():
    conn = dbmod.connect_memory()
    assert demo_history.seed(conn) == 5
    assert demo_history.seed(conn) == 0          # already seeded -> no duplicates
    assert dbmod.has_demo(conn) is True
    assert len(dbmod.list_batteries(conn)) == 5


def test_battery_metadata_surfaces_in_list():
    conn = dbmod.connect_memory()
    demo_history.seed(conn)
    rows = {r["serial_no"]: r for r in dbmod.list_batteries(conn)}
    a = rows["1807050214BC4E37"]
    assert a["alias"] == "Shop drill 18V"
    assert a["owner"] == "mine"
    assert a["status"] == "repaired"
    assert a["n_readings"] == 3


def test_filters_status_and_tag():
    conn = dbmod.connect_memory()
    demo_history.seed(conn)
    assert len(dbmod.list_batteries(conn, status="repaired")) == 2
    assert len(dbmod.list_batteries(conn, tag="thermistor")) == 1
    assert len(dbmod.list_batteries(conn, search="martin")) == 1   # owner match...
    assert len(dbmod.list_batteries(conn, search="watch")) == 1    # alias match


def test_verdict_series_shows_degradation():
    conn = dbmod.connect_memory()
    demo_history.seed(conn)
    series = [v for _, v in dbmod.verdict_series(conn, "1601140311225788")]
    assert series == ["HEALTHY", "HEALTHY", "SUSPECT", "REAL_FAULT"]


def test_repair_session_ground_truth():
    conn = dbmod.connect_memory()
    demo_history.seed(conn)
    held = {s["serial_no"]: s["held"] for s in dbmod.get_repair_sessions(conn)}
    assert held["1809150211AA0102"] == 0     # re-locked
    assert held["1703110207C41D33"] == 1     # held


def test_upsert_battery_roundtrip():
    conn = dbmod.connect_memory()
    dbmod.insert_reading(conn, protocol.read_all(healthy()))
    dbmod.upsert_battery(conn, "1807050214BC4E37", alias="My pack", tags=["x", "y"])
    b = dbmod.get_battery(conn, "1807050214BC4E37")
    assert b["alias"] == "My pack"
    assert dbmod.battery_tags(b) == ["x", "y"]
    dbmod.upsert_battery(conn, "1807050214BC4E37", status="scrap")   # update keeps alias
    b = dbmod.get_battery(conn, "1807050214BC4E37")
    assert b["alias"] == "My pack" and b["status"] == "scrap"


def test_clear_demo_leaves_real_data():
    conn = dbmod.connect_memory()
    demo_history.seed(conn)
    real_id = dbmod.insert_reading(conn, protocol.read_all(healthy()))  # real (is_demo=0)
    dbmod.clear_demo(conn)
    assert dbmod.has_demo(conn) is False
    assert dbmod.get_reading(conn, real_id) is not None      # real reading survived

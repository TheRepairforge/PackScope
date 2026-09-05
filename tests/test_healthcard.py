"""Health-card HTML generation."""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packscope import db as dbmod, demo_history, healthcard


def test_build_html_contains_key_facts():
    conn = dbmod.connect_memory()
    demo_history.seed(conn)
    html = healthcard.build_html(conn, "1601140311225788", generated_at="2026-08-10T10:00")
    assert "Battery Health Report" in html
    assert "1601140311225788" in html          # S/N
    assert "BL1850B" in html                    # model
    assert "HARDWARE FIX" in html               # latest verdict label (degraded pack)
    assert "Verdict over time" in html
    assert "<!doctype html>" in html.lower()


def test_build_html_unknown_serial_raises():
    conn = dbmod.connect_memory()
    with pytest.raises(ValueError):
        healthcard.build_html(conn, "DEADBEEF")


def test_export_writes_file(tmp_path):
    conn = dbmod.connect_memory()
    demo_history.seed(conn)
    p = healthcard.export_health_card(conn, "1807050214BC4E37", tmp_path / "card.html")
    assert p.exists() and p.read_text(encoding="utf-8").startswith("<!doctype")

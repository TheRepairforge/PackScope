"""Demo bridges produce the intended verdicts (regression for the offline demo)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packscope import demo, protocol
from packscope.models import Verdict
from packscope.verdict import compute_verdict


def _verdict(bridge):
    return compute_verdict(protocol.read_all(bridge))


def test_demo_healthy():
    assert _verdict(demo.healthy()) == Verdict.HEALTHY


def test_demo_false_lock_repairable():
    r = protocol.read_all(demo.false_lock())
    assert r.charger_locked is True
    assert compute_verdict(r) == Verdict.REPAIRABLE


def test_demo_thermistor_real_fault():
    assert _verdict(demo.thermistor()) == Verdict.REAL_FAULT


def test_demo_locked_repairable():
    # D24: the BL1850B demo is a genuinely charger-locked pack. Its D6 markers are kept
    # raw (never latched), and the lock drives the verdict -> REPAIRABLE.
    r = protocol.read_all(demo.latched(), extended=True)
    assert r.latched_fault is False
    assert r.locked is True
    assert compute_verdict(r) == Verdict.REPAIRABLE


def test_all_demo_packs_read():
    for name, factory in demo.DEMO_PACKS.items():
        r = protocol.read_all(factory())
        assert r.valid, name

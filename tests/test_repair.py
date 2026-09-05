"""Repair: frame-repair safety, unlock command sequence, repair_sessions DB."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packscope import db as dbmod
from packscope import decode, demo, protocol
from packscope.models import Reading


def test_build_repaired_frame_clears_lock_keeps_failure_code():
    m = bytearray(32)
    decode.nyb_set(m, 40, 0xF)     # failure code = dead
    decode.nyb_set(m, 34, 0x1)     # charger lock set
    out = decode.build_repaired_frame(m)

    assert decode.nyb_get(out, 34) == 0        # lock cleared
    assert decode.nyb_get(out, 40) == 0xF      # failure code NEVER touched
    assert decode.lock_causes(out) == 0        # frame is self-consistent -> unlocked


def test_frame_diff_flags_changed_nybbles():
    a = bytearray(32)
    b = bytearray(32)
    decode.nyb_set(b, 34, 1)      # charger-lock nybble changed
    decode.nyb_set(b, 20, 5)      # some other byte
    diffs = {d[0]: d for d in decode.frame_diff(a, b)}
    assert 34 in diffs and diffs[34][4] == "charger lock (N34)"
    assert diffs[34][2] == 0 and diffs[34][3] == 1
    assert 20 in diffs


def test_build_repaired_frame_unlocks_a_locked_pack():
    # A demo false-locked frame -> after repair, no lock causes remain.
    before = protocol.read_all(demo.false_lock(), extended=False)
    assert decode.lock_causes(before.msg) != 0
    repaired = decode.build_repaired_frame(before.msg)
    assert decode.lock_causes(repaired) == 0


def test_unlock_issues_the_repair_sequence():
    b = demo.false_lock()
    before = protocol.read_all(b, extended=False)
    b.sent.clear()
    after = protocol.unlock(b)

    assert protocol.ARM_CMD in b.sent
    assert protocol.STORE_CMD in b.sent
    assert protocol.TESTMODE_CMD in b.sent
    assert protocol.RESET_ERROR_CMD in b.sent
    repaired = decode.build_repaired_frame(before.msg)
    assert protocol._frame_write_cmd(repaired) in b.sent
    assert isinstance(after, Reading)


def test_repair_session_roundtrip():
    conn = dbmod.connect_memory()
    before = protocol.read_all(demo.false_lock())
    bid = dbmod.insert_reading(conn, before)
    sid = dbmod.create_repair_session(conn, before.serial_no, bid, "REPAIRABLE")

    after = protocol.read_all(demo.healthy())
    aid = dbmod.insert_reading(conn, after, wizard_session_id=sid)
    dbmod.finish_repair_session(conn, sid, after_reading_id=aid,
                                override_used=False, unlocked_ok=True,
                                held=True, notes="held after charge")

    rows = dbmod.get_repair_sessions(conn)
    assert len(rows) == 1
    s = rows[0]
    assert s["before_reading_id"] == bid
    assert s["after_reading_id"] == aid
    assert s["unlocked_ok"] == 1
    assert s["held"] == 1
    assert s["verdict_before"] == "REPAIRABLE"

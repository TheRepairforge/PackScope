"""Demo HISTORY dataset — populate the DB with realistic packs so the Batteries
screen can be explored/demoed/filmed without real hardware. Everything is tagged
is_demo=1 so db.clear_demo() removes it cleanly, leaving real data intact.

Includes: a healthy daily pack, a latched pack that RE-LOCKED after unlock, a
thermistor-fault pack, a false-lock pack whose unlock HELD, and a pack that
DEGRADES over time (HEALTHY -> HEALTHY -> SUSPECT -> REAL_FAULT) to show the
verdict-evolution strip and trends.
"""

from __future__ import annotations

from . import db as dbmod, decode
from .models import Reading


def _frame(nyb34=0):
    """A minimal 32-byte static frame with the charger-lock nybble set/clear
    (enough for the Compare frame-diff demo)."""
    m = bytearray(32)
    decode.nyb_set(m, 34, nyb34)
    return bytes(m)


def _reading(serial, model, cells, t_cell, t_board, capacity, cycles,
             locked=False, charger_locked=False, latched=False, frame=None) -> Reading:
    r = Reading(valid=True)
    r.model = model
    r.rom_id = bytes.fromhex(serial)
    r.cell = list(cells)
    r.cell_diff = max(cells) - min(cells)
    r.pack_voltage = round(sum(cells), 3)
    r.temp_cell = t_cell
    r.temp_mosfet = t_board
    r.board_temp_valid = True   # demo readings are two-sensor D7 reads
    r.capacity_ah = capacity
    r.charge_count = cycles
    r.locked = locked
    r.charger_locked = charger_locked
    r.latched_fault = latched
    if frame is not None:
        r.msg = bytes(frame)
    return r


def _ins(conn, r, read_at):
    return dbmod.insert_reading(conn, r, fw_version="demo", read_at=read_at, is_demo=True)


def seed(conn) -> int:
    """Insert the demo dataset. Returns the number of batteries created."""
    if dbmod.has_demo(conn):
        return 0

    # 1) Healthy daily pack ---------------------------------------------------
    A = "1807050214BC4E37"
    dbmod.upsert_battery(conn, A, alias="Shop drill 18V", owner="mine",
                         status="repaired", tags=["daily"], is_demo=True)
    for d, t in (("2026-06-01T09:12:00", 28), ("2026-07-03T14:20:00", 31),
                 ("2026-08-05T10:05:00", 30)):
        _ins(conn, _reading(A, "BL1860B", [4.10, 4.10, 4.09, 4.10, 4.10], t, t + 1,
                            6.0, 40), d)

    # 2) Latched pack that RE-LOCKED after unlock -----------------------------
    B = "1809150211AA0102"
    dbmod.upsert_battery(conn, B, alias="", owner="Client Dupont",
                         status="scrap", tags=["re-lock"], is_demo=True)
    b_before = _ins(conn, _reading(B, "BL1850B", [3.72] * 5, 26, 27, 5.0, 83,
                                   locked=True, latched=True, frame=_frame(nyb34=1)),
                    "2026-07-20T11:00:00")
    b_after = _ins(conn, _reading(B, "BL1850B", [3.72] * 5, 26, 27, 5.0, 83,
                                  latched=True, frame=_frame(nyb34=0)),
                   "2026-07-20T11:04:00")
    sid = dbmod.create_repair_session(conn, B, b_before, "SUSPECT",
                                      started_at="2026-07-20T11:02:00", is_demo=True)
    dbmod.finish_repair_session(conn, sid, after_reading_id=b_after,
                                override_used=True, unlocked_ok=True, held=False,
                                notes="Re-locked ~10 s into charge.")

    # 3) Thermistor fault -----------------------------------------------------
    C = "1506120214AA5501"
    dbmod.upsert_battery(conn, C, alias="Deep-discharge rescue", owner="mine",
                         status="parts", tags=["thermistor"], is_demo=True)
    _ins(conn, _reading(C, "BL1830B", [3.13] * 5, -30, 35, 3.0, 214),
         "2026-07-28T16:40:00")

    # 4) False lock whose unlock HELD -----------------------------------------
    D = "1703110207C41D33"
    dbmod.upsert_battery(conn, D, alias="", owner="Client Martin",
                         status="repaired", tags=["false-lock"], is_demo=True)
    d_before = _ins(conn, _reading(D, "BL1840B", [3.80] * 5, 25, 26, 4.0, 120,
                                   charger_locked=True), "2026-08-01T09:30:00")
    d_after = _ins(conn, _reading(D, "BL1840B", [3.82] * 5, 25, 26, 4.0, 120),
                   "2026-08-01T09:35:00")
    sid = dbmod.create_repair_session(conn, D, d_before, "REPAIRABLE",
                                      started_at="2026-08-01T09:33:00", is_demo=True)
    dbmod.finish_repair_session(conn, sid, after_reading_id=d_after,
                                override_used=False, unlocked_ok=True, held=True,
                                notes="False over-discharge lockout; held after charge.")

    # 5) Degrading pack: HEALTHY -> HEALTHY -> SUSPECT -> REAL_FAULT -----------
    E = "1601140311225788"
    dbmod.upsert_battery(conn, E, alias="Pack under watch", owner="mine",
                         status="to_diagnose", tags=["watch"], is_demo=True)
    _ins(conn, _reading(E, "BL1850B", [4.10] * 5, 29, 30, 5.0, 210), "2026-05-10T10:00:00")
    _ins(conn, _reading(E, "BL1850B", [4.00, 4.00, 3.98, 4.01, 4.00], 30, 34, 5.0, 260),
         "2026-06-18T10:00:00")
    _ins(conn, _reading(E, "BL1850B", [3.95] * 5, 25, 55, 5.0, 300), "2026-07-22T10:00:00")
    _ins(conn, _reading(E, "BL1850B", [3.9, 3.9, 2.3, 3.9, 3.9], 28, 30, 5.0, 340),
         "2026-08-06T10:00:00")

    return 5

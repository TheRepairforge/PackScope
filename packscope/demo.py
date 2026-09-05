"""Demo bridges — canned FakeBridge packs so the app runs with no hardware.

Lets the UI be explored, screenshotted and demoed offline. The four packs match
the states in the UI mockup: healthy, false-lock (repairable), thermistor fault
and latched fault.
"""

from __future__ import annotations

from . import decode, protocol
from .bridge import FakeBridge


def _le(v: int) -> bytes:
    return bytes([v & 0xFF, (v >> 8) & 0xFF])


def _set_nyb(d: bytearray, n: int, v: int) -> None:
    v &= 0x0F
    if n & 1:
        d[n >> 1] = (d[n >> 1] & 0x0F) | (v << 4)
    else:
        d[n >> 1] = (d[n >> 1] & 0xF0) | v


def _seal(m: bytearray) -> None:
    """Recompute the three primary checksums so a demo frame is self-consistent
    (otherwise lock_causes() would flag a false charger lock)."""
    _set_nyb(m, 41, decode.cs_calc(m, 0, 15))
    _set_nyb(m, 42, decode.cs_calc(m, 16, 31))
    _set_nyb(m, 43, decode.cs_calc(m, 32, 40))


def _live(pack_mv: int, cells_mv, t1_raw: int, t2_raw: int) -> bytes:
    p = bytearray(29)
    p[0:2] = _le(pack_mv)
    for i in range(5):
        p[2 + 2 * i:4 + 2 * i] = _le(cells_mv[i])
    p[14:16] = _le(t1_raw)
    p[16:18] = _le(t2_raw)
    return bytes(p)


def _msg(rom_hex: str, cap_byte: int = 0x00, lock_nib: int = 0,
         nyb34: int = 0, charge_lsb: int = 0x82) -> bytes:
    rom = bytes.fromhex(rom_hex)
    m = bytearray(32)
    m[16] = cap_byte
    m[20] = lock_nib & 0x0F
    m[17] = (m[17] & 0xF0) | (nyb34 & 0x0F)   # nybble 34 = charger lock
    m[27] = charge_lsb                          # charge count low byte
    _seal(m)                                    # consistent checksums (CS0/CS1/CS2)
    return rom + bytes(m)


def _base(model: bytes, live: bytes, msg: bytes) -> FakeBridge:
    b = FakeBridge()
    b.add(protocol.MODEL_CMD, model + b"\x00" * (16 - len(model)))
    b.add(protocol.READ_DATA_CMD, live)
    b.add(protocol.READ_MSG_CMD, msg)
    b.add(protocol.VERSION_CMD, bytes([0x00, 0x09, 0x06]))
    return b


def healthy() -> FakeBridge:
    return _base(b"BL1860B",
                 _live(20457, [4096, 4096, 4090, 4096, 4096], 3053, 3061),
                 _msg("1807050214BC4E37", cap_byte=0xC3, charge_lsb=0x04))


def false_lock() -> FakeBridge:
    # Healthy cells/temps, charger lock set, no latched marker -> REPAIRABLE.
    return _base(b"BL1840B",
                 _live(19020, [3800, 3800, 3790, 3810, 3800], 2985, 2995),
                 _msg("2205110207C41D33", cap_byte=0x14, nyb34=1))


def thermistor() -> FakeBridge:
    # One sensor pinned at raw 2430 (-30 C) -> hardware/thermistor REAL_FAULT.
    return _base(b"BL1830B",
                 _live(15680, [3130, 3130, 3120, 3130, 3130], 2430, 3085),
                 _msg("2112060214AA5501", cap_byte=0xE1, charge_lsb=0x82))


def latched() -> FakeBridge:
    # Balanced/normal but latched marker set (D6) -> REAL_FAULT, unlock won't hold.
    b = _base(b"BL1850B",
              _live(18570, [3720, 3720, 3720, 3710, 3720], 2992, 3002),
              _msg("1809150211AA0102", cap_byte=0x23, lock_nib=3))
    b.add(protocol._d6_read_byte(0x58D), bytes([0x0B, 0x06]))
    b.add(protocol._d6_read_byte(0x309), bytes([0x48, 0x06]))
    # Extended D4 reads a real latched pack answers (the block is trusted only when the
    # over-discharge count is not 0xFF — see _read_extended): assembly 2018-09-15,
    # a couple of over-discharge events, no over-load.
    b.add(protocol._d4_read(0x000, 1), bytes([0x12, 0x06]))         # asm year 18
    b.add(protocol._d4_read(0x001, 1), bytes([0x09, 0x06]))         # asm month
    b.add(protocol._d4_read(0x002, 1), bytes([0x0F, 0x06]))         # asm day 15
    b.add(protocol._d4_read(0x150, 2), bytes([0x52, 0x11, 0x06]))   # SOC raw 4434
    b.add(protocol._d4_read(0x0BA, 1), bytes([0x02, 0x06]))         # 2 over-discharge events
    b.add(protocol._d4_read(0x08D, 7), bytes([0, 0, 0, 0, 0, 0, 0, 0x06]))  # 0 over-load
    return b


DEMO_PACKS = {
    "Healthy (BL1860B)": healthy,
    "False lock (BL1840B)": false_lock,
    "Thermistor (BL1830B)": thermistor,
    "Latched (BL1850B)": latched,
}

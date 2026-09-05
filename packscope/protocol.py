"""Makita LXT protocol transactions over a PocketOBI bridge.

Command bytes are taken verbatim from PocketOBI.ino (which took them from
makita_lxt.py). Each command is the ArduinoOBI frame
``[0x01, len, rsp_len, cmd, data...]``; the bridge returns ``rsp_len`` payload
bytes, which we hand to ``decode``.

Read ordering (from the hardware findings):
  1. MODEL  (0xCC) — detects standard vs older F0513, does NOT lock out live.
  2. LIVE   (0xCC) — MUST be read before the 0x33 static message: the pack
     stops answering live data once the 0x33 message read has run.
  3. MESSAGE(0x33) — ROM ID + 32-byte static frame.
  4. EXTENDED (D4/D6) — best-effort; needs TESTMODE first (see caveat below).
"""

from __future__ import annotations

from typing import NamedTuple, Optional, Tuple

from . import decode
from .bridge import BridgeClient, BridgeError
from .models import Reading

# --- Command frames (ino: the `const uint8_t *_CMD[]` block) ----------------
VERSION_CMD = bytes([0x01, 0x00, 0x03, 0x01])              # interface/fw version
CONTRACT_CMD = bytes([0x01, 0x00, 0x03, 0x02])             # Desk<->fw contract (3 bytes)

# Compatibility-contract version this Desk build was written against. Must match
# PROTOCOL_VERSION in PocketOBI.ino. Bump BOTH together, and ONLY when the coupling
# actually changes (a bridge command, a decode offset, or a mirrored verdict rule) —
# NOT on cosmetic firmware version bumps. A firmware that reports a different value
# (or none: an old firmware predating opcode 0x02) means verdicts may diverge.
# The 0x02 response is [protocol_version, gamme, cell_count]; byte 0 is still the version,
# so this check is unchanged for older 1-byte firmware.
EXPECTED_PROTOCOL = 2

# Gamme/family ids reported by the device in the contract (must match GAMME_* in
# PocketOBI.ino). Used to route decoding by what the device says, not the model string.
GAMME_LXT, GAMME_XGT, GAMME_M18 = 1, 2, 3
GAMME_NAMES = {GAMME_LXT: "LXT", GAMME_XGT: "XGT", GAMME_M18: "M18"}
MODEL_CMD = bytes([0x01, 0x02, 0x10, 0xCC, 0xDC, 0x0C])
READ_DATA_CMD = bytes([0x01, 0x04, 0x1D, 0xCC, 0xD7, 0x00, 0x00, 0xFF])
READ_MSG_CMD = bytes([0x01, 0x02, 0x28, 0x33, 0xAA, 0x00])
TESTMODE_CMD = bytes([0x01, 0x03, 0x09, 0x33, 0xD9, 0x96, 0xA5])
TESTMODE_EXIT_CMD = bytes([0x01, 0x03, 0x00, 0xCC, 0xD9, 0xFF, 0xFF])
RESET_ERROR_CMD = bytes([0x01, 0x02, 0x09, 0x33, 0xDA, 0x04])
ARM_CMD = bytes([0x01, 0x02, 0x20, 0xCC, 0xF0, 0x00])          # arm charger-write
STORE_CMD = bytes([0x01, 0x02, 0x08, 0x33, 0x55, 0xA5])        # store / commit

# F0513 (older generation) — raw model + per-cell / temperature reads.
F0513_MODEL_CMD = bytes([0x01, 0x00, 0x02, 0x31])
F0513_VCELL_CMDS = [
    bytes([0x01, 0x01, 0x02, 0xCC, 0x31]),
    bytes([0x01, 0x01, 0x02, 0xCC, 0x32]),
    bytes([0x01, 0x01, 0x02, 0xCC, 0x33]),
    bytes([0x01, 0x01, 0x02, 0xCC, 0x34]),
    bytes([0x01, 0x01, 0x02, 0xCC, 0x35]),
]
F0513_TEMP_CMD = bytes([0x01, 0x01, 0x02, 0xCC, 0x52])


def _d4_read(addr: int, count: int) -> bytes:
    """A D4 addressed read of ``count`` bytes: CC D4 <lo> <hi> <count>.
    rsp_len = count + 1 so the response includes the trailing 0x06 ACK the BMS
    returns; callers slice it off (``[:count]`` / ``[0]``)."""
    return bytes([0x01, 0x04, count + 1, 0xCC, 0xD4,
                  addr & 0xFF, (addr >> 8) & 0xFF, count])


def _d6_read_byte(addr: int) -> bytes:
    """A D6 addressed single-byte read: CC D6 <lo> <hi> 01."""
    return bytes([0x01, 0x04, 0x02, 0xCC, 0xD6,
                  addr & 0xFF, (addr >> 8) & 0xFF, 0x01])


def read_version(bridge: BridgeClient) -> Tuple[int, int, int]:
    """Query the bridge's interface/firmware version (3 bytes)."""
    p = bridge.transaction(VERSION_CMD)
    if len(p) < 3:
        raise BridgeError(f"short version response: {p.hex()}")
    return p[0], p[1], p[2]


class Contract(NamedTuple):
    """The device's compatibility contract (bridge opcode 0x02). Any field is
    ``None`` when the firmware is too old to report it (see :func:`read_contract`)."""
    protocol: Optional[int]     # contract version — checked against EXPECTED_PROTOCOL
    gamme: Optional[int]        # family id (GAMME_*) — for decoder routing
    cell_count: Optional[int]   # active family cell count reported by the device

    @property
    def gamme_name(self) -> str:
        return GAMME_NAMES.get(self.gamme, "?")


def read_contract(bridge: BridgeClient) -> Contract:
    """Query the firmware's compatibility contract (see CONTRACT_CMD).

    Returns a :class:`Contract`. Every field is ``None`` for a "legacy" firmware
    that predates opcode 0x02: such a firmware drops 0x02 into serviceBridge's
    default branch — it echoes the requested rsp_len but sends NO payload, so the
    read times out -> BridgeError. A firmware that predates the 3-byte contract
    (v1) answers with just the version byte, so ``gamme`` / ``cell_count`` come back
    ``None`` while ``protocol`` is still read. This probe never raises: a mismatch is
    a non-blocking warning, never a hard failure (the transport is a stable drop-in
    ArduinoOBI regardless of version).
    """
    try:
        p = bridge.transaction(CONTRACT_CMD, retries=0)
    except BridgeError:
        return Contract(None, None, None)
    return Contract(
        p[0] if len(p) >= 1 else None,
        p[1] if len(p) >= 2 else None,
        p[2] if len(p) >= 3 else None,
    )


def read_protocol_version(bridge: BridgeClient) -> int | None:
    """Contract version only (byte 0). Thin wrapper over :func:`read_contract`."""
    return read_contract(bridge).protocol


def _read_extended(bridge: BridgeClient, r: Reading) -> None:
    """Best-effort extended D4/D6 read (latched-fault markers, counters, dates).

    CAVEAT — needs hardware validation: on-device, readExtended() does the whole
    D4/D6 sweep inside ONE ENABLE session after a single TESTMODE. Through the
    bridge each command is a separate transaction that toggles ENABLE and resets
    the bus, so TESTMODE may not persist across them. If it doesn't, the reads
    return 0xFF and this degrades gracefully (ext_valid stays False, latched_fault
    stays False — the verdict is still computed from cell/temperature signals).
    If hardware proves TESTMODE doesn't survive, the fix is a dedicated firmware
    bridge opcode that runs the sweep device-side (phase-2 firmware change).
    """
    if r.is_f0513:
        return
    try:
        bridge.transaction(TESTMODE_CMD)
        fault_a = bridge.transaction(_d6_read_byte(0x58D))[0]
        fault_b = bridge.transaction(_d6_read_byte(0x309))[0]
        asm = [bridge.transaction(_d4_read(a, 1))[0] for a in (0x000, 0x001, 0x002)]
        soc = bridge.transaction(_d4_read(0x150, 2))[:2]
        od_event = bridge.transaction(_d4_read(0x0BA, 1))[0]
        ol_block = bridge.transaction(_d4_read(0x08D, 7))[:7]
        bridge.transaction(TESTMODE_EXIT_CMD)
    except (BridgeError, IndexError):
        return  # extended is optional; leave ext_valid False

    # A 0xFF over-discharge count means the D4 path did not answer, so the WHOLE
    # extended block — OD/OL and the D6 fault markers — is untrustworthy (one old
    # pack read odCnt=FF with marker 0x309=FD -> a false latched/70 %) (ino: readExtended).
    if od_event == 0xFF:
        return
    decode.apply_extended(r, fault_a, fault_b, asm, soc, od_event, ol_block)


def _frame_write_cmd(frame32: bytes) -> bytes:
    """0x33 frame-write: reset, 33, (ROM), write [0x0F, 0x00, <32 frame bytes>].
    rsp_len = 8 (ROM only, no payload) — mirrors the device writeFrame/ow33."""
    return bytes([0x01, 34, 8, 0x33, 0x0F, 0x00]) + bytes(frame32[:32])


def unlock(bridge: BridgeClient) -> Reading:
    """Clear a charger lock (frame repair) and return a fresh post-unlock reading.

    Clean-room reimplementation of the device unlockRepair() using the same
    opcodes: read the frame, rebuild it (clear nybble 34 + recompute CS0/CS1/CS2,
    NEVER touching the failure code), write it back (arm CC F0 00 -> 33 0F 00 +
    32B -> store 33 55 A5), then a full error reset. Re-reads to verify.

    CAVEAT (needs hardware validation): on-device the write is followed by an
    explicit bus power-cycle so the BMS commits to flash; over the bridge we rely
    on the per-command ENABLE toggling instead. Validate on a KNOWN false-locked
    pack first. Only touches nybble 34 — never the failure code / status.
    """
    r = read_all(bridge, extended=False)
    if not r.valid or r.is_f0513:
        raise BridgeError("no standard pack to unlock")

    repaired = decode.build_repaired_frame(r.msg)
    bridge.transaction(ARM_CMD)                 # arm the charger-write
    bridge.transaction(_frame_write_cmd(repaired))
    bridge.transaction(STORE_CMD)               # store / commit
    # Full error reset (TESTMODE -> RESET_ERROR -> TESTMODE exit).
    bridge.transaction(TESTMODE_CMD)
    bridge.transaction(RESET_ERROR_CMD)
    bridge.transaction(TESTMODE_EXIT_CMD)

    return read_all(bridge, extended=True)      # verify


def read_all(bridge: BridgeClient, extended: bool = True) -> Reading:
    """Full read of the connected pack into a fresh ``Reading``.

    Handles standard and F0513 packs, preserving the live-before-0x33 ordering.
    Raises ``BridgeError`` only if the initial model read fails entirely.

    ``extended`` (default ON) adds the D4/D6 sweep (latched-fault markers,
    counters, dates). It is the only signal that catches a latched real fault on a
    pack that reads clean at rest (one that re-locks on charge) — without it such a
    pack is wrongly reported HEALTHY. It is best-effort: on any bus error it degrades
    gracefully (see _read_extended),
    and the bridge retries/resyncs the link so an occasional glitch on the D4/D6
    sweep does not break the next read.
    """
    r = Reading()

    model_payload = bridge.transaction(MODEL_CMD)
    model_ascii = decode.is_printable_ascii(model_payload, 7)

    # Read live data BEFORE the 0x33 message: the defensive order for packs where the live
    # read can go mute after a 0x33 read (the bridge does not power-cycle between commands
    # the way the standalone device does).
    live_payload = bridge.transaction(READ_DATA_CMD)   # BEFORE the 0x33 read
    msg_resp = bridge.transaction(READ_MSG_CMD)        # 8 ROM + 32 message

    # Identify by the 0x33 frame, NOT the ASCII model (ino: readStaticInfo): some
    # old packs answer READ_MSG + live perfectly but return all-FF to MODEL. A valid
    # 0x33 frame ⇒ standard pack; fall to F0513 ONLY when READ_MSG itself is silent.
    if len(msg_resp) >= 40 and not decode.is_all_ff(msg_resp[:40]):
        # --- Standard pack ---
        rom_id, msg = msg_resp[:8], msg_resp[8:40]
        decode.apply_static_standard(r, model_payload, msg, rom_id)
        if not model_ascii:
            r.model = "LXT ?"   # MODEL silent on this generation: unidentified standard LXT

        # Live: D7 normally; if D7 is silent (all-FF), read the cells over the F0513 set
        # regardless of the static path — a D7-silent standard pack otherwise decodes
        # ~65.5 V / ~6280 C -> false REAL_FAULT (ino: readLiveData fallback).
        if decode.is_all_ff(live_payload):
            cells_raw = [decode.le16(bridge.transaction(c), 0) for c in F0513_VCELL_CMDS]
            temp_raw = decode.le16(bridge.transaction(F0513_TEMP_CMD), 0)
            decode.apply_live_f0513(r, cells_raw, temp_raw)   # single-sensor
        else:
            decode.apply_live_standard(r, live_payload)

        r.raw_model = bytes(model_payload)
        r.raw_live = bytes(live_payload)
        if extended:
            _read_extended(bridge, r)
    else:
        # --- Older F0513 generation (0x33 frame silent) ---
        f = bridge.transaction(F0513_MODEL_CMD)
        # serviceBridge returns [b2, b1]; model = BL{b2:X}{b1:X}.
        model = decode.f0513_model_string(f[1], f[0]) if len(f) >= 2 else "BL?"
        decode.apply_static_f0513(r, model)

        cells_raw = [decode.le16(bridge.transaction(c), 0) for c in F0513_VCELL_CMDS]
        temp_raw = decode.le16(bridge.transaction(F0513_TEMP_CMD), 0)
        decode.apply_live_f0513(r, cells_raw, temp_raw)

    return r

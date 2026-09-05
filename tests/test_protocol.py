"""End-to-end tests: FakeBridge -> protocol.read_all -> decode -> verdict.

Proves the whole link/decode/verdict chain wires together, and pins the
live-before-0x33 read ordering.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packscope import protocol
from packscope.bridge import FakeBridge
from packscope.models import Verdict
from packscope.verdict import compute_verdict


def le(v):
    return bytes([v & 0xFF, (v >> 8) & 0xFF])


def build_live(pack_mv, cells_mv, t1_raw, t2_raw):
    p = bytearray(29)
    p[0:2] = le(pack_mv)
    for i in range(5):
        p[2 + 2 * i:4 + 2 * i] = le(cells_mv[i])
    p[14:16] = le(t1_raw)
    p[16:18] = le(t2_raw)
    return bytes(p)


def build_msg_resp(rom_hex, msg=None):
    rom = bytes.fromhex(rom_hex)
    msg = bytes(msg) if msg is not None else bytes(32)
    return rom + msg


def test_read_all_bl1860b_healthy():
    bridge = FakeBridge()
    bridge.add(protocol.MODEL_CMD, b"BL1860B" + b"\x00" * 9)
    bridge.add(protocol.READ_DATA_CMD, build_live(20457, [4096] * 5, 3053, 3061))
    bridge.add(protocol.READ_MSG_CMD, build_msg_resp("1807050214BC4E37"))
    # No extended responses -> FakeBridge returns 0xFF -> graceful skip.

    r = protocol.read_all(bridge)

    assert r.valid and not r.is_f0513
    assert r.model == "BL1860B"
    assert r.serial_no == "1807050214BC4E37"
    assert r.pack_voltage == pytest.approx(20.457, abs=1e-3)
    assert r.temp_cell == pytest.approx(32.15, abs=0.01)
    assert r.latched_fault is False        # extended degraded gracefully
    assert compute_verdict(r) == Verdict.HEALTHY


def test_read_ordering_live_before_message():
    bridge = FakeBridge()
    bridge.add(protocol.MODEL_CMD, b"BL1860B" + b"\x00" * 9)
    bridge.add(protocol.READ_DATA_CMD, build_live(20457, [4096] * 5, 3053, 3061))
    bridge.add(protocol.READ_MSG_CMD, build_msg_resp("1807050214BC4E37"))

    protocol.read_all(bridge)

    # MODEL first, then LIVE (0xCC D7) strictly before MESSAGE (0x33 AA).
    assert bridge.sent[0] == protocol.MODEL_CMD
    assert bridge.sent[1] == protocol.READ_DATA_CMD
    assert bridge.sent[2] == protocol.READ_MSG_CMD
    live_i = bridge.sent.index(protocol.READ_DATA_CMD)
    msg_i = bridge.sent.index(protocol.READ_MSG_CMD)
    assert live_i < msg_i


def test_read_all_bl1850b_latched_suspect():
    # Balanced cells, normal temps, but the latched marker is set (via extended).
    msg = bytearray(32)
    msg[20] = 0x03                         # locked nibble
    bridge = FakeBridge()
    bridge.add(protocol.MODEL_CMD, b"BL1850B" + b"\x00" * 9)
    bridge.add(protocol.READ_DATA_CMD, build_live(18570, [3720] * 5, 2992, 3002))
    bridge.add(protocol.READ_MSG_CMD, build_msg_resp("1809150211AA0102", msg))
    # Extended: latched-fault markers non-zero (0x58D=0x0B, 0x309=0x48). The block is
    # only trusted when the over-discharge count is not 0xFF (#38), so answer that D4 read.
    bridge.add(protocol._d6_read_byte(0x58D), bytes([0x0B, 0x06]))
    bridge.add(protocol._d6_read_byte(0x309), bytes([0x48, 0x06]))
    bridge.add(protocol._d4_read(0x0BA, 1), bytes([0x02, 0x06]))   # 2 over-discharge events

    r = protocol.read_all(bridge, extended=True)

    assert r.locked is True
    assert r.latched_fault is True
    assert compute_verdict(r) == Verdict.SUSPECT


def test_standard_pack_with_nonascii_model_is_identified_by_frame():
    # #38: an old pack answers READ_MSG + live but returns non-ASCII to MODEL. It must
    # stay on the standard path (model "LXT ?"), NOT fall into F0513 (which zeroes fields).
    bridge = FakeBridge()
    bridge.add(protocol.MODEL_CMD, b"\xff" * 16)                    # MODEL silent / non-ASCII
    bridge.add(protocol.READ_DATA_CMD, build_live(18490, [3698] * 5, 2972, 2982))
    bridge.add(protocol.READ_MSG_CMD, build_msg_resp("1301070211AA0102"))

    r = protocol.read_all(bridge)

    assert r.valid and not r.is_f0513
    assert r.model == "LXT ?"
    assert r.serial_no == "1301070211AA0102"
    assert r.pack_voltage == pytest.approx(18.490, abs=1e-3)


def test_d7_silent_standard_pack_falls_back_to_f0513_cells():
    # #38: a standard pack (valid 0x33 frame) whose D7 live read is silent (all-FF) must
    # read its cells over the F0513 set, single-sensor — NOT decode FF as ~65 V / ~6280 C.
    bridge = FakeBridge()
    bridge.add(protocol.MODEL_CMD, b"BL1830B" + b"\x00" * 9)
    # READ_DATA_CMD left unregistered -> FakeBridge returns all-0xFF (D7 silent).
    bridge.add(protocol.READ_MSG_CMD, build_msg_resp("1301070211AA0102"))
    for c in protocol.F0513_VCELL_CMDS:
        bridge.add(c, le(3200))
    bridge.add(protocol.F0513_TEMP_CMD, le(2972))

    r = protocol.read_all(bridge)

    assert r.valid and not r.is_f0513          # still a standard pack by identity
    assert r.board_temp_valid is False         # single-sensor fallback
    assert r.pack_voltage == pytest.approx(16.0, abs=1e-3)   # 5 x 3.200 V, not 65 V
    assert r.temp_cell == pytest.approx(24.05, abs=0.01)  # 2972/10-273.15, shows 24 C


def test_extended_bails_when_overdischarge_count_is_ff():
    # #38: latched markers set but the D4 over-discharge count reads 0xFF (D4 path silent)
    # -> the whole extended block is untrusted, latched stays False (no false SUSPECT).
    bridge = FakeBridge()
    bridge.add(protocol.MODEL_CMD, b"BL1850B" + b"\x00" * 9)
    bridge.add(protocol.READ_DATA_CMD, build_live(18570, [3720] * 5, 2992, 3002))
    bridge.add(protocol.READ_MSG_CMD, build_msg_resp("1809150211AA0102"))
    bridge.add(protocol._d6_read_byte(0x58D), bytes([0x0B, 0x06]))
    bridge.add(protocol._d6_read_byte(0x309), bytes([0x48, 0x06]))
    # 0x0BA (over-discharge count) left unregistered -> 0xFF -> extended block bails.

    r = protocol.read_all(bridge, extended=True)

    assert r.ext_valid is False
    assert r.latched_fault is False
    assert compute_verdict(r) == Verdict.HEALTHY


def test_read_all_f0513_path():
    bridge = FakeBridge()
    bridge.add(protocol.MODEL_CMD, b"\xff" * 16)          # not ASCII -> F0513
    bridge.add(protocol.F0513_MODEL_CMD, bytes([0x18, 0x50]))
    for c in protocol.F0513_VCELL_CMDS:
        bridge.add(c, le(3600))
    bridge.add(protocol.F0513_TEMP_CMD, le(2980))

    r = protocol.read_all(bridge)

    assert r.is_f0513
    assert r.model.startswith("BL")
    assert r.pack_voltage == pytest.approx(18.0, abs=1e-3)   # 5 x 3.600 V


def test_read_version():
    bridge = FakeBridge()
    bridge.add(protocol.VERSION_CMD, bytes([0x00, 0x09, 0x06]))
    assert protocol.read_version(bridge) == (0, 9, 6)


def test_read_protocol_version_present():
    bridge = FakeBridge()
    bridge.add(protocol.CONTRACT_CMD, bytes([protocol.EXPECTED_PROTOCOL]))
    assert protocol.read_protocol_version(bridge) == protocol.EXPECTED_PROTOCOL


def test_read_protocol_version_legacy_firmware_is_none():
    # A firmware predating opcode 0x02 has no canned response; on the real bridge
    # this manifests as a BridgeError (echoed rsp_len but no payload -> timeout).
    # FakeBridge(default_ff=False) raises BridgeError the same way -> None, no raise.
    bridge = FakeBridge(default_ff=False)
    assert protocol.read_protocol_version(bridge) is None


def test_read_contract_full():
    # v2 contract: [protocol_version, gamme, cell_count].
    bridge = FakeBridge()
    bridge.add(protocol.CONTRACT_CMD,
               bytes([protocol.EXPECTED_PROTOCOL, protocol.GAMME_LXT, 5]))
    c = protocol.read_contract(bridge)
    assert c.protocol == protocol.EXPECTED_PROTOCOL
    assert c.gamme == protocol.GAMME_LXT and c.gamme_name == "LXT"
    assert c.cell_count == 5


def test_read_contract_v1_firmware_reports_version_only():
    # A v1 firmware answers the contract query with just the version byte: the
    # version still reads, gamme/cell_count come back None (graceful downgrade).
    bridge = FakeBridge()
    bridge.add(protocol.CONTRACT_CMD, bytes([1]))
    c = protocol.read_contract(bridge)
    assert c.protocol == 1 and c.gamme is None and c.cell_count is None
    assert c.gamme_name == "?"


def test_read_contract_legacy_firmware_all_none():
    bridge = FakeBridge(default_ff=False)
    c = protocol.read_contract(bridge)
    assert c == protocol.Contract(None, None, None)

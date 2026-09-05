"""USB-serial link to a PocketOBI unit running in bridge mode.

The firmware's bridge (PocketOBI.ino, serviceBridge ~line 2342) speaks the
binary ArduinoOBI framing, NOT the JSON/`READ<CR>` the spec guessed:

    Desk  -> PocketOBI :  [0x01, len, rsp_len, cmd, data...]
    PocketOBI -> Desk  :  [cmd_echo, rsp_len, payload... (rsp_len bytes)]

The port is 115200 8N1. This module exposes a small ``BridgeClient`` interface
with two implementations:

  * ``SerialBridge`` — the real link over pyserial.
  * ``FakeBridge``   — replays canned responses, so the UI/DB and the whole
    protocol layer are usable and testable without any hardware.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Protocol


class BridgeError(Exception):
    """A framing error, timeout, or unexpected echo on the bridge link."""


class BridgeClient(Protocol):
    """A transport that runs one ArduinoOBI command frame and returns its
    payload. Implementations must validate the echoed command byte and return
    exactly ``rsp_len`` payload bytes (the count the firmware echoes back)."""

    def transaction(self, frame: bytes, retries: int = 0) -> bytes:
        ...

    def close(self) -> None:
        ...


def _validate_frame(frame: bytes) -> None:
    if len(frame) < 4 or frame[0] != 0x01:
        raise BridgeError(f"malformed command frame: {frame.hex()}")


# ---------------------------------------------------------------------------
# Real serial link
# ---------------------------------------------------------------------------
class SerialBridge:
    """Bridge over a real serial port (pyserial imported lazily).

    Opens the port with DTR/RTS held LOW so the ESP32-C3's native-USB auto-reset
    is not triggered — otherwise merely connecting would reboot the PocketOBI (and
    drop it out of bridge mode). ``boot_delay`` waits for the device after open in
    case a reset still happens; the caller should also retry the first handshake.
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0,
                 boot_delay: float = 0.0):
        try:
            import serial  # noqa: F401  (lazy: FakeBridge users don't need pyserial)
        except ImportError as exc:  # pragma: no cover - env dependent
            raise BridgeError(
                "pyserial is required for a real serial connection "
                "(pip install pyserial)"
            ) from exc
        import time
        self._serial_mod = serial
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        # Build closed, deassert DTR/RTS, THEN open -> no auto-reset pulse.
        self._ser = serial.Serial()
        self._ser.port = port
        self._ser.baudrate = baudrate
        self._ser.timeout = timeout
        try:
            self._ser.dtr = False
            self._ser.rts = False
        except Exception:  # pragma: no cover - some drivers reject pre-open set
            pass
        self._ser.open()
        try:
            self._ser.dtr = False
            self._ser.rts = False
        except Exception:  # pragma: no cover
            pass
        if boot_delay:
            time.sleep(boot_delay)
        try:
            self._ser.reset_input_buffer()
        except Exception:  # pragma: no cover
            pass

    def _read_exact(self, n: int) -> bytes:
        buf = self._ser.read(n)
        if len(buf) != n:
            raise BridgeError(
                f"timeout: expected {n} bytes, got {len(buf)} ({buf.hex()})"
            )
        return buf

    def transaction(self, frame: bytes, retries: int = 2) -> bytes:
        _validate_frame(frame)
        expected_cmd = frame[3]
        last: Optional[BridgeError] = None
        for attempt in range(retries + 1):
            try:
                self._ser.reset_input_buffer()
                self._ser.write(frame)
                self._ser.flush()
                cmd_echo = self._read_exact(1)[0]
                if cmd_echo != expected_cmd:
                    raise BridgeError(
                        f"cmd echo mismatch: sent 0x{expected_cmd:02X}, "
                        f"got 0x{cmd_echo:02X}")
                rsp_len = self._read_exact(1)[0]
                return self._read_exact(rsp_len)
            except BridgeError as exc:
                last = exc
                # Resync: let the firmware's per-byte read timeouts drain any
                # half-parsed frame, then flush our side before retrying.
                if attempt < retries:
                    time.sleep(0.15)
                    try:
                        self._ser.reset_input_buffer()
                    except Exception:  # pragma: no cover
                        pass
        raise last  # type: ignore[misc]

    def close(self) -> None:
        try:
            self._ser.close()
        except Exception:  # pragma: no cover
            pass


# ---------------------------------------------------------------------------
# Fake link (dev / tests)
# ---------------------------------------------------------------------------
class FakeBridge:
    """Replays canned responses keyed by the command bytes (cmd + data).

    Build one with ``add(frame, payload)`` for each command the code will send,
    or pass a dict. Unknown commands return ``default`` (an all-0xFF payload of
    the frame's rsp_len by default, i.e. "no answer"), matching how a real pack
    behaves for a command it doesn't support. Also records every frame sent, in
    ``self.sent``, for assertions.
    """

    def __init__(self, responses: Optional[Dict[bytes, bytes]] = None,
                 default_ff: bool = True):
        self._responses: Dict[bytes, bytes] = dict(responses or {})
        self.default_ff = default_ff
        self.sent: List[bytes] = []

    @staticmethod
    def _key(frame: bytes) -> bytes:
        # cmd + data uniquely identify a command (incl. D4/D6 address bytes).
        return bytes(frame[3:])

    def add(self, frame: bytes, payload: bytes) -> "FakeBridge":
        self._responses[self._key(frame)] = bytes(payload)
        return self

    def transaction(self, frame: bytes, retries: int = 0) -> bytes:
        _validate_frame(frame)
        self.sent.append(bytes(frame))
        key = self._key(frame)
        if key in self._responses:
            return self._responses[key]
        if self.default_ff:
            return b"\xff" * frame[2]   # rsp_len bytes of 0xFF = no answer
        raise BridgeError(f"FakeBridge: no canned response for {frame.hex()}")

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------
def list_serial_ports() -> List[str]:
    """Available serial port device names (empty if pyserial is missing)."""
    try:
        from serial.tools import list_ports
    except ImportError:  # pragma: no cover - env dependent
        return []
    return [p.device for p in list_ports.comports()]

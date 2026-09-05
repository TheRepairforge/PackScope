"""App-data paths and persisted settings for PackScope.

Data lives in a per-user app-data directory:
  * Windows : %APPDATA%/PackScope/
  * Linux/Mac: ~/.packscope/
holding the SQLite DB and a small ``config.json``.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict


def _portable_dir() -> Path | None:
    """Portable mode: a frozen build with a ``portable.txt`` marker next to the
    executable keeps everything in ``data/`` beside it (USB-stick use), instead of
    the per-user location. Returns that dir, or None for the normal location."""
    if not getattr(sys, "frozen", False):
        return None
    exe_dir = Path(sys.executable).resolve().parent
    if (exe_dir / "portable.txt").exists():
        d = exe_dir / "data"
        d.mkdir(parents=True, exist_ok=True)
        return d
    return None


def app_data_dir() -> Path:
    """The per-user app-data directory (created on demand). A frozen build with a
    ``portable.txt`` next to the executable stores data in ``data/`` there instead."""
    portable = _portable_dir()
    if portable is not None:
        return portable
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or str(Path.home())
        d = Path(base) / "PackScope"
    else:
        d = Path.home() / ".packscope"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_db_path() -> Path:
    return app_data_dir() / "packscope.db"


def config_path() -> Path:
    return app_data_dir() / "config.json"


@dataclass
class Settings:
    """User-facing settings (Settings screen, phase 2). Kept minimal for now."""

    serial_port: str = ""            # default port, "" = ask each time
    temp_unit: str = "C"             # "C" or "F"
    language: str = "en"             # "en"/"fr"/"de"/"es" (JP: default EN)
    appearance: str = "dark"         # "dark" (default) or "light"
    csv_columns: str = "full"        # "makita" (compat) or "full"
    db_path: str = ""                # "" = default_db_path()
    # Reserved for a FUTURE manual report export (never auto-sent). Generated
    # once so a shared export could hash serials consistently if the user opts in.
    report_seed: str = ""

    extra: Dict[str, Any] = field(default_factory=dict)

    def resolved_db_path(self) -> Path:
        return Path(self.db_path) if self.db_path else default_db_path()


def load_settings() -> Settings:
    p = config_path()
    if not p.exists():
        return Settings()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return Settings()
    known = {f: data[f] for f in Settings.__dataclass_fields__ if f in data}
    s = Settings(**known)
    # Keep any unknown keys around so a newer config isn't clobbered by an old build.
    s.extra = {k: v for k, v in data.items() if k not in Settings.__dataclass_fields__}
    return s


def save_settings(s: Settings) -> None:
    data = asdict(s)
    extra = data.pop("extra", {})
    data.update(extra)
    config_path().write_text(json.dumps(data, indent=2), encoding="utf-8")

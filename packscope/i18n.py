"""Tiny runtime translation layer for the Desk UI.

Catalogs live in ``locales/{en,fr,de,es}.json`` and are GENERATED from the firmware
STRTAB by ``tools/gen_locales.py`` (the firmware is the canonical source — see that
script). This module just loads them and resolves a key at call time:

    from .. import i18n
    i18n.set_language("fr")
    i18n.t("S_REPAIR")                      -> "Réparer"
    i18n.t("S_ACT_SENSE", 3)               -> "Ressoude le fil du groupe 3"

Resolution order for a key: active language -> English -> the key itself (so a
missing key is VISIBLE in the UI, never a blank). Positional args, when given, are
applied printf-style (``%d``) to match the firmware format strings verbatim.

Default language is English (JP: always start in EN; the user switches in Settings).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

LANGS = ("en", "fr", "de", "es")
DEFAULT = "en"

_LOCALES_DIR = Path(__file__).resolve().parent / "locales"
_catalogs: Dict[str, Dict[str, str]] = {}
_lang = DEFAULT


def _load() -> None:
    """Load every catalog once (idempotent)."""
    if _catalogs:
        return
    for lang in LANGS:
        path = _LOCALES_DIR / f"{lang}.json"
        try:
            _catalogs[lang] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _catalogs[lang] = {}


def set_language(lang: str) -> None:
    """Set the active language (falls back to English if unknown)."""
    global _lang
    _load()
    _lang = lang if lang in LANGS else DEFAULT


def current() -> str:
    return _lang


def available() -> tuple:
    return LANGS


def t(key: str, *args, **kwargs) -> str:
    """Translate ``key`` in the active language, with EN fallback then the key.

    Two placeholder styles, so a template can reorder words per language:
      * positional ``args`` -> printf ``%d``/``%s`` (firmware strings use these);
      * keyword ``kwargs``  -> ``str.format`` ``{name}`` / ``{val:.0f}`` (Desk
        diagnostic templates use these, since word order varies by language).
    A format mismatch degrades to the raw string rather than raising.
    """
    _load()
    s = _catalogs.get(_lang, {}).get(key)
    if s is None:
        s = _catalogs.get(DEFAULT, {}).get(key)
    if s is None:
        return key
    if kwargs:
        try:
            return s.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return s
    if args:
        try:
            return s % args
        except (TypeError, ValueError):
            return s
    return s

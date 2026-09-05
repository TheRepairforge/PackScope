"""i18n runtime layer: catalogs load, key parity, resolution + fallback."""

from __future__ import annotations

import json
from pathlib import Path

from packscope import i18n

_LOCALES = Path(i18n.__file__).resolve().parent / "locales"


def _cat(lang: str) -> dict:
    return json.loads((_LOCALES / f"{lang}.json").read_text(encoding="utf-8"))


def test_all_catalogs_present_and_same_keys():
    keysets = {lang: set(_cat(lang)) for lang in i18n.LANGS}
    en = keysets["en"]
    assert len(en) >= 90                       # ~126 keys parsed from STRTAB
    for lang, ks in keysets.items():
        assert ks == en, f"{lang} key set differs from en: {en ^ ks}"


def test_translation_and_accents():
    i18n.set_language("fr")
    assert i18n.t("S_REPAIR") == "Réparer"
    assert i18n.t("S_CONDITION") == "État"
    i18n.set_language("de")
    assert i18n.t("S_CAPACITY") == "Kapazität"
    i18n.set_language("es")
    assert i18n.t("S_BATTERY") == "Batería"


def test_english_default_and_key_fallback():
    i18n.set_language("en")
    assert i18n.t("S_BATTERY") == "Battery"
    # Unknown key -> returned verbatim (visible, never blank).
    assert i18n.t("S_DOES_NOT_EXIST_XYZ") == "S_DOES_NOT_EXIST_XYZ"


def test_missing_key_falls_back_to_english(monkeypatch):
    i18n._load()
    # Remove a key from the FR catalog in-memory -> should fall back to EN.
    i18n.set_language("fr")
    saved = dict(i18n._catalogs["fr"])
    try:
        i18n._catalogs["fr"].pop("S_BATTERY", None)
        assert i18n.t("S_BATTERY") == "Battery"   # EN fallback
    finally:
        i18n._catalogs["fr"] = saved


def test_printf_args():
    i18n.set_language("en")
    assert i18n.t("S_ACT_SENSE", 3) == "Resolder sense wire on group 3"
    # Format mismatch degrades to the raw string, never raises.
    i18n.set_language("fr")
    assert "%d" not in i18n.t("S_ACT_SENSE", 2)


def test_unknown_language_falls_back_to_default():
    i18n.set_language("jp")           # parked / unsupported
    assert i18n.current() == "en"
    assert i18n.t("S_BATTERY") == "Battery"


def test_desk_only_keys_present_and_translated():
    # DESK_* keys are hand-authored (not from STRTAB) and merged into every catalog.
    i18n.set_language("fr")
    assert i18n.t("DESK_READ_PACK") == "Lire le pack"
    i18n.set_language("en")
    assert i18n.t("DESK_READ_PACK") == "Read pack"


def test_diagnose_translates_but_db_detail_stays_english():
    from packscope.models import Reading
    from packscope import verdict as V
    # Pinned-thermistor reading -> THERMISTOR finding (see test_verdict ground truth).
    r = Reading(valid=True)
    r.cell = [3.13] * 5
    r.cell_diff = 0.0
    r.pack_voltage = sum(r.cell)
    r.temp_cell, r.temp_mosfet = -30.15, 35.35
    r.msg = b""

    i18n.set_language("fr")
    d = V.diagnose(r)
    assert "thermistance" in d["cause"].lower()      # translated to FR
    # DB detail is forced to English regardless of the active UI language...
    detail = V.verdict_detail_text(r)
    assert "thermistor" in detail.lower()
    # ...and the UI language is restored afterwards.
    assert i18n.current() == "fr"
    i18n.set_language("en")


def test_verdict_key_matches_english_label():
    # The UI translates the verdict word via i18n.t(verdict_key(v)); in English it
    # must equal verdict_label(v) exactly (no wording gap with the firmware).
    from packscope.models import Verdict
    from packscope.verdict import verdict_key, verdict_label
    i18n.set_language("en")
    for v in Verdict:
        assert i18n.t(verdict_key(v)) == verdict_label(v)

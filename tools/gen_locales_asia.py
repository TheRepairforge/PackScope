"""Generate the Desk's Asia catalogs (ja, ko, zh, zh_tw, vi) next to the EN/FR/DE/ES ones.

The EU catalogs come from the firmware STRTAB (`gen_locales.py`). The firmware's Asia
languages live in separate one-column tables (`PocketOBI/strings_<lang>.h`, `STRTAB_<LANG>[]`,
one entry per StrId, `nullptr` = untranslated), which `gen_locales.py` must not parse (it
requires four literals per row). This script fills each Asia catalog, for every key of the
on-disk `en.json` (the key set stays identical across languages, `tests/test_i18n.py`):

    1. `desk_strings_asia.py` ASIA[lang][key], when present (Desk-only DESK_*/HK_* keys,
       and every Vietnamese S_* key: the firmware's VI is ASCII, the Desk restores diacritics);
    2. else an S_* key from the firmware table, verbatim (JA reviewed by a native speaker in
       PocketOBI 2.7.1; ZH/TW written by native users, D70/D72);
    3. else English (what the device shows for an untranslated string).

Like `gen_locales.py`, the default is a MERGE: values already in an on-disk catalog are kept
(hand edits survive), only missing keys are added. `--overwrite` reseeds from the sources.

Usage:
    python tools/gen_locales_asia.py [--fw DIR] [--out DIR] [--check] [--overwrite]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from gen_locales import DEFAULT_OUT, _c_string_literals  # noqa: E402

# Desk language code -> firmware header suffix / array suffix.
ASIA = {"ja": "JA", "ko": "KO", "zh": "ZH", "zh_tw": "ZH_TW", "vi": "VI"}
DEFAULT_FW = _HERE.parent.parent / "PocketOBI"
_PH = re.compile(r"%[-0-9.]*[dsfX]|\{[a-z_]+(?::[^}]*)?\}")


def parse_column(src: str, lang: str) -> dict[str, str]:
    """Map S_* -> string from `STRTAB_<LANG>[] = { /*S_X*/ "..." | nullptr, ... };` (nullptr dropped)."""
    m = re.search(r"STRTAB_" + ASIA[lang] + r"\[\]\s*=\s*\{(.*?)\n\};", src, re.DOTALL)
    if not m:
        raise SystemExit(f"error: STRTAB_{ASIA[lang]} not found")
    out = {}
    for line in m.group(1).splitlines():
        lab = re.match(r"\s*/\*\s*(S_[A-Z0-9_]+)\s*\*/\s*(.*)", line)
        if not lab:
            continue
        body = re.sub(r"//.*$", "", lab.group(2))      # the trailing // EN: "..." comment
        lits = _c_string_literals(body)
        if lits:
            out[lab.group(1)] = "".join(lits)
    return out


def placeholders(s: str) -> list[str]:
    return sorted(_PH.findall(s))


def build(en: dict, fw: dict, over: dict) -> dict:
    cat = {}
    for key, en_val in en.items():
        if key in over:
            cat[key] = over[key]
        elif key.startswith("S_") and key in fw:
            cat[key] = fw[key]
        else:
            cat[key] = en_val
    return cat


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fw", type=Path, default=DEFAULT_FW, help="PocketOBI firmware tree")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="locales dir")
    ap.add_argument("--check", action="store_true", help="report only, do not write")
    ap.add_argument("--overwrite", action="store_true", help="reseed, discarding hand edits")
    args = ap.parse_args()
    from desk_strings_asia import ASIA as OVER        # noqa: E402

    en = json.loads((args.out / "en.json").read_text(encoding="utf-8"))
    bad = 0
    for lang, suffix in ASIA.items():
        fw = parse_column((args.fw / f"strings_{suffix.lower()}.h").read_text(encoding="utf-8"), lang)
        seed = build(en, fw, OVER.get(lang, {}))
        for k, v in seed.items():
            if placeholders(v) != placeholders(en[k]):
                print(f"  [{lang}] {k}: placeholders {placeholders(v)} != EN {placeholders(en[k])}")
                bad += 1
            if unicodedata.normalize("NFC", v) != v:
                print(f"  [{lang}] {k}: not NFC")
                bad += 1
        english = [k for k in seed if seed[k] == en[k] and any(c.isalpha() for c in en[k])]
        print(f"{lang}: {len(seed)} keys, {len(OVER.get(lang, {}))} from desk_strings_asia, "
              f"{sum(1 for k in seed if k.startswith('S_') and k in fw and k not in OVER.get(lang, {}))} "
              f"from the firmware, {len(english)} same as English")
        if args.check:
            continue
        path = args.out / f"{lang}.json"
        final = seed
        if path.exists() and not args.overwrite:
            final = json.loads(path.read_text(encoding="utf-8"))
            for k in seed:
                final.setdefault(k, seed[k])
            for k in [k for k in final if k not in seed]:
                del final[k]                          # key set follows en.json
        path.write_text(json.dumps(final, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

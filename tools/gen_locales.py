"""Generate the Desk translation catalogs from the firmware's STRTAB.

The PocketOBI firmware (`PocketOBI/PocketOBI.ino`) already ships a complete i18n
system: `enum StrId { ... }` + `STRTAB[S_COUNT][LANG_COUNT]` with EN/FR/DE/ES, plus
`tr()`. That table is the CANONICAL source of the shared vocabulary — verdicts,
field names, and the diagnostic wording — so the two tools never drift ("no gap"
requirement).

This script parses that table out of the .ino and emits one JSON catalog per
language under `packscope/locales/`. The firmware is constrained to ASCII
(embedded font, no accents: "Reparer", "Kapazitaet", "Bateria"); the Desk has no
such limit, so we RESTORE proper accents via a per-key override table
(`locale_accents.py`). Keys are kept VERBATIM from the firmware (`S_BATTERY`, ...)
so a coherence check can diff the two sides key-for-key.

Run it whenever the firmware strings change; commit the regenerated JSON. It is a
maintenance tool, not a runtime dependency (the app reads the committed JSON).

The catalogs are HAND-CURATED after generation (JP reviews FR wording — infinitive
register, etc.), so by default this MERGES: existing on-disk values are kept and
only missing keys are added. Regenerating is therefore safe and never clobbers a
reviewed translation. Use --overwrite only to deliberately reseed from the sources.

Usage:
    python tools/gen_locales.py [--ino PATH] [--out DIR] [--check] [--overwrite]

    --check     : do not write; only report parse counts + accent-review candidates
                  (exit 1 if the key count looks wrong). Handy for CI.
    --overwrite : reseed every value from the sources, DISCARDING hand edits in the
                  catalogs (default is a non-destructive merge).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

# Firmware column order in STRTAB[...][LANG_COUNT].
LANGS = ["en", "fr", "de", "es"]

# Repo layout: this file is PackScope/tools/gen_locales.py; the firmware repo
# is a sibling of PackScope/. Both are overridable on the command line.
_HERE = Path(__file__).resolve().parent
# The i18n table (enum StrId + STRTAB) was extracted from PocketOBI.ino into its own
# header (backlog #25 / D9 stage 1), so parse THAT, not the .ino.
DEFAULT_INO = _HERE.parent.parent / "PocketOBI" / "strings_i18n.h"
DEFAULT_OUT = _HERE.parent / "packscope" / "locales"


def _strip_comments(text: str) -> str:
    """Remove // line comments and /* */ block comments (for the enum body only —
    NOT used on STRTAB, whose /*S_XXX*/ labels we rely on)."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def parse_enum_keys(src: str) -> list[str]:
    """Ordered StrId identifiers (S_COUNT excluded)."""
    m = re.search(r"enum\s+StrId\s*\{(.*?)\};", src, re.DOTALL)
    if not m:
        raise SystemExit("error: could not find `enum StrId { ... };` in the firmware i18n source")
    body = _strip_comments(m.group(1))
    keys = [tok for tok in re.findall(r"S_[A-Z0-9_]+", body) if tok != "S_COUNT"]
    if not keys:
        raise SystemExit("error: enum StrId parsed empty")
    return keys


def _c_string_literals(row_body: str) -> list[str]:
    """Extract C string literals from a STRTAB row body, honoring \\" and \\\\."""
    raw = re.findall(r'"((?:[^"\\]|\\.)*)"', row_body)
    out = []
    for s in raw:
        s = s.replace('\\"', '"').replace("\\\\", "\\")
        out.append(s)
    return out


def parse_strtab(src: str) -> dict[str, list[str]]:
    """Map each firmware key -> [EN, FR, DE, ES], parsed by its /*S_XXX*/ label."""
    m = re.search(
        r"STRTAB\[S_COUNT\]\[LANG_COUNT\]\s*=\s*\{(.*?)\n\};", src, re.DOTALL
    )
    if not m:
        raise SystemExit("error: could not find the STRTAB initializer in the firmware i18n source")
    body = m.group(1)
    table: dict[str, list[str]] = {}
    # Each row: /*S_XXX*/ { "en", "fr", "de", "es" },
    for label, row in re.findall(
        r"/\*\s*(S_[A-Z0-9_]+)\s*\*/\s*\{(.*?)\}\s*,", body, re.DOTALL
    ):
        lits = _c_string_literals(row)
        if len(lits) != len(LANGS):
            raise SystemExit(
                f"error: {label} has {len(lits)} literals, expected {len(LANGS)}: {lits!r}"
            )
        table[label] = lits
    if not table:
        raise SystemExit("error: STRTAB parsed empty")
    return table


def _looks_unaccented(s: str, lang: str) -> bool:
    """Heuristic: an FR/DE/ES string that is pure ASCII and contains a lowercase
    letter is a candidate for a missing accent (for the review report only)."""
    if lang == "en":
        return False
    ascii_only = all(ord(c) < 128 for c in s)
    return ascii_only and any(c.isalpha() for c in s)


def build_catalogs(table: dict[str, list[str]], accents: dict,
                   desk: dict | None = None) -> dict[str, dict]:
    """Produce {lang: {key: string}}: firmware S_* keys (with accent overrides)
    merged with the hand-authored Desk-only DESK_* keys."""
    cat = {lang: {} for lang in LANGS}
    for key, cols in table.items():
        for i, lang in enumerate(LANGS):
            value = cols[i]
            override = accents.get(lang, {}).get(key)
            if override is not None:
                value = override
            cat[lang][key] = value
    for key, langmap in (desk or {}).items():
        for lang in LANGS:
            # DESK_* entries fall back to EN if a language is missing.
            cat[lang][key] = langmap.get(lang, langmap.get("en", key))
    return cat


def review_candidates(cat: dict[str, dict]) -> dict[str, list[str]]:
    """Per-language keys whose value is still pure-ASCII (likely need review)."""
    out: dict[str, list[str]] = {}
    for lang in ("fr", "de", "es"):
        flagged = [k for k, v in cat[lang].items() if _looks_unaccented(v, lang)]
        if flagged:
            out[lang] = flagged
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ino", type=Path, default=DEFAULT_INO,
                    help=f"path to the firmware i18n source strings_i18n.h (default: {DEFAULT_INO})")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"output locales dir (default: {DEFAULT_OUT})")
    ap.add_argument("--check", action="store_true",
                    help="report only, do not write files")
    ap.add_argument("--overwrite", action="store_true",
                    help="reseed every value from the sources, DISCARDING hand edits "
                         "in the on-disk catalogs (default: merge — keep existing "
                         "values, only add missing keys)")
    args = ap.parse_args()

    if not args.ino.exists():
        raise SystemExit(f"error: firmware source not found: {args.ino}")

    # Accent overrides live next to this script.
    sys.path.insert(0, str(_HERE))
    try:
        from locale_accents import ACCENTS  # noqa: E402
    except ImportError:
        ACCENTS = {}
        print("warning: locale_accents.py not found — emitting the firmware's "
              "ASCII strings unchanged (no accents restored).", file=sys.stderr)
    try:
        from desk_strings import DESK  # noqa: E402
    except ImportError:
        DESK = {}
        print("warning: desk_strings.py not found — no Desk-only (DESK_*) keys "
              "will be emitted.", file=sys.stderr)

    src = args.ino.read_text(encoding="utf-8", errors="replace")
    keys = parse_enum_keys(src)
    table = parse_strtab(src)

    # Every enum key must have a STRTAB row and vice versa (order preserved).
    missing = [k for k in keys if k not in table]
    extra = [k for k in table if k not in keys]
    if missing or extra:
        print(f"error: enum/STRTAB mismatch. missing rows: {missing} ; "
              f"unexpected rows: {extra}", file=sys.stderr)
        return 1

    cat = build_catalogs(table, ACCENTS, DESK)
    review = review_candidates(cat)

    print(f"parsed {len(table)} firmware keys + {len(DESK)} Desk keys "
          f"x {len(LANGS)} languages from {args.ino.name}")
    for lang in review:
        print(f"  [{lang}] {len(review[lang])} string(s) still ASCII — review: "
              + ", ".join(review[lang][:12])
              + (" ..." if len(review[lang]) > 12 else ""))

    if args.check:
        # Sanity floor: the table is ~110 keys; well below that = a parse problem.
        return 0 if len(table) >= 90 else 1

    args.out.mkdir(parents=True, exist_ok=True)
    for lang in LANGS:
        path = args.out / f"{lang}.json"
        seed = cat[lang]
        if args.overwrite or not path.exists():
            final = seed
        else:
            # MERGE (default): the on-disk catalog is authoritative — hand edits
            # (e.g. FR reviewed by JP) are NEVER overwritten. We only ADD keys the
            # catalog is missing, and report orphans / drift for a human to look at.
            existing = json.loads(path.read_text(encoding="utf-8"))
            final = dict(existing)
            added = [k for k in seed if k not in existing]
            for k in added:
                final[k] = seed[k]
            orphans = [k for k in existing if k not in seed]
            drift = [k for k in existing if k in seed and existing[k] != seed[k]]
            if added:
                print(f"  [{lang}] +{len(added)} new key(s): " + ", ".join(added[:12]))
            if orphans:
                print(f"  [{lang}] {len(orphans)} orphan(s) (in catalog, not in sources): "
                      + ", ".join(orphans[:12]))
            if drift:
                print(f"  [{lang}] {len(drift)} key(s) differ from the seed (kept the "
                      f"catalog value; --overwrite to reseed): " + ", ".join(drift[:12]))
        path.write_text(
            json.dumps(final, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {path}  ({len(final)} keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

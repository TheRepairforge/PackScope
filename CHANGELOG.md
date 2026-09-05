# Changelog

All notable changes to PackScope (the companion PC app) are documented here.
Versioning follows [Semantic Versioning](https://semver.org/): MAJOR.MINOR.PATCH.
The version is defined in `packscope/__init__.py` as `__version__`.

The verdict/decode logic here is a 1:1 port of the PocketOBI firmware
(`PocketOBI/PocketOBI.ino`), which remains the **single source of truth**. Entries
below are kept in sync with the firmware `CHANGELOG.md` when a change touches the
shared protocol, decode offsets, or verdict thresholds.

## [1.0.0] - 2026-09-05

First public release of the companion app, published as **PackScope** (renamed from the
internal "PocketOBI Desk"). Licensed **PolyForm Noncommercial 1.0.0**, matching PocketOBI.

### Added
- **Cross-platform builds** — Windows, Linux and macOS executables built by PyInstaller via
  GitHub Actions on each release tag. **Portable mode:** drop a `portable.txt` next to the
  executable to keep the database and settings beside it (USB-stick use) instead of the
  per-user app-data directory.

### Summary
- **Multilingual UI (EN/FR/DE/ES)** — the whole localized interface is now translatable, driven by
  catalogs generated from the firmware STRTAB (single source, "no gap" with the device) plus
  Desk-only `DESK_*` strings. Minor bump for the feature. See the entries below.

### Added / Changed (2026-08-15, Live-read reworked: our health estimate + wear counters)
- **Our own cycle-based health estimate is now shown** — a 3-colour bar + `%` under the pack
  voltage (`DESK_HEALTH_EST` "Health (est.)"; green ≥80 / amber 50-79 / red <50, via the new
  pure `verdict.health_band()`). This is OUR estimate (`health_est_pct = 100 − cycles/8.96`),
  a distinct axis from the verdict badge (repairability) — NOT the Makita SOH gauge, which
  stays out (we don't fake Makita's proprietary SOH). `—` on F0513 packs (no cycle data).
- **Over-discharge / over-load surfaced** (closing a gap with the device Health page): two
  tiles reusing the firmware `S_OVERDISCHARGE` / `S_OVERLOAD` strings (no label drift), showing
  the D4 **event count** as `N×` ("how many times the protection tripped"; `—` when the
  extended read didn't survive the bridge; 0 is green). The protection **threshold** is no
  longer shown on the tile (static config, it confused the reading) — it stays in the History
  technical inspector, which now shows clean `Over-disch` / `Over-load` / `SOC raw` lines
  instead of a raw dict dump.
- **Live-read metrics regrouped** for coherence: capacity moved into the header (it's a spec),
  cell spread (`Δ`) moved next to the cell bars it summarises, and the grid is now two clean
  rows — usage/wear (cycles · over-discharge · over-load) and temperature (cell · board ·
  spread). New `units.fmt_wear()`; +6 tests (89 pass).
- **Production date + age** shown right under the S/N (same mono style): `Fabriqué 2018-07-05
  (8 yr)` — from the ROM ID (`S_PRODUCED`), age in whole years via the new pure
  `units.pack_age_years()` and `DESK_AGE_YEARS`. A plain proxy for pack age, which weighs on
  the repair decision; it also fills the lower area of the card.
- **Fixed `tools/gen_locales.py`** which broke when the firmware i18n table moved to
  `strings_i18n.h` (backlog #25): it now parses the header instead of `PocketOBI.ino`.

### Changed (2026-08-15, bridge contract v2 — gamme + cell count)
- **`EXPECTED_PROTOCOL` 1 → 2**, in lockstep with the firmware's `PROTOCOL_VERSION`. The
  contract query (`CONTRACT_CMD`, opcode `0x02`) now reads **3 bytes** — `[protocol, gamme,
  cell_count]` — via the new `read_contract()`, which returns a `Contract` namedtuple and
  degrades gracefully (a v1 firmware reports only the version; a pre-`0x02` firmware still
  yields all-`None`). Added `GAMME_LXT/XGT/M18` ids. Connect stores the device-reported
  family (`app.device_gamme`) so decoding can be routed by what the device says instead of the
  model string once a second gamme's decoder exists (backlog #20). `read_protocol_version()`
  is kept as a thin wrapper. No behaviour change for the LXT path; the compatibility banner is
  unchanged. 3 new protocol tests.

### Fixed (2026-08-12, Repair finding label overflow in DE)
- The Repair "finding" label column was a fixed 90 px, so a long label collided with the value
  text (spotted in German: "Wahrscheinliche Ursache" ran into the value). Widened the column to
  115 px with an 8 px gap, and shortened the German label to "Mögl. Ursache". FR/ES ("Cause
  probable" / "Causa probable") now have margin too.

### Added (2026-08-12, German + Spanish — full first pass)
- **DE and ES now cover every `DESK_*` key** (nav, Live read, the diagnostic engine, the Repair
  wizard, Connect, Settings, status chip, and Batteries/History) — no more English fallback in
  the Desk-specific strings. Authored in `tools/desk_strings.py` and reseeded into the catalogs
  (`gen_locales.py --overwrite`; EN/FR unchanged, only `de.json`/`es.json` updated). This is a
  first full pass in a consistent register; a native proofread is still recommended (as for the
  firmware `S_*` DE/ES accents). All four languages are now selectable and complete for the whole
  localized UI. 83 tests green.

### Added (2026-08-12, localized Batteries/History screen)
- **The Batteries (History) screen is localized** (EN/FR; DE/ES fall back to EN): filters,
  search, list, detail header/stats/sections, trend, repairs, the edit-identity dialog, the
  compare dialog labels, and export status lines. `DESK_HIST_*` keys added. The metric selector,
  status labels and status filter show translated labels but keep STABLE logical keys internally
  (metrics drive `_metric_series`; status keys are stored in the DB), mapped via per-instance
  dicts rebuilt on a language switch. Fixed a latent shadowing (`for t in …` vs the `t` import).
- **Two technical inspectors stay English on purpose:** the raw reading dump and the frame-diff
  view (aligned monospace, developer-facing). About + Health card also remain English (as noted).

### Added (2026-08-12, localized Connect + Settings + shared chrome)
- **Connect, Settings, the status chip and the shared components are localized** (EN/FR; DE/ES
  fall back to EN). Connect: port picker, buttons, tips, demo section, all status/error lines +
  the firmware-compat banner. Settings: section headers, every option label (Language reuses
  `S_LANGUAGE`), the clear-history dialog; the Appearance/CSV segmented controls show translated
  labels but map back to stable codes (like the Repair held/re-locked control). Status chip
  ("not connected"/"disconnected") and the shared "No reading" placeholders too. `DESK_CONN_*`/
  `DESK_SET_*`/`DESK_STATUS_*` keys added.
- **CSV export now writes `utf-8-sig` (BOM)** so Excel — notably on non-English Windows — reads
  accents correctly. Column headers stay English (stable for external parsers). Test updated to
  read the BOM. 83 tests green.
- **About screen and the printable Health card are intentionally left in English** for now (a
  standalone customer document; its verdict detail comes from the DB, which is English).

### Added (2026-08-12, localized Repair wizard)
- **The Repair wizard (Read/Classify/Unlock/Confirm) is fully localized** (EN/FR; DE/ES fall
  back to EN). Stepper labels, step titles/descriptions, the raw-signal checklist, finding
  labels, result messages, buttons and status lines now go through `i18n.t()`; the verdict word
  uses `i18n.t(verdict_key(v))`. The checklist labels/values (Charger lock/Latched/Thermistor/
  Cells, none/yes/ok/fault) and Before/After reuse the firmware `S_*` keys (device-matching).
  `DESK_RPR_*` keys added (~39). The "held/re-locked/unknown" segmented control shows translated
  labels but maps back to stable logical keys, so stored outcomes are language-independent.

### Added (2026-08-12, localized diagnostic engine — verdict.diagnose)
- **`verdict.diagnose()` is now fully localized (EN/FR).** The rich diagnostic prose
  (Observation / likely Cause / what to Check, per fault class + the latched/thermistor/gap
  findings) was refactored from inline f-strings/concatenation into parameterised catalog
  templates (`DESK_DIAG_*`, 51 keys) resolved via `i18n.t(..., **kwargs)` (`str.format`, so
  word order can vary by language). FR follows the infinitive register; **DE/ES fall back to
  EN** for these sentences until a native review (keeps key-parity, no fake translations).
  Terminology stays anchored to the firmware (same fault classes/verdicts) — richer prose, no
  gap in meaning.
- **`i18n.t()` gains keyword placeholders** (`{name}`, `{val:.0f}`) alongside the printf `%d`
  path, needed for reorderable diagnostic templates.
- **`verdict_detail_text()` (stored in the DB) is forced to ENGLISH** regardless of the UI
  language, so historized data stays stable/analysable (matching the English health card/CSV);
  the UI language is saved and restored around it. +1 test (diagnose translates, DB detail stays
  English). 83 tests green. (Repair screen labels localize in their own later pass.)

### Added (2026-08-12, localized sidebar navigation + top-bar titles)
- **Nav entries and top-bar titles now translate** (EN/FR/DE/ES). `NAV` holds i18n keys resolved
  via `i18n.t()` at build time, so `apply_language` re-translates them: Connect/Live read/Batteries
  are Desk-only (`DESK_NAV_*`), Repair/Settings/About reuse the firmware `S_REPAIR`/`S_SETTINGS`/
  `S_ABOUT` keys (device-matching wording). FR: Connecter / Lecture directe / Réparer / Batteries /
  Réglages / À propos.

### Fixed (2026-08-12, remaining FR imperatives -> infinitive)
- Three user-facing FR strings still in the tu-imperative were switched to the infinitive register:
  `S_NO_PACK_REPLY1` ("Vérifie"→"Vérifier"), `S_ACT_IMB` ("recontrôle"→"recontrôler"),
  `S_TOAST_FIXHW` ("Répare"→"Réparer"). Purely descriptive 3rd-person strings (e.g. "Répare un
  faux verrou seulement") are intentionally left as-is (they describe the action, not command the user).

### Changed (2026-08-12, French register review + non-destructive generator)
- **French UI adopts the INFINITIVE register** (not the tu-imperative): "Connecter…lire"
  instead of "Connecte…lis", "ouvrir/vérifier/Ressouder/Mesurer/Réparer", "votre PC" not
  "ton PC", no article before "PocketOBI", "Temp." abbreviated. JP reviewed the whole
  `fr.json`; the edits were back-ported into the generator sources (`tools/desk_strings.py`
  + `tools/locale_accents.py`) so a reseed reproduces them.
- **`gen_locales.py` is now non-destructive by default (MERGE).** It keeps existing on-disk
  catalog values (so a hand-reviewed translation is NEVER clobbered) and only adds missing
  keys, reporting orphans/drift; `--overwrite` forces a full reseed from the sources. The
  catalogs are generated-then-hand-curated: edit `fr.json` freely, regen is safe.

### Added (2026-08-12, i18n PoC — Live read screen localized + DESK_* infra)
- **Live read is the first fully localized screen** (EN/FR/DE/ES). All its labels, buttons and
  status messages now go through `i18n.t()`; the verdict word uses `i18n.t(verdict_key(v))` so it
  is sourced from the firmware catalog (SAINE / DÉBLOQUER / RÉPA MATÉRIEL…) — no wording gap with
  the device. `verdict.py` gains `verdict_key(v)` (firmware STRTAB key per verdict); `verdict_label()`
  is unchanged (stays English for tests / health card).
- **Desk-only string infrastructure (`DESK_*`).** Strings with no firmware counterpart
  (Connect/Live-read/... chrome) live in `tools/desk_strings.py` (hand-authored, 4 langs) and are
  MERGED into the catalogs by `gen_locales.py` alongside the firmware `S_*` keys. Catalogs are now
  126 firmware + 20 Desk = 146 keys/lang. FR reviewed; DE/ES best-effort (native pass TODO).
- Still English until their own conversion pass: the verdict REASON sentence (`diagnose()`, next
  step) and the other screens (Connect/Repair/History/About). +2 tests (DESK_* resolution, verdict
  key↔label parity). 82 tests green.

### Added (2026-08-12, i18n runtime layer + language selector)
- **`i18n.py` translation layer + a Language selector in Settings (EN/FR/DE/ES).** `t(key,*args)`
  resolves active-language -> English -> the key itself (a missing key stays visible, never
  blank); printf args make the firmware `%d` strings work unchanged. `App.apply_language()`
  persists the choice and rebuilds the UI in place — the SAME mechanism as the light/dark
  switch. Default language = English (user switches in Settings). Not visible on screens yet:
  screens are converted to `t()` starting next (the selector already switches + rebuilds). +6
  tests (catalog key-parity across languages, accent resolution, EN fallback, printf args).

### Added (2026-08-12, i18n groundwork — catalogs derived from the firmware)
- **Translation catalogs generated from the firmware STRTAB** (not yet wired into the UI).
  `tools/gen_locales.py` parses `enum StrId` + `STRTAB` out of `PocketOBI/PocketOBI.ino` and
  emits `packscope/locales/{en,fr,de,es}.json` (126 keys, firmware key names verbatim).
  The firmware is the CANONICAL source of the shared vocabulary (verdicts, field names, DIAG
  terminology) so the two tools never drift ("no gap"). The firmware is ASCII-only (embedded
  font); `tools/locale_accents.py` restores proper accents per language — FR reviewed, DE/ES
  best-effort pending a native pass. Desk-only strings (History/Connect/...) will be added later
  under `DESK_*` keys. Not user-facing yet — the `i18n`/Settings wiring lands next.

### Added (2026-08-12, firmware compatibility check at connect)
- **Warn on a firmware/Desk version mismatch, without ever blocking.** On connect the
  Desk now queries the firmware's compatibility-contract version (bridge opcode `0x02`,
  `protocol.read_protocol_version`) and compares it to `EXPECTED_PROTOCOL` (this build =
  **1**, mirroring `PROTOCOL_VERSION` in `PocketOBI.ino`). A mismatch shows a non-blocking
  amber banner on the Connect screen:
  - `None` (older firmware predating the `0x02` opcode -> the probe times out): "some
    readings and verdicts may be missing or differ; update the firmware for full parity."
  - a different number: "verdicts may diverge; update whichever side is older."
  The connection always succeeds regardless — the transport is a stable drop-in ArduinoOBI
  frame, so a version skew degrades gracefully (missing extended reads, possibly divergent
  verdicts) rather than failing. Rationale: the real risk of running mixed versions is a
  SILENT verdict divergence (e.g. an extended latched-fault read the old side can't do), not
  a broken link. `EXPECTED_PROTOCOL` bumps in lockstep with the firmware `PROTOCOL_VERSION`.

### Fixed (2026-08-12, firmware/Desk coherence review)
- **Verdict parity: `TEMP_SPREAD_BAD` realigned to the firmware, 25 C -> 10 C**
  (`models.py`). The two-sensor "suspect thermistor" spread threshold had drifted to
  25 C here while the firmware (authoritative source of the verdict) uses 10 C. Effect
  of the bug: a pack whose two temperature probes disagreed by 10-25 C (and had no other
  fault) was reported HEALTHY (green) by the Desk while the on-device tool reported
  SUSPECT / POSSIBLE HW FIX (orange) — contradictory verdicts on the same pack. Now
  identical. 10 C is the deliberate empirical charger-refusal signal (see firmware
  `CHANGELOG.md`, "reconcile temp thresholds with Makita ground-truth"). Fixed the stale
  `(ino:953)` code reference to `(ino:1010)`, and the matching test comment.

### Docs (2026-08-12, comment cleanup — no behavior change)
- **Firmware cross-references de-drifted.** The `(ino:NNN)` line-number references in
  `decode.py`, `protocol.py` and `models.py` had gone stale (the firmware moved). Replaced
  them with STABLE references — the firmware symbol/function name (e.g. `ino: readStaticInfo`)
  or the shared byte/nybble offset — which do not drift when `PocketOBI.ino` changes. In
  `models.py` the threshold block now simply notes it mirrors the firmware `#define`s of the
  same name. Also corrected the `verdict.py` thermistor action text to the firmware's
  evidence-based wording ("Re-read cold, then check NTC") and the `_d4_read` ACK comment
  (the 0x06 is included in the response and sliced off by the caller, not stripped upstream).

### Docs (2026-08-12)
- **Read ordering: documented the INTENTIONAL divergence from the firmware** (`protocol.py`,
  no behavior change). The Desk reads live data BEFORE the static `0x33` message (the
  defensive order — live can go mute after a `0x33` read on some packs), whereas the
  firmware `readAllData()` reads static-first. On the device this is safe because
  `sendCommand()` power-cycles ENABLE around every command; the firmware order is
  HW-validated. Added a cross-reference comment so the coherence checker (and readers) see
  it is deliberate, not a desync. See firmware `CHANGELOG.md`.

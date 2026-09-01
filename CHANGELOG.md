# Changelog

## 0.3.0

- Added a version-controlled five-font registry with canonical ASS family names, aliases, canonical attachment filenames, verified versions/sizes and exact SHA-256 identities.
- Added `subflow fonts install SOURCE` and `subflow fonts verify`; user-provided fonts are matched by SHA and imported only into ignored `fonts/local/`, while source releases continue to exclude font binaries.
- Canonicalized Kiwi Collector dialogue to `WenQuanYi Micro Hei` while retaining legacy/internal family aliases for existing ASS files.
- Bound the font registry itself into deterministic QA invalidation and included registry provenance in font audit evidence.
- Changed default MKV attachment construction to use canonical attachment names while leaving MIME detection to MKVToolNix rather than forcing a maintained MIME mapping.
- Extended Hybrid special-style protection for wanted-poster/formal/document/newspaper/prop/screen-text role names.


- Hardened semantic proposal provenance/stale checks with unit and context fingerprints; imported proposal artifacts are archived with SHA-256 provenance and unimported proposals block Release.
- Added structural QA enforcement that approved/custom semantic decisions must still be materialized in the current workfile.
- Extended QA invalidation inputs to canon JSON, proposal files and configured font-map evidence.
- Bound Research, Semantic QA and Visual QA approvals to durable evidence snapshots; Release schema 3 freezes those gate snapshots plus visual-QA media identity.
- Made real FFmpeg/libass preview rendering use the exact audited font files through `fontsdir`, hash rendered frames, and invalidate prior visual evidence before rerender.
- Added explicit font-map internal-family validation when FontTools is available and blocked same-attachment-name/different-SHA font collisions.
- Preserved JP bilingual plain special Styles (Note/Title/Song/etc.) that were previously dropped when no complex override tag was present.
- Prevented explicit `single` profiles from silently becoming source-assisted merely because C is present.
- Made `style set` transactional so an invalid profile cannot corrupt `title.json`.
- Hardened source replacement with pre-replace source-integrity verification, unique immutable archives and archived SHA/path history.
- Bound visual-QA video identity through Release/Remux and blocked input/output path aliasing during Remux.
- Narrowed OpenCode shell permissions so human-impacting SubtitleFlow commands no longer inherit a blanket allow.
- Added regression coverage for stale/tampered gate paths and a real FFmpeg/libass exact-font render verification.

## 0.2.0

- Generalized evidence intake beyond mandatory A/B/C/D.
- Added S self-contained subtitle role and `single` / `source-assisted` profiles.
- Added dynamic `auto`, `dub`, `bilingual`, and `full` workflow profiles.
- Added final `kiwi-collector-v1` ASS profile using 文泉驿微米黑 with Doraemon-derived grey/gold palette, 60/50 dialogue sizing, 2 px outline and event-level `\blur2`.
- Added Hybrid source preservation for complex events and common authored special styles even when they contain no complex override tag.
- Added font reference extraction from used ASS Styles and inline `\fn`, including `@` vertical-font normalization.
- Added local font directory/map resolution, optional FontTools metadata matching, SHA-256 font audit and production font gate.
- Added font attachment freeze to the release manifest.
- Added MKVToolNix font attachment command generation with modern font MIME types and output attachment verification.
- Added clean branch support throughout compile/QA/render/visual/release/remux state invalidation.
- Updated OpenCode agents, skills and commands for evidence-profile-aware operation plus `/subtitle/fonts` and `/subtitle/style`.
- Added v0.2 regression tests for single/source-assisted workflows, Hybrid preservation, final style, font audit and attachment safety.

## 0.1.0

- Initial A/B/C/D evidence workflow with TW and JP branches, human review, deterministic QA, visual QA, release freeze and MKV remux orchestration.

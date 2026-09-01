# Changelog

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

# Changelog

## 0.6.0

- Added fragment-level spoken-source accounting with stable source identities, explicit dispositions/reasons, final-reference integrity, ownership validation and deterministic event-level closure.
- Made unresolved fragments, partially presented source events, invalid refs, missing disposition reasons and substantive source-order violations block deterministic QA and Release.
- Upgraded bilingual reconciliation/coverage artifacts to schema 2 while retaining the legacy `source_split_decisions` adapter; older schema-1 artifacts remain readable but must rerun `prepare` before a new Release.
- Added first-class `source-accounting.json` release evidence and M01-derived minimal regressions for partial events, meaningful short lines, ownership leakage, repeated/parallel calls, unsupported source expansion and Canon boundaries.
- Added the independent `subtitleflow-producer` ChatGPT/Web Skill as a repository mirror without coupling Web production to the local runtime.

## 0.5.0

- Separated translation provenance, translation trust and editing policy; added centralized `preserve` / `proofread` / `retranslate` / assessment-first `auto` behavior with explicit user-policy priority.
- Extended Human Review and Change Records with structured primary/secondary evidence, authority domain, evidence grade, conflicts, confidence and final decision.
- Split alignment membership from JP bilingual reconciliation; added exact/split/merge/SOURCE_GAP/unresolved provenance, semantic-risk signals, fabrication guard and verified bilingual coverage.
- Added semantic-role classification so source style names are evidence rather than position authority; generic `Style2` remains dialogue and translator/fansub credits are excluded by default.
- Added separate clean/bilingual geometry and deterministic ZH-above-JA visual blocks for dialogue and songs, including the JA-multiline libass collision regression.
- Added structural/static-layout/FFmpeg-libass renderer QA layers, high-risk frame selection and fontselect-based fallback detection.
- Added first-class release audit artifacts for changes, source provenance, alignment/reconciliation, coverage, unresolved items, QA, layout and renderer evidence.
- Added real-world synthetic ASS/workfile specimens, regression coverage, OpenCode policy synchronization, style-profile drift protection and CI verification.
- Kept project/workfile schemas backward-readable; existing JP workfiles must rerun `prepare` to create reconciliation artifacts. Release Manifest remains schema 4 with optional audit metadata.

## 0.4.1

- Decoupled SubtitleFlow `project_id` from SRP `series_id`; titles now carry an explicit series identity with a legacy project-ID fallback.
- Project Research Libraries can store multiple series; compatibility is enforced at bind/resolve, and the resolver uses the title's effective series identity.
- Series identity changes stale dependent evidence, update resolver provenance to v2, and freeze series identity in release provenance.

## 0.4.0

- Added optional Subtitle Research Pack (`SRP/1.0`) support with bundled Draft 2020-12 schemas and strict offline validation; web/high-end-model research is an optional producer, not a SubtitleFlow dependency.
- Finalized SRP scope semantics with `series`, `title`, `series_branch`, and title-specific `branch`; deterministic SRP precedence is title+branch > series+branch > title > series.
- Added project-level immutable SRP import registry, ZIP/directory safety checks, deterministic pack digests, exact-digest title bindings, and import/bind separation.
- Added `research.mode = off | advisory | enforce`; new titles default to `off`, while v0.3 titles without a research object retain the legacy Markdown Research Gate.
- Added deterministic Effective Knowledge resolution across bound SRP packs and existing local project/title canon using scope-first/origin-second precedence.
- Extended local glossary records with optional semantic `key` and `enforcement`; SRP `locked` remains separate from deterministic `auto_replace`.
- Added Research context generation per active SubtitleFlow branch and integrated Effective Terms with terminology QA. Advisory SRP findings warn; enforcing locked/forbidden violations can fail QA.
- Added semantic/provenance research digests and precise stale propagation: semantic changes stale QA/semantic release evidence while provenance-only changes do not unnecessarily invalidate visual QA.
- Added explicit SRP Research approval evidence for `enforce` mode and compact SRP identity/digests to Release Manifest schema 4.
- Added `subflow research validate-pack/import/list/set-mode/map-branch/bind/unbind/resolve/diff/approve/status` and retained `research mark-complete` as a legacy compatibility path.
- Updated OpenCode orchestration so `/subtitle/run` and `/subtitle/research` respect optional research modes and never assume network access or a specific research producer.
- Added SRP examples, protocol/research documentation, security/regression coverage, and compatibility tests.

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

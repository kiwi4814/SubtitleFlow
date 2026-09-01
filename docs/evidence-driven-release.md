# Evidence-driven Subtitle Release System

SubtitleFlow separates three decisions that must never be inferred from each other:

- **Translation provenance**: how a translation originated (`official`, `professional`, `human-fansub`, `curated-human`, `machine`, `hybrid`, `transcript`, `unknown`).
- **Translation trust**: the current project's quality judgment (`high`, `medium`, `low`, `unknown`).
- **Editing policy**: how much semantic editing is permitted (`preserve`, `proofread`, `retranslate`, `auto`).

`official` and `human-fansub` are provenance labels, not trust scores.

## Editorial policies

`preserve` keeps a correct, natural existing translation. Evidence-backed canon, terminology, fact, semantic, number/unit and alignment corrections may be proposed; stylistic rewrites are blocked or human-gated.

`proofread` treats the existing translation as a seed. Source-language evidence controls meaning, while correct/natural target wording is retained. Mistranslation, omission, unsupported addition, negation, subject/object, names, terminology, register/voice, literal wording and segmentation may be corrected.

`retranslate` allows substantial rewrite and full translation from source authority while preserving the original target source and all provenance.

`auto` requires a structured Translation Quality Assessment before semantic editing. The assessment records semantic accuracy, terminology consistency, fluency, omission/mistranslation/alignment risk, confidence and a recommended policy. An explicit user policy always overrides the recommendation.

Existing projects that have no `editorial` configuration retain the v0.4 Minimal Editorial Intervention behavior and resolve to legacy `preserve`.

## Evidence and Human Review

Editing permission, evidence and review are separate layers. `ChangeRecord` and `ReviewCandidate` can carry primary evidence, secondary evidence, authority domain, evidence grade, source conflicts, confidence, proposal source, review status and final decision.

Evidence grades are authority/agreement labels rather than source-count scores:

- `A`: explicit primary evidence plus independent material support with no material conflict.
- `B+`: explicit primary evidence is sufficient, but secondary evidence is missing, weak or conflicting.
- `ALIGN`: alignment/pairing correction only; no new translation judgment.
- `SOURCE_GAP`: target material exists but no reliable source-language cue can be paired.
- `UNRESOLVED`: evidence is insufficient for a release decision.

Example: Japanese supports X, English supports Y and the old Chinese translation also says Y. Choosing X from explicit Japanese evidence is `B+` with both secondary conflicts recorded; it is not multi-source corroboration.

AI semantic changes continue to enter durable Human Review. A policy that permits a change does not imply automatic approval.

## Alignment and bilingual reconciliation

Alignment answers **which source/target cues belong together**. Reconciliation separately answers **how those groups become release events**.

- 1 target : 1 source -> `exact-pair`.
- 1 target : N source -> `source-merge`; all source cue IDs remain attached.
- N target : 1 source -> `source-split`; each target requires an explicit editor/AI-approved fragment inside the same original source cue, and the parent cue ID is retained.
- target without reliable source -> `SOURCE_GAP`; emit target only.
- source without target -> `unmatched-source`; semantic-risk review.
- unresolved N:M -> final bilingual compile is blocked.

A source gap is never repaired by translating target text back into the source language. Verified bilingual coverage reports exact pairs, source splits, source merges, source gaps, unresolved pairs and `fabricated`; a final release requires `fabricated = 0`.

For every sourced final bilingual pair, target and source events use identical Start/End timestamps.

## Semantic risk from alignment

Alignment emits review signals for N:M grouping, unmatched target/source, low confidence, anomalous text-length ratio, number conflicts, negation mismatch and weak speaker/role mismatch evidence. These are risk candidates, not automatic findings of translation error.

## Semantic roles

Source style names are evidence only. Generic names such as `Style2` do not imply `screen-text`, `\an8` or top placement. Events are first classified as dialogue, song, screen text, title, episode/next-episode title, annotation, staff credit, protected FX, document or prop. Position intent is modeled separately.

Translator notes, fansub URLs and production credits are excluded by default. Screen text/dialogue duplicates are QA candidates rather than automatic deletions.

## Deterministic layout

Clean and bilingual releases use different geometry. Clean target dialogue does not reserve an empty Japanese row.

A normal bilingual block is one visual unit:

```text
Chinese target
Japanese source
```

Generated events use explicit bottom-center positioning derived from profile resolution, font size/scale/outline, target/source visual row counts, bottom anchor and inter-language gap. A multi-line source therefore moves the target upward deterministically instead of relying on libass collision avoidance. The same contract applies to OP/ED/insert-song bilingual blocks.

Profile numbers are dimensionless layout intent where possible; no title-specific `if ja_rows == 2` pixel constants exist.

## QA layers

1. **Structural QA**: immutable source hashes, timing, empty text, unresolved reconciliation, source fabrication, pending review and related contracts.
2. **Static Layout QA**: width, overflow, row count, deterministic block geometry and predicted order/collision risk.
3. **Renderer QA**: when FFmpeg/libass and required fonts are available, render risk-selected frames and parse `fontselect` output for unexpected fallback. A synthetic profile-size canvas verifies typography/layout only.
4. **Video Visual Review**: when a real video is available, separately inspect face/object/sign occlusion, composition, safe area and visibility.

Static ASS Style/Margin values express intent. Renderer output is the observed visual authority.

## Release audit artifacts

A release can include:

- `change-audit.json`
- `change-audit.csv`
- `CHANGELOG_EVIDENCE.md`
- `source-provenance.json`
- `alignment-report.json`
- `bilingual-coverage.json`
- `unresolved.json`
- `qa-report.json`
- `layout-report.json`
- `render-summary.json`
- `previews/` from renderer/video QA

Raw A/B/C/D/S sources remain immutable and source hashes remain in the source manifest. Split, merge, correction, normalization and translation happen only in normalized/work/release layers.

## Compatibility

The project/workfile schema version is not bumped. New `Cue`, `BranchUnit`, `ChangeRecord` and `ReviewCandidate` fields are optional/defaulted so existing JSON continues to load. Existing JP workfiles must rerun `subflow prepare` before a new bilingual compile because reconciliation is now a first-class required artifact. Release Manifest remains schema version 4 for compatibility; audit artifact metadata is added as optional fields.

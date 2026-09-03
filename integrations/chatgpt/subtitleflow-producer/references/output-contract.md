# Portable Web release contract

Default archive:

```text
SubtitleFlow-<title>-<branch>.zip
├── subtitles/<release>.ass
├── reports/
│   ├── summary.md
│   ├── qa.json
│   ├── target-ledger.jsonl
│   ├── source-fragment-ledger.jsonl
│   ├── changes.jsonl
│   ├── punctuation-review.jsonl
│   ├── human-review.md            # required for OCR/dub-clean; may contain zero actionable items
│   └── canon-gaps.jsonl          # only when non-empty
├── renders/                      # only when actual render evidence exists
└── manifest.json
```

## Required accounting

Record input names/hashes, release intent, Canon/SRP provenance when used, baseline/accounted/unaccounted counts, source-fragment total/resolved/unresolved counts, invalid refs, source-order violations, provenance classes, unresolved semantic/punctuation/Canon issues, and output ASS SHA-256.

Also record:

- presentation mode (`clean`, `bilingual`, etc.) and expected geometry/anchor;
- actual geometry gate result, including cross-mode leakage such as monolingual y=430 remnants;
- `textual_uncertainty` separately from `audio_validation_deferred`;
- whether any render used exact registered font bytes or font fallback;
- independent convergence pass result and `new_major_semantic_or_provenance_issue` for Golden candidates;
- OCR/dub-clean human-review counts (`must_confirm`, `optional_listen`), plus whether exact dub-audio fidelity is `verified`, `pending-human-review`, or `waived`.

A source event with one final ref is not automatically fully presented. Fragment coverage is authoritative. Ledgers/reports, not ASS Effect text alone, are authoritative provenance.

## Human-review report

For OCR/dub-clean, `human-review.md` is a compact exception queue governed by `human-review-policy.md`, not a complete QA history. Default to 3-8 actionable items, re-filter queues above 10, show issue-confidence and repair-confidence separately, and include ambiguous dub divergence only when actual listening can distinguish adaptation from OCR/transcription error.

If `MUST_CONFIRM > 0`, do not describe the release as fully matched to Taiwan-dub speech.

## Change report

Classify material changes as `hard_semantic_fix`, `source_reconciliation_fix`, `canon_enforced`, `presentation_required`, `stylistic_optional`, or `overedit_revert`. Late-stage stylistic alternatives normally remain unchanged.

When clear same-cut Taiwan-dub audio proves the hard-sub/OCR wording does not match what the actor actually said, record the wording change as `dub_audio_override` with the audio/listening evidence provenance.

## Golden scope

Do not declare Golden in the same independent pass that discovers and fixes a major issue. After repair, run another independent pass. Golden requires zero new major semantic/provenance findings on that post-fix pass.

Record exact Golden scope and all deferred checks. Semantic/provenance/presentation Golden status does not prove exact-font, video, audio timing, MKV/remux, or archival-final status.

## QA truthfulness

Synthetic libass rendering may pass only for what was actually rendered. **A fallback-font render cannot be reported as exact-font PASS.** Exact-font validation requires the exact registered bytes. Full-video timing/occlusion requires video evidence; MKV attachment/remux requires actual MKVToolNix work.

## Deterministic packaging

Use stable ordering, UTF-8 JSON, portable paths, manifests, and hashes. Do not leak runtime-specific absolute paths into packaged reports.

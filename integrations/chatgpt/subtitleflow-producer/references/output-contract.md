# Portable Web release contract

Default archive:

```text
SubtitleFlow-<title>-<branch>.zip
├── subtitles/
│   └── <release>.ass
├── reports/
│   ├── summary.md
│   ├── qa.json
│   ├── target-ledger.jsonl
│   ├── source-fragment-ledger.jsonl
│   ├── changes.jsonl
│   ├── punctuation-review.jsonl
│   └── canon-gaps.jsonl          # only when non-empty
├── renders/                      # only when actual render evidence exists
│   └── *.png
└── manifest.json
```

## Required accounting

Record at minimum:

- input file names and SHA-256 values;
- title/series and release intent when known;
- compatible Canon/SRP provenance when used;
- baseline target unit count;
- accounted target unit count;
- unaccounted target count (must be zero for release-candidate/final);
- source spoken-fragment total/resolved/unresolved counts;
- source-event `presented_full` / `presented_partial` / resolved-nonpresented / unresolved counts when event-level summaries are emitted;
- invalid final-reference count;
- substantive source-order violation count;
- source provenance classes used (original/recovered/realigned/reconstructed);
- unresolved semantic/punctuation/Canon issues;
- output ASS SHA-256.

A source event with at least one final reference is not automatically fully presented. Fragment coverage is authoritative for spoken-source closure.

`final.ass` alone is not authoritative provenance. ASS `Effect` or comments may expose convenient provenance hints, but the ledgers/reports are authoritative.

## Change report

Classify material changes using:

- `hard_semantic_fix`
- `source_reconciliation_fix`
- `canon_enforced`
- `presentation_required`
- `stylistic_optional`
- `overedit_revert`

In conservative regression/audit mode, `stylistic_optional` should normally remain unchanged in the ASS and may be recorded only as a non-blocking observation.

## Golden scope

If a candidate reaches Golden convergence, record the exact Golden scope, such as `web-semantic-provenance`, plus all deferred checks. Do not imply that semantic/provenance Golden status proves exact-font, video-render, audio-timing, MKV/remux, or archival-final status.

## QA truthfulness

Separate Web checks from environment-dependent archival checks:

- semantic/accounting/Canon/punctuation/layout checks may pass in Web when actually performed;
- synthetic libass rendering may pass only if real FFmpeg/libass rendering occurred with known fonts;
- full-video timing/occlusion requires actual video evidence;
- exact font-byte audit requires actual font files;
- MKV attachment/remux requires actual MKVToolNix work.

Never label a deferred or unavailable check as passed.

## Deterministic packaging

Use stable ordering, UTF-8 JSON, normalized portable paths, and output hashes. Do not leak runtime-specific absolute paths into packaged reports.

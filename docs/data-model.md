# Data model

## `project.json`

Series/franchise defaults and `canon_version`.

## `title.json`

One movie/episode configuration: A/B/C/D roles, branch rules, alignment thresholds, ASS typography, quality gates, media path and release track names. See `configuration.md`.

## `source/manifest.json`

Immutable source provenance: role, internal path, original filename, SHA-256, size and import time. Replacement requires explicit `--replace` and archives the prior source.

## `normalized/<role>.json`

Parsed cues plus protection status. Normalization never changes source files.

## `work/tw.json`

A↔D groups. `raw_text` is D evidence; `normalized_text` contains deterministic conversion; `final_text` changes only through approved operations.

## `work/jp.json`

A↔B groups plus C Japanese evidence. `source_text` is C; `final_text` is the Chinese line used in the bilingual release.

## `review/candidates.json`

Every semantic proposal and its decision state. The human gate is intentionally separate from workfile generation.

## `qa/summary.json`

Deterministic QA result plus `input_snapshot`: hashes of workfiles, glossary/config/review inputs and compiled final ASS. Release rejects a stale snapshot.

## `qa/semantic-review.md`

Independent semantic audit evidence. It must be non-empty before the semantic-QA gate can pass.

## `qa/previews/<branch>/`

Actual FFmpeg/libass PNG renders. Their existence proves render success only; `visual_<branch>` is a separate approval stage.

## `release/release-manifest.json`

Frozen release provenance: source integrity, final ASS hashes, review counts, QA hash/input snapshot, canon version and gate status.

## `state.json`

Durable stage status. OpenCode reads this instead of relying on conversation history.

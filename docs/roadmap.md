# SubtitleFlow post-0.4.0 roadmap

SubtitleFlow 0.4.0 adds optional SRP/1.0 research integration while keeping the default workflow research-independent. The next work should continue to prioritize correctness and durable gates over architectural novelty.

## P0 — next production blockers

### 1. Durable Alignment Human Review Gate

Current low-confidence N:M alignment is surfaced as a QA warning but has no first-class durable approval ledger. Add an alignment-review artifact with evidence fingerprint and `Approve / Adjust / Defer` decisions. Release must require every `review_required` alignment to be resolved.

Do not merely turn low-confidence warnings into errors: that creates no legitimate unlock path.

### 2. Complete Timing QA against real media

Add deterministic checks for:

- cue range versus probed video duration;
- extremely short/long cue durations;
- overlap severity rather than one undifferentiated warning;
- beginning/middle/end drift sampling for multi-source aligned branches;
- evidence snapshot of the media identity used by timing QA.

Timing changes must stale downstream semantic/layout/render/release evidence as appropriate.

## P1 — workflow and evidence maturity

### 3. Engine-level `advance-to-next-gate`

Move the semantics of `/subtitle/run` into the deterministic engine. OpenCode/Codex/Claude Code/OMP should all ask the same planner: inspect repository state, execute only safe deterministic stages, and stop at the next human/AI judgment gate.

OpenCode remains an orchestration front end, not the owner of the state machine.

### 4. Approved semantic-change rebase/replay

When `prepare` regenerates a workfile:

- if a previously approved proposal's evidence fingerprint is unchanged, replay the approved result deterministically;
- if the relevant unit/evidence changed, mark the old decision `superseded` and require new Human Review;
- never silently discard or silently re-approve a semantic change.

0.3.0 already blocks Release if an approval is no longer materialized; this item improves recovery rather than safety.

### 5. Evidence Capabilities as an internal layer

Keep S/A/B/C/D as provenance roles and keep profiles as user-facing intent. Gradually introduce internal descriptors such as:

```yaml
capabilities:
  - timing
  - editable_text
  - source_semantics
  - dub_wording
```

Add authority separately from capability. Migrate stage-planning decisions only when a concrete limitation of role-based branching appears; do not rewrite the entire engine around capabilities pre-emptively.

### 6. Research/Canon provenance — completed in 0.4.0

SRP/1.0 now provides structured producer-neutral Sources/Evidence, series/title/series-branch/title-branch scope, Terms/Decisions, immutable pack identities, Effective Knowledge resolution, and semantic/provenance digests. Future work here should be additive rather than redesigning the core protocol: richer authority-domain tooling, canon-promotion UX, and the optional web Research Skill/request-bundle workflow.

## P1 — font/MKV archival hardening

### 7. Glyph coverage QA

Use FontTools `cmap` to prove that every code point used by each final ASS font role exists in the selected registered face. Report missing glyphs before render/release.

This is different from Name Table matching: a correct family can still lack a rare character.

### 8. Formal libass no-fallback evidence

Capture/parse libass `fontselect` diagnostics during visual rendering and bind requested family → selected font identity to render evidence. A successful render should not be treated as proof of correct selection merely because pixels were produced.

### 9. Output attachment SHA verification

After Remux, keep `mkvmerge -J` structural verification and optionally use `mkvextract` to re-extract every required output font and compare SHA-256 with the frozen Release Manifest. This gives byte-level end-to-end attachment proof.

## P2 — portability and maintenance

### 10. Cross-platform CI matrix

Run the deterministic suite on Python 3.11/3.12/3.13, plus Windows and Linux path/encoding coverage. Add macOS where external tool behavior warrants it. Real FFmpeg/MKVToolNix jobs can remain explicit integration jobs.

### 11. Coordinate-safe style scaling

Kiwi Collector values are authored for 1920×1080, while protected source effects may use another PlayRes. Add scaling only after `\pos`, `\move`, `\clip`, drawings and other coordinate-bearing tags can be transformed safely. Until then, preserve source PlayRes and rely on visual QA.

### 12. Reproducible build artifacts

Make wheel/source archive output reproducible with a stable build timestamp policy (for example `SOURCE_DATE_EPOCH`) and verify artifact hashes in CI. This is packaging provenance, not subtitle correctness, so it stays below the production gates above.

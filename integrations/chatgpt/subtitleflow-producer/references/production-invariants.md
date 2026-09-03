# Production invariants

These invariants are mandatory and outrank cosmetic symmetry or convenient QA numbers.

1. **Narrative Integrity** — target narrative information may be preserved, edited, split, merged, or explicitly folded, but never silently disappear. Every baseline target unit must be accounted for.
2. **Source Authenticity** — keep source-original, source-recovered, source-realigned, and auxiliary reconstructed language provenance distinct.
3. **Semantic Pair Integrity** — timing overlap never substitutes for semantic/speaker/source-fragment compatibility.
4. **Deterministic Release Style** — once semantic content is decided, Canon aliases, typography, layout constraints, and character-form normalization are deterministic.
5. **No Silent Failure** — never hide source gaps, drop target cues, fake 1:1 pairing, relabel reconstruction as source, or mark an unperformed check passed.
6. **Evidence Is Not Presentation** — the evidence model may be N:M, fragmented, parallel, or target-only even when the final viewing layout is visually 1:1.
7. **Readability Beats Forced Geometry** — severe horizontal compression or stacked multi-line dialogue is not an acceptable substitute for correct segmentation/reconciliation. Revisit semantics before shrinking text; when a coarse source cue contains multiple semantic clauses, preserve the source evidence unit but project sequential one-line bilingual events. Inferred internal timing must be marked as presentation inference, never source timing.
8. **Punctuation Carries Meaning** — punctuation/delivery is part of semantic editing before typography normalization, not a final regex cleanup.
9. **Minimal Edit** — `KEEP` is the default when the target is semantically correct, substantively complete, source-owned correctly, and compliant with the pinned Canon. Do not rewrite merely because another wording is stylistically preferable.

## Target accounting states

A baseline target unit must end in one explicit state such as:

- `preserved`
- `edited`
- `split`
- `merged`
- `folded-redundant`
- `removed-approved-non-dialogue`
- `unresolved`

`unaccounted` is never acceptable for a release candidate.

## Source-fragment accounting

Account spoken source content at semantic-fragment/span level when a source event contains multiple independently meaningful pieces. A source event having any `final_ref` does **not** prove full coverage.

Each spoken fragment must resolve to an explicit disposition such as:

- `presented`
- `merged_presented`
- `folded_with_reason`
- `parallel_reaction_omitted_with_reason`
- `nonverbal`
- `unresolved`

Event-level status must be derived from fragment coverage (`presented_full`, `presented_partial`, `resolved_nonpresented`, or `unresolved`). `presented_partial` is not closure.

Removing a speaker tag must never erase adjacent spoken content by accident. Meaningful short spoken fragments must not be treated as expendable merely because they are short.

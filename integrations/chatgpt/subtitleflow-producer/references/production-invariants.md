# Production invariants

These invariants are mandatory and outrank cosmetic symmetry or convenient QA numbers.

1. **Narrative Integrity** — narrative information may be preserved, edited, split, merged, or explicitly folded, but never silently disappear.
2. **Source Authenticity** — keep source-original, source-recovered, source-realigned, dub-authentic, and auxiliary reconstructed provenance distinct.
3. **Semantic Pair Integrity** — timing overlap never substitutes for semantic/speaker/source-fragment compatibility.
4. **Deterministic Release Style** — once semantics are decided, Canon aliases, typography, presentation mode, layout constraints, and character-form normalization are deterministic.
5. **No Silent Failure** — never hide source gaps, drop cues, fake 1:1 pairing, relabel reconstruction as source, or mark an unperformed check passed.
6. **Evidence Is Not Presentation** — evidence may be N:M, fragmented, parallel, dub-only, or target-only even when final viewing layout is visually 1:1.
7. **Readability Beats Forced Geometry** — severe compression or stacked multi-line dialogue is not a substitute for correct reconciliation.
8. **Punctuation Carries Meaning** — punctuation/delivery is semantic editing, not a final regex cleanup.
9. **Minimal Edit** — `KEEP` is the default when text is semantically correct, substantively complete, source-owned correctly, and Canon-compliant.
10. **Lossless Component Parsing** — structural parsing must never consume valid semantic characters. A leading `一` or other Han character is content unless explicit syntax proves otherwise. Round-trip source spans after component extraction.
11. **Truthful Split State** — label a unit `split` only when it actually yields multiple independently meaningful components/presentation units. One component plus one final ref is not a split.
12. **Dub Authority Boundary** — on a Taiwan-dub cleanup branch, actual same-cut dub speech is the highest authority for exact spoken wording/delivery; reliable same-dub hard-sub/transcript follows; Japanese-track wording is challenge/context evidence only. A real dub adaptation must not be normalized back to Japanese.
13. **Human Review Is Bounded** — unresolved cases go to the user only when listening materially improves exact recovery. Do not export a broad uncertainty dump; apply the review budget and confidence rules in `human-review-policy.md`.
14. **Uncertainty Scope** — separate textual uncertainty from unavailable audio/video validation. Do not keep readable source-authentic wording textually unresolved solely because media verification is deferred.

## Target accounting states

A baseline target unit must end in an explicit state such as `preserved`, `edited`, `split`, `merged`, `folded-redundant`, `removed-approved-non-dialogue`, or `unresolved`. `unaccounted` is never acceptable for a release candidate.

## Source-fragment accounting

Account spoken source content at semantic-fragment/span level when one event contains multiple meaningful pieces. A source event having any `final_ref` does not prove full coverage.

Resolve each spoken fragment to an explicit disposition such as `presented`, `merged_presented`, `folded_with_reason`, `parallel_reaction_omitted_with_reason`, `nonverbal`, or `unresolved`. Derive event status from fragment coverage; `presented_partial` is not closure.

Removing speaker metadata must never erase adjacent speech. Meaningful short fragments are not expendable merely because they are short.

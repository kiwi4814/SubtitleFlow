---
name: Subtitle Alignment
description: Align cross-source evidence, emit semantic-risk signals, then reconcile source/target groups for release.
---

Run `subflow prepare`; never match by line number. A/S timing remains authoritative for video coordinates.

Alignment answers only **which cues belong together**. It supports 1:1, 1:N, N:1, N:M and unmatched groups and emits review signals for grouping anomalies, low confidence, unusual length, number/negation conflicts and weak speaker/role mismatch evidence. These signals are not proof that a translation is wrong.

For JP, reconciliation is a separate contract:
- 1 target + 1 source -> `exact-pair`.
- 1 target + N source -> `source-merge`, preserving every source cue id.
- N target + 1 source -> `source-split` only after an explicit semantic split decision inside that original source cue. Never concatenate adjacent source cues and arbitrarily resplit them.
- target with no reliable source -> `SOURCE_GAP`; keep ZH and emit no fake JA.
- source with no target -> `unmatched-source`; route to semantic-risk review.
- unresolved N:M blocks final JP compile.

Final sourced bilingual pairs use identical ZH/JA timestamps. `SOURCE_GAP` is a truthful coverage loss, not a reason to back-translate Japanese.

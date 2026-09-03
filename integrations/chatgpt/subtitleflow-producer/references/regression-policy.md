# Regression, anti-overedit, and Golden policy

Use this policy for late-stage candidate review, independent regression audit, or any request to decide whether a subtitle release has converged.

## Minimal Edit invariant

Default to `KEEP` unless there is a material reason to change the candidate. Material reasons are `hard_semantic_fix`, `source_reconciliation_fix`, `canon_enforced`, or `presentation_required`. `stylistic_optional` defaults to KEEP in regression mode.

Classify every material diff as `hard_semantic_fix`, `source_reconciliation_fix`, `canon_enforced`, `presentation_required`, `stylistic_optional`, or `overedit_revert`. After broad edits, review the diff in reverse and revert changes whose pre-edit text was already correct, complete, correctly owned, and Canon-compliant.

## Fragment-level source closure

A source event is not fully accounted merely because it has one final reference. Decompose independently meaningful spans and derive event-level status from fragment coverage. `presented_partial` is not closure. Never classify a meaningful short spoken line as expendable merely because it is short.

## Duplicate short-fragment matching

Text equality alone is never sufficient for repeated fragments such as `うん`, `あっ`, or `ドラえもん！`. Use temporal neighborhood, monotonic order, speaker, adjacent fragments, candidate distance, and simultaneous/parallel structure. Preserve separate source identities for simultaneous identical calls.

## Plausible-Han OCR challenge

Late OCR cleanup must scan errors that still look like normal Chinese. Challenge, in context:

- deictics/direction: `这/那`, `来/去`, `上/下`, `前/后`, `左/右`;
- polarity/negation and causal operators;
- numbers, counters, names, and high-information nouns;
- sentence-final particles such as `吗/嘛/吧/呢` that can reverse the speech act;
- short replies such as `是/好/对` whose punctuation may have been hallucinated as ellipsis;
- duplicated valid Han and shape-confusable forms;
- plausible words that contradict both scene logic and independent challenge evidence.

Do not mechanically substitute the Japanese line. On a dub branch, corroborating Japanese/other Chinese evidence can establish that OCR is wrong, but genuine dub divergence must remain intact.

## Dub divergence challenge

For Taiwan-dub hard-sub cleanup, use this authority order for wording: reliable dub audio/transcript/hard-sub evidence first; Japanese and Japanese-audio Chinese as semantic/context challenge evidence. A missing or different Japanese line does not by itself authorize deletion or rewrite of readable dub text.

## Independent re-audit mode

Start from immutable source evidence plus the current candidate ASS. Previous PASS labels, ledger dispositions, source ownership, punctuation judgments, and Canon judgments are candidate evidence only.

A strong independent pass should include:

1. full-title source-to-candidate semantic challenge, not only previously flagged rows;
2. reverse scan of source/OCR units not directly presented, to detect silent speech deletion;
3. direct-diff/anti-overedit review of material source-to-final changes;
4. failure-class scans discovered in prior passes, including component prefix loss, false split, profile-geometry leakage, plausible-Han OCR, and stale uncertainty effects;
5. deterministic accounting/reference/layout gates.

## Golden convergence protocol

Lifecycle:

`production -> release-candidate -> independent regression audit`

If the audit finds a new major semantic/provenance defect:

`fix -> new release-candidate -> independent post-fix audit`

Do **not** declare Golden on the same pass that discovered and fixed a major issue. Declare `Golden Regression` only when a subsequent genuinely independent pass finds:

`new_major_semantic_or_provenance_issue = 0`

Golden is scope-specific. Keep exact-font, real-video, audio timing, MKV/remux, and archival freeze deferred unless separately proven. A fallback-font render does not satisfy exact-font scope.

After Golden convergence, stop open-ended polishing unless a material defect, authoritative Canon change, new evidence, or requested profile change reopens the artifact.

## Public regression evidence

Prefer minimal/synthetic fixtures, hashes/manifests, expected deterministic outputs, and dispositions rather than committing a full copyrighted Golden ASS. Keep complete title-level Golden subtitles in the user's private Evidence Library/archive when appropriate.

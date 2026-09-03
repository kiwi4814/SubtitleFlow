# Regression, anti-overedit, and Golden policy

Use this policy for late-stage candidate review, independent regression audit, or any request to decide whether a subtitle release has converged.

## Minimal Edit invariant

Default to `KEEP` unless there is a material reason to change the candidate.

Material reasons are:

- `hard_semantic_fix` — clear mistranslation, polarity/subject/object/causality/entity error, or materially wrong speech act;
- `source_reconciliation_fix` — substantive omission, wrong source-fragment ownership, speaker leakage, sequence/cascade error, or strict bilingual pairing defect;
- `canon_enforced` — violation of the pinned Canon/SRP rule that is actually authoritative for the active release profile;
- `presentation_required` — a wording/segmentation change strictly required to satisfy the active presentation contract after reconciliation has been rechecked.

Do not change a semantically correct, source-accounted, Canon-compliant line merely because another wording sounds smoother.

In regression/audit mode, `stylistic_optional` defaults to `KEEP`.

## Change classification and over-edit review

Classify every material diff as one of:

- `hard_semantic_fix`
- `source_reconciliation_fix`
- `canon_enforced`
- `presentation_required`
- `stylistic_optional`
- `overedit_revert`

After any broad model-led edit pass, audit the diff in reverse: for each change, ask whether the pre-edit target already satisfied semantic correctness, substantive coverage, source ownership, and pinned Canon.

If a late-stage candidate suddenly produces a large diff without a newly discovered release-wide failure class, treat that as an anomaly and run the over-edit review before accepting the changes. Do not normalize the candidate merely to make it sound more like the current model's preferred prose.

## Fragment-level source closure

A source event is not fully accounted merely because it has one final reference.

Decompose spoken content into semantic fragments/spans when an event contains multiple independently accountable pieces. Track each fragment to one explicit disposition such as:

- `presented`
- `merged_presented`
- `folded_with_reason`
- `parallel_reaction_omitted_with_reason`
- `nonverbal`
- `unresolved`

Derive event-level states from fragment coverage:

- `presented_full`
- `presented_partial`
- `resolved_nonpresented`
- `unresolved`

`presented_partial` is not closure. A source event with `A B C` and a final reference covering only `A B` must keep `C` unresolved until separately presented or explicitly disposed with reason.

Never classify a meaningful short spoken line as expendable merely because it is short.

## Duplicate short-fragment matching

Text equality alone is never sufficient to bind a short or repeated source fragment such as `うん`, `あっ`, `ふ～ん`, or `ドラえもん！`.

Resolve candidates using, at minimum:

- temporal neighborhood;
- monotonic source order;
- speaker when known;
- adjacent source fragments;
- candidate distance;
- simultaneous/parallel presentation structure.

When identical calls occur simultaneously or near-simultaneously from different source events/speakers, preserve separate source identities and bind each fragment to the correct final presentation. Never collapse them because the text is identical.

## Conditional source challenge

For Japanese-audio releases, the pinned primary Japanese subtitle is the normal semantic authority, but not an infallible oracle.

Trigger an independent source challenge only for high-risk or disputed cases, for example:

- primary source wording conflicts with scene/context or grammar;
- two credible Japanese sources materially disagree;
- the candidate change would overturn a high-confidence established translation;
- a user explicitly challenges the transcription/version;
- the primary source appears truncated, corrupted, or version-specific.

Use independent evidence such as alternate Japanese subtitles, JA-CC, manga, or official Japanese material to challenge the primary source. Do not force web research for ordinary lines, and do not use simple majority voting as the decision rule.

## Independent re-audit mode

An independent regression audit must start from immutable source evidence plus the current candidate ASS.

Previous-pass items such as semantic PASS, ledger disposition, source ownership, punctuation judgment, or Canon decision are candidate evidence only, not inherited truth. Re-evaluate the relevant claims independently.

For late-stage conservative regression audit, permit new text changes only for:

1. clear mistranslation;
2. substantive omission;
3. source ownership / speaker / strict bilingual alignment error;
4. pinned Canon/SRP violation.

Everything else defaults to `KEEP` or an explicit non-blocking note.

## Golden convergence protocol

Use this lifecycle:

`production -> release-candidate -> independent regression audit`

If the independent audit finds a new major semantic/provenance issue:

`fix -> new release-candidate -> new independent audit`

Declare `Golden Regression` only when a genuinely independent pass finds:

`new_major_semantic_or_provenance_issue = 0`

Golden is scope-specific. Record what is actually Golden, for example `semantic/provenance`, while leaving exact-font, libass/video, audio timing, MKV/remux, or archival freeze explicitly deferred unless separately proven.

After Golden convergence, stop open-ended language polishing. Reopen the Golden text only for a material new defect, authoritative Canon change, new evidence that challenges a prior decision, or an explicitly requested release-profile change.

## Public regression evidence

Do not require a public repository to contain a full copyrighted Golden ASS. Prefer:

- minimal snippets needed to reproduce one failure class;
- synthetic fixtures;
- hashes/manifests for private Golden artifacts;
- expected deterministic outputs and dispositions.

Keep the complete title-level Golden subtitle in the user's private Evidence Library / collector archive when appropriate.

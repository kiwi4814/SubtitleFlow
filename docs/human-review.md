# Human review

AI semantic changes are proposals, not edits.

The default is **KEEP**. Automatic edits are limited to project-approved deterministic transformations such as known terminology rules and explicitly configured script conversion.

Semantic review is required for changes involving mistranslation claims, omission, negation, subject/object, numbers, causality/modality, relationship/register, plot-critical terminology, or meaningful dub wording.

For `clean` without C, do not label a proposal as source mistranslation because no source evidence exists. Limit proposals to language/OCR/consistency defects unless other evidence is supplied.

## Durable proposal evidence

Proposal JSON written to `review/proposals/` is itself repository evidence. `subflow release` blocks while any unimported proposal file remains. On import, the original proposal file is archived under `review/proposals/_imported/` with its SHA-256 recorded on the candidate, so later review can trace which model artifact created the decision item.

## Stale protection

A candidate is accepted only while all relevant evidence still matches:

- `original_text` still equals the unit's current `final_text`;
- unit timing/source-cue/raw-normalized evidence still matches its proposal-time fingerprint;
- the source manifest still matches;
- project/title canon JSON still matches;
- title research context/sources still match when present.

Approve/reject/custom decisions are durable. An accepted wording change creates a workfile `ChangeRecord` linked to the candidate and invalidates downstream compile/QA/semantic/render/visual/release/remux state. Structural QA additionally verifies that every approved/custom candidate is still materialized in the current workfile; regenerating a workfile cannot silently erase an approved semantic change and still produce a valid Release.

## Known rebase decision

The current engine **detects and blocks** an approval that is no longer materialized after a new `prepare`, but it does not yet auto-replay approvals. The recommended future behavior is: replay an accepted edit only when its unit/evidence fingerprint is unchanged; otherwise mark the old candidate `superseded` and require a new Human Review decision. That behavior is intentionally not inferred silently because it changes project workflow semantics.

## Policy permission is not review approval

The centralized Editorial Policy matrix answers whether an AI/editor may propose a change type. Evidence answers why the proposal is justified. Human Review independently decides whether a substantive semantic proposal is accepted. `proofread` therefore permits broader detection without auto-approving low-confidence semantic changes, and `official`/`human-fansub` provenance never bypasses review. Approved changes copy their structured evidence, conflicts, grade, confidence, proposal source and final decision into the workfile Change Record so Release can answer exactly what changed.

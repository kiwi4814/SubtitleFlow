---
name: subtitleflow-producer
description: Produce, polish, align, QA, independently re-audit, and package collector-grade ASS subtitles directly in ChatGPT/Web from uploaded subtitle files, using strong-model semantic judgment plus deterministic audits. Use for Japanese-audio Simplified-Chinese subtitles, Taiwan-dub Simplified-Chinese subtitles, Japanese-Chinese bilingual ASS, subtitle repair, OCR/dub cleanup, alignment/reconciliation fixes, Canon-aware terminology enforcement, late-stage regression audit, Golden convergence, punctuation/notation repair, and collector release candidates. Consume existing Canon/SRP/evidence selectively from GitHub when useful, but do not depend on cloning or running the local SubtitleFlow repository.
---

# SubtitleFlow Producer

Operate as an independent Web subtitle producer. Do not require the local SubtitleFlow runtime, repository clone, CLI, OpenCode, or Core state machine to finish a Web production.

Use strong-model judgment for language and semantic decisions. Use bundled scripts only for deterministic parsing, accounting, risk discovery, and acceptance gates; never let a script mechanically decide a mistranslation, source-fragment ownership, speech act, Canon creation, or ambiguous punctuation.

## Production model

1. Inspect uploaded subtitle files/archives and infer their practical roles.
2. Preserve immutable input bytes and build an internal evidence model.
3. When long-term knowledge is useful, selectively read the compatible Canon/SRP/evidence snapshot from GitHub; never clone the whole repository for production.
4. Build accountable target/source-fragment ledgers before editing.
5. Reconcile N:M evidence semantically. Treat timing overlap as evidence, never proof of one sentence.
6. Perform model-led semantic editing and punctuation/delivery judgment under the Minimal Edit invariant.
7. Project the evidence model into the requested presentation profile.
8. Run deterministic audits and model-led high-risk QA. Iterate back to reconciliation/editing when QA exposes semantic or layout problems.
9. For late-stage candidates, run anti-overedit review and, when requested, an independent regression re-audit that does not inherit previous PASS decisions as truth.
10. Package the ASS plus provenance/accounting/QA reports. Call it `Golden Regression` only after an independent audit finds zero new major semantic/provenance issues; otherwise use the accurate lower completion state.

Read `references/workflow.md` for the full flow and feedback loops.
Read `references/production-invariants.md` before any production.
Read `references/regression-policy.md` for Minimal Edit, fragment-level closure, duplicate short-fragment matching, independent re-audit, conditional source challenge, anti-overedit, and Golden convergence.
Read `references/punctuation-policy.md` whenever Chinese/Japanese punctuation, source notation, quotation, speaker labels, ellipsis, or delivery is involved.
Read `references/layout-policy.md` whenever line width, wrapping, `fscx`, bilingual spacing, sequential presentation splits, or synthetic-canvas rendering is involved.
Read `references/evidence-policy.md` when Canon/SRP or conflicting source claims matter.
Read `references/output-contract.md` before packaging.
Read `references/m01-regression-fixtures.md` when validating alignment, punctuation, notation, Canon, accounting, over-edit, duplicate matching, or layout regressions.
Read `references/github-layout.md` only when retrieving long-term repository evidence.

## Minimal Edit rule

Default to `KEEP` when the candidate is:

- semantically correct;
- substantively complete;
- correctly owned by the source fragment/speaker;
- compliant with the pinned Canon/SRP for the active release profile.

Do not rewrite merely because another wording sounds smoother. In conservative regression/audit mode, permit new text edits only for clear mistranslation, substantive omission, source ownership/strict bilingual-alignment error, or pinned Canon violation. Treat stylistic alternatives as non-blocking notes, not automatic edits.

## Strong-model responsibility

The model must personally decide cases that require language understanding, including:

- N:M semantic boundaries and source-fragment ownership;
- mistranslation vs stylistic difference;
- speaker/reaction vs same-sentence merge;
- whether a short spoken fragment is meaningful content or legitimately omittable with reason;
- whether an ellipsis, question mark, exclamation mark, or `？！` matches the actual speech act;
- whether source notation is delivery metadata, literal quotation, lyrics, accessibility annotation, or spoken text;
- whether a target-only line is real narrative content, redundant expansion, or unsupported translation;
- whether a long line should be resegmented/retranslated instead of compressed;
- whether a disputed/high-risk primary Japanese source should trigger independent source challenge.

Do not convert these judgments into blind regex rules. A deterministic script may flag `中文…… / 日文！`; the model must decide whether that mismatch is wrong in context.

## Source accounting discipline

A source event having any `final_ref` does not prove the event is fully presented. When a source event contains multiple accountable semantic fragments, track every fragment/span separately and derive event-level closure from fragment coverage.

Do not bind repeated short fragments by exact text alone. Use timing neighborhood, source monotonicity, speaker, adjacent fragments, candidate distance, and simultaneous/parallel structure. Identical simultaneous calls may require separate source refs even when their text is the same.

For Japanese-audio bilingual collector production, do not fabricate Japanese merely to keep visible 1:1. `JA_AUX_RECONSTRUCTED` is disabled by default unless the user explicitly chooses a viewer-assist profile that permits reconstructed language.

## Canon boundary

Consume Canon; do not create Canon.

- Enforce pinned locked/authoritative values for the active release profile.
- Respect accepted aliases according to their actual scope/policy.
- If a long-tail term is absent or unresolved, keep a semantically valid existing target rather than proactively normalizing it from external popularity; record a Canon gap when durable research is needed.
- Route new durable Canon decisions to `subtitle-canon-research`.

## Deterministic responsibility

Use scripts/checks for facts that should not consume model judgment:

- ASS parsing, event/timing/style inventory;
- target accounting, fragment-ledger integrity, final-reference validity and hashes;
- half/full-width punctuation normalization after semantic punctuation is decided;
- balanced/unclassified notation detection;
- duplicate/unaccounted ledger entries;
- forbidden Canon aliases once a release profile has selected them;
- explicit line breaks, `q2`, geometry and `fscx` bounds;
- packaging manifests and checksums.

Do not let deterministic bookkeeping infer semantic closure from event-level reference existence alone.

## User feedback rule

Treat a concrete user correction as evidence of a bug class, not merely an isolated edit. After fixing the cited line, scan the entire release for the same failure class. Examples:

- “这里还是技安” -> scan all forbidden/obsolete aliases.
- “日文粘在一起了” -> scan parallel-speaker/source-merge contamination.
- “这里怎么是省略号” -> scan seed-ellipsis inheritance and semantic punctuation conflicts.
- “这里的《》是什么” -> classify and scan all source-notation leakage.
- “这里行距/字体被压得很怪” -> audit the full layout class and send severe overflow back to reconciliation.
- “是不是改太多了” -> switch to conservative regression mode and run reverse over-edit review on the diff.
- “账本是不是假闭账” -> audit fragment-level coverage, partial source events, invalid refs, repeated short-fragment binding and source-order integrity.

## Truthfulness and convergence

- Never fabricate source-language evidence.
- Never silently delete target narrative content or spoken source fragments.
- Never claim source closure when only part of a source event is covered.
- Never inherit a previous audit's PASS labels as truth during an explicitly independent re-audit.
- Never claim full-video visual approval, exact-font validation, MKV attachment verification, or Remux unless those checks were actually performed in the available environment.
- Record Golden scope precisely. `web-semantic-provenance` Golden does not imply exact-font/video/audio/remux Golden.
- After Golden convergence, stop open-ended language polishing unless a material new defect, authoritative Canon change, new challenge evidence, or requested release-profile change reopens the artifact.

## Final response

Return the primary ASS and a portable ZIP when files were produced. Summarize material semantic decisions, provenance/accounting status, Canon gaps, anti-overedit findings, passed Web gates, Golden scope when applicable, and deferred media/font/remux checks. Keep internal stage jargon out of the normal response unless diagnostic detail is useful.

---
name: subtitleflow-producer
description: Produce, polish, align, QA, independently re-audit, and package collector-grade ASS subtitles directly in ChatGPT/Web from uploaded subtitle files, using strong-model semantic judgment plus deterministic audits. Use for Japanese-audio Simplified-Chinese subtitles, Taiwan-dub source-form Traditional/Simplified Chinese subtitles, Japanese-Chinese bilingual ASS, subtitle repair, OCR/dub cleanup, alignment/reconciliation fixes, Canon-aware terminology enforcement, late-stage regression audit, Golden convergence, punctuation/notation repair, and collector release candidates. Consume existing Canon/SRP/evidence selectively from GitHub when useful, but do not depend on cloning or running the local SubtitleFlow repository.
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
7. Select the requested presentation mode, then project the evidence model into that mode's deterministic geometry. Never inherit bilingual geometry into a monolingual release.
8. Run deterministic audits and model-led high-risk QA. Iterate back to reconciliation/editing when QA exposes semantic or layout problems.
9. For late-stage candidates, run anti-overedit review and, when requested, an independent regression re-audit that does not inherit previous PASS decisions as truth.
10. If the independent pass finds a material bug, fix the candidate and run another genuinely independent post-fix pass. Golden requires zero new major semantic/provenance findings on that post-fix pass.
11. Package the ASS plus provenance/accounting/QA reports. Call it `Golden Regression` only for the exact scope actually proven.

Read `references/workflow.md` for the full flow and feedback loops.
Read `references/production-invariants.md` before any production.
Read `references/regression-policy.md` for Minimal Edit, fragment-level closure, duplicate short-fragment matching, plausible-Han OCR challenge, independent re-audit, conditional source challenge, anti-overedit, and Golden convergence.
Read `references/punctuation-policy.md` whenever Chinese/Japanese punctuation, source notation, quotation, speaker labels, ellipsis, dub OCR particles, short replies, or delivery is involved.
Read `references/layout-policy.md` whenever line width, wrapping, `fscx`, monolingual/bilingual geometry, sequential presentation splits, or synthetic-canvas rendering is involved.
Read `references/character-form-policy.md` whenever Chinese OCR cleanup may require Traditional/Simplified source-form preservation or dual character-form deliverables.
Read `references/evidence-policy.md` when Canon/SRP or conflicting source claims matter.
Read `references/output-contract.md` before packaging.
Read `references/m01-regression-fixtures.md` when validating alignment, punctuation, notation, Canon, accounting, over-edit, duplicate matching, OCR cleanup, dub divergence, or layout regressions.
Read `references/github-layout.md` only when retrieving long-term repository evidence.

## Minimal Edit rule

Default to `KEEP` when the candidate is semantically correct, substantively complete, correctly source-owned, and compliant with pinned Canon/SRP for the active release profile. Do not rewrite merely because another wording sounds smoother.

In conservative regression/audit mode, permit new text edits only for clear mistranslation, substantive omission, source ownership/alignment error, pinned Canon violation, or a presentation change strictly required after semantic reconciliation. Treat stylistic alternatives as non-blocking notes.

## Strong-model responsibility

The model must personally decide cases that require language understanding, including:

- N:M semantic boundaries and source-fragment ownership;
- mistranslation vs stylistic difference;
- speaker/reaction vs same-sentence merge;
- whether a short spoken fragment is meaningful content or legitimately omittable with reason;
- whether an ellipsis, question mark, exclamation mark, `？！`, sentence-final particle, or short reply matches the actual speech act;
- whether source notation is delivery metadata, literal quotation, lyrics, accessibility annotation, or spoken text;
- whether a target-only/dub-only line is real narrative content, redundant expansion, or unsupported text;
- whether a long line should be resegmented/retranslated instead of compressed;
- whether a disputed/high-risk primary source should trigger independent source challenge.

Do not convert these judgments into blind regex rules. Deterministic checks may flag risk; the model decides semantics.

## Taiwan-dub OCR cleanup

For a Taiwan-dub hard-sub OCR cleanup branch, produce character forms under `references/character-form-policy.md`: clean and freeze the source-form master first; generate Simplified only as a deterministic derivative when the retained OCR is Traditional. If the retained OCR is already Simplified, emit only the Simplified master. Never independently rewrite the Simplified derivative.

For wording/evidence:

- credible Taiwan hard-sub OCR/dub transcript/audio is **wording authority**;
- Japanese and Japanese-audio Chinese are **challenge/context evidence**, not replacement wording authority;
- a Japanese mismatch can expose OCR corruption, but it can also be a genuine dub divergence;
- absence of a Japanese counterpart is not sufficient reason to delete readable Taiwan-dub hard-sub text;
- preserve Taiwan-specific wording and terminology unless the user explicitly requests another release profile;
- distinguish `textual_uncertainty` from `audio_validation_deferred`: readable source-authentic wording should not remain textually unresolved merely because matching dub audio is unavailable.
- treat the cleaned source-form OCR master as authoritative final wording; character-form projections inherit wording, punctuation, timing, segmentation, layout, and provenance without independent edits.

During late-stage OCR QA, challenge plausible-looking Han errors, not only garbage. Scan semantic oppositions and confusables such as `这/那`, `来/去`, `上/下`, `前/后`, negation, quantities, names, sentence-final `吗/嘛/吧`, short affirmative responses, duplicated valid Han, and punctuation that changes speech act.

## Source accounting discipline

A source event having any `final_ref` does not prove the event is fully presented. Track independently meaningful fragments/spans and derive event-level closure from fragment coverage.

Do not bind repeated short fragments by exact text alone. Use timing neighborhood, source monotonicity, speaker, adjacent fragments, candidate distance, and simultaneous/parallel structure.

Component extraction must be lossless with respect to semantic text. Never consume a valid leading character such as `一` as a list/component marker unless explicit source syntax proves it is structural. After component projection, round-trip accountable text against the source span.

Use `split` only when the source unit actually projects into two or more independently meaningful components/presentation units. One meaningful component with one final ref is not a split.

For Japanese-audio bilingual collector production, do not fabricate Japanese merely to keep visible 1:1. `JA_AUX_RECONSTRUCTED` is disabled by default unless the user explicitly chooses a viewer-assist profile that permits reconstructed language.

## Canon boundary

Consume Canon; do not create Canon. Enforce pinned locked/authoritative values for the active release profile, respect alias scope, and keep semantically valid unfrozen long-tail terms rather than normalizing them from popularity. Route durable new decisions to `subtitle-canon-research`.

## Deterministic responsibility

Use scripts/checks for ASS inventory, accounting, final-reference validity, character-form normalization after semantic decisions, notation risk discovery, forbidden Canon aliases, explicit line breaks, `q2`, presentation-mode geometry, `fscx` bounds, stale uncertainty effects, manifests, and checksums.

Do not let deterministic bookkeeping infer semantic closure from event-level reference existence alone.

## User feedback rule

Treat a concrete user correction as evidence of a bug class, not merely an isolated edit. After fixing the cited line, scan the entire release for the same failure class. Examples:

- “这里还是技安” -> scan all forbidden/obsolete aliases.
- “日文粘在一起了” -> scan parallel-speaker/source-merge contamination.
- “这里怎么是省略号” -> scan seed-ellipsis inheritance and semantic punctuation conflicts.
- “这里的《》是什么” -> classify and scan all source-notation leakage.
- “单语中文字幕是不是应该再往下一点” -> verify presentation mode first, then audit the full release for bilingual-geometry leakage.
- “这个一怎么没了” -> scan component extraction for semantic-prefix loss and false `split` states.
- “这句日文不一样” on a dub branch -> challenge OCR but do not overwrite source-authentic dub divergence.
- “是不是改太多了” -> switch to conservative regression mode and run reverse over-edit review on the diff.
- “账本是不是假闭账” -> audit fragment coverage, partial source events, invalid refs, repeated short-fragment binding and source-order integrity.

## Truthfulness and convergence

- Never fabricate source-language or dub evidence.
- Never silently delete target narrative content or spoken source fragments.
- Never claim source closure when only part of a source event is covered.
- Never inherit a previous audit's PASS labels as truth during an explicitly independent re-audit.
- Never claim exact-font validation from a fallback-font render. Record the actual selected/fallback font and defer exact-font status when the registered bytes are unavailable.
- Never claim full-video visual approval, audio-exact timing, MKV attachment verification, or Remux unless actually performed.
- Record Golden scope precisely. Web semantic/provenance Golden does not imply exact-font/video/audio/remux Golden.
- After Golden convergence, stop open-ended language polishing unless material new evidence, a pinned Canon change, a real defect, or a requested profile change reopens the artifact.

## Final response

Return the primary ASS and a portable ZIP when files were produced. Summarize material semantic decisions, provenance/accounting status, anti-overedit findings, passed Web gates, Golden scope when applicable, and deferred media/font/remux checks. Keep internal stage jargon out of the normal response unless diagnostic detail is useful.

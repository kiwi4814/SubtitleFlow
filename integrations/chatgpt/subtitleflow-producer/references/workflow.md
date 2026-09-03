# Web production workflow

## 1. Intake and immutable evidence

Inventory uploaded files without changing source bytes. Detect format, language, timing usefulness, likely audio relationship, duplicates, ASS styles/override tags, and source notation patterns.

Infer the requested viewing release from natural language. Do not require S/A/B/C/D terminology from the user.

Determine the review mode:

- normal production/editing;
- conservative late-stage regression audit;
- independent Golden-convergence audit.

Regression/audit mode uses the stricter Minimal Edit policy in `regression-policy.md`.

## 2. Selective long-term evidence

When the title/series needs established terminology or research, selectively read the compatible Canon/SRP/evidence snapshot from GitHub. Do not clone the repository and do not require local SubtitleFlow execution.

Evidence priority:

1. explicit user instruction for this release;
2. compatible title/branch Canon decision;
3. compatible series/branch Canon decision;
4. source-language semantics / relevant dub wording for the requested audio;
5. other credible localized evidence;
6. existing translation as an editing seed;
7. model inference, clearly marked and never promoted to permanent Canon automatically.

Use conditional source challenge only for disputed/high-risk cases under `evidence-policy.md` and `regression-policy.md`.

## 3. Build ledgers before editing

Create a stable target ledger for every baseline target unit and a source-fragment ledger for spoken source evidence. Preserve speaker/delivery/notation metadata separately from presentation text.

Do not close a source event merely because it has one final reference. When one source event contains multiple semantic pieces, create accountable fragment/spans and derive the event status from their coverage.

Do not let source cleanup discard spoken fragments. Do not declare SOURCE_GAP after a single local miss.

For short/repeated fragments, text equality alone is insufficient. Bind using timing neighborhood, monotonic order, speaker, adjacent fragments, candidate distance, and parallel structure. Preserve separate source identity for simultaneous identical calls.

## 4. Reconciliation

Align by timing plus semantics, speaker, sequence, and fragment consumption. Support N:M relations and fragments. Different speakers or simultaneous reactions default against automatic merge unless semantics proves they belong together.

Before declaring a gap, inspect nearby source cues, unconsumed prefix/suffix fragments, N-target:1-source possibilities, speaker overlap, translation-seed expansion, and redundant target information.

Classify gaps/redundancies explicitly rather than using one generic bucket.

For Japanese-audio bilingual production, do **not** invent auxiliary Japanese merely to preserve visual 1:1. `JA_AUX_RECONSTRUCTED` is disabled by default and may be used only when the user explicitly requests a viewer-assist profile that permits reconstructed language; it must remain clearly non-source provenance.

## 5. Strong-model semantic editing

Use the model to review the whole production, prioritizing high-risk units but not skipping normal units blindly. For Japanese-audio Chinese, Japanese semantics is authoritative and the existing Chinese subtitle is a translation seed rather than target truth.

Judge mistranslation, omission, proper nouns, sentence boundaries, source-fragment ownership, calls/reactions, and semantic punctuation in context.

Apply the Minimal Edit invariant: keep a correct, substantively complete, correctly owned, Canon-compliant target rather than rewriting it for style. In conservative regression mode, new text edits are limited to clear mistranslation, substantive omission, source ownership/alignment error, or pinned Canon violation.

Classify accepted diffs under `regression-policy.md`. After a broad or unexpectedly large late-stage diff, run the reverse over-edit audit before accepting it.

## 6. Canon and release-style projection

Apply selected release-profile Canon after semantic wording is decided, then audit forbidden aliases. Do not normalize an unfrozen long-tail term just because another external translation is common; record a Canon gap when durable research is needed.

Project the semantic model into deterministic layout/typography. Evidence N:M relations do not need to become presentation N:M; visual 1:1 is a presentation choice only.

For punctuation and notation, follow `punctuation-policy.md`. For line width, `fscx`, sequential single-line splitting, inferred presentation timing, and canvas rendering, follow `layout-policy.md`.

## 7. QA with feedback loops

Run deterministic inventory/accounting/typography/layout audits, then perform model-led review of flagged semantic risks.

Allow these explicit loops:

- semantic QA -> reconciliation;
- coverage/accounting QA -> reconciliation;
- punctuation QA -> semantic editing/reconciliation;
- severe layout overflow -> reconciliation or retranslation before scaling;
- Canon QA -> semantic editing/normalization;
- user feedback -> corresponding bug-class full-release scan.

Do not solve a severe long-line problem by silently shrinking text or by introducing a stacked two-line dialogue. Treat `fscx < 85` or any ordinary dialogue `\N` as a hard review condition. First re-check reconciliation and wording; if the source cue still contains multiple semantic clauses, project it as sequential one-line bilingual events under `layout-policy.md`. When the source lacks an internal timestamp, mark the presentation boundary inferred and keep exact audio timing deferred.

## 8. Independent re-audit and convergence

When the user requests independent regression audit, do not inherit previous PASS labels, ledger dispositions, source ownership, punctuation judgments, or Canon judgments as truth. Re-audit immutable source evidence against the candidate ASS; prior reports are supporting evidence only.

Use `references/regression-policy.md` for the Golden convergence loop. A candidate may become Golden only after an independent pass reports zero new major semantic/provenance issues.

Once Golden, stop open-ended linguistic polishing unless material new evidence, a pinned Canon change, a real defect, or a requested profile change reopens the artifact.

## 9. Completion states

Use `draft`, `candidate`, `reviewed`, `release-candidate`, `final`, and `Golden Regression` accurately. `final` requires every mandatory Web semantic/accounting/presentation gate to pass. Golden scope must be explicit. Missing real-video/font/remux capabilities must be reported as deferred, not passed.

# Web production workflow

## 1. Intake and immutable evidence

Inventory uploads without changing source bytes. Detect format, language, timing usefulness, likely audio relationship, duplicates, ASS styles/override tags, source notation, and whether the requested output is monolingual, bilingual, dub-clean, or another release profile.

Choose normal production, conservative regression audit, or independent Golden-convergence audit.

## 2. Selective long-term evidence

Read only compatible Canon/SRP/evidence when needed. Do not require a clone or local Core runtime. Evidence priority is: explicit user release instruction; compatible title/series Canon; authoritative source/dub evidence for the requested audio; other credible localized evidence; translation seed; model inference.

## 3. Build ledgers before editing

Create stable target and source-fragment ledgers. Preserve speaker/delivery/notation metadata separately. Do not close an event merely because it has one final ref. Bind repeated short fragments with timing/order/speaker/adjacency evidence.

Component parsing must round-trip semantic source spans and must not consume a valid leading Han character as a structural marker without explicit syntax.

## 4. Reconciliation

Align by timing plus semantics, speaker, sequence, and fragment consumption. Support N:M and dub-only source content. Before declaring a gap, inspect nearby cues, prefix/suffix fragments, multi-target:one-source possibilities, speaker overlap, translation-seed expansion, and redundancy.

For Japanese-audio bilingual production, do not invent auxiliary Japanese unless the user explicitly selects a viewer-assist reconstruction profile.

## 5. Strong-model semantic editing

Review the whole production. For Japanese-audio Chinese, Japanese semantics is authoritative and Chinese is a seed. For Taiwan-dub OCR cleanup, credible dub hard-sub/transcript/audio wording is authoritative and Japanese is challenge/context evidence.

Apply Minimal Edit. In OCR branches, explicitly challenge plausible-Han failures: direction/deixis, negation, quantities, names, sentence-final particles, short replies, duplicated Han, and punctuation that changes speech act.

## 6. Canon and release-style projection

Apply active release Canon after semantic wording is decided. Then select presentation mode and project deterministic layout. **Mode selection precedes coordinates.** For the bundled 640x480 reference profile, clean monolingual Chinese uses y=453; bilingual Chinese/Japanese use y=430/y=460.

## 7. QA with feedback loops

Run deterministic inventory/accounting/typography/layout audits, then model-led semantic risk review. Route semantic/accounting/punctuation/layout/Canon failures back to the appropriate editing stage. Treat any user-found defect as a full-release bug class.

For dub OCR cleanup, reverse-scan removed/non-presented OCR units for plausible spoken content and compare material OCR-to-final diffs for over-edit or accidental Japan-track normalization.

Do not rescue severe long lines with `fscx < 85` or ordinary dialogue `\\N`.

## 8. Independent post-fix convergence

An independent audit must not inherit prior PASS decisions as truth. Re-audit immutable source evidence against the current candidate.

If a major issue is found, fix it, promote a new RC, and run a **second independent post-fix pass**. Golden requires that later pass to report zero new major semantic/provenance findings. Do not declare Golden in the same pass that discovered a major issue.

## 9. Render evidence and truthfulness

Synthetic libass rendering can support presentation QA. Record the actual selected font. If the registered font bytes are unavailable and libass falls back, label the render supplemental/fallback and keep exact-font validation deferred.

## 10. Completion states

Use `draft`, `candidate`, `reviewed`, `release-candidate`, `final`, and `Golden Regression` accurately. Record exact Golden scope and separate `textual_uncertainty` from `audio_validation_deferred`. Missing real-video/font/remux capabilities are deferred, not passed.

---
name: Subtitle Release QA
description: Run structural, static-layout, renderer, real-video, font and audit gates for a traceable subtitle release.
---

Release order:
1. Pending Human Review must be zero; approved semantic edits must still match their frozen context.
2. Compile only reconciled workfiles. `SOURCE_GAP` may emit ZH without JA; unresolved N:M blocks JP compile.
3. Structural QA checks timing, empty text, undefined/missing source relations, source fabrication and pending review.
4. Static Layout QA predicts wide/overflow/row-count/bilingual-order/collision risks from profile geometry. It is not final visual authority.
5. Font audit resolves ASS family -> registry -> exact font file/attachment.
6. Renderer QA, when FFmpeg/libass and required fonts are available, renders risk-selected frames. A synthetic 1920x1080/profile canvas verifies typography/layout only and must explicitly state that scene occlusion was not verified. Parse `fontselect`; unexpected dialogue fallback is a high-severity failure.
7. If real video exists and visual QA is required, inspect real frames for faces, objects, signs, composition, safe area and visibility. Rendering alone is not Human Visual Approval.
8. `subflow release` freezes final ASS plus Change Audit, source provenance, alignment/reconciliation, verified bilingual coverage, unresolved issues, QA/layout/render reports and hashes.
9. `subflow remux` attaches the already audited font files. Do not report Remux success without successful `mkvmerge` execution and output verification.

A real 98.6% verified bilingual coverage with `fabricated=0` is valid; a fabricated 100% is never valid.

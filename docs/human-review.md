# Human review

AI semantic changes are proposals, not edits.

The default is KEEP. Automatic edits are limited to project-approved deterministic transformations such as known terminology rules and explicitly configured script conversion.

Semantic review is required for changes involving mistranslation claims, omission, negation, subject/object, numbers, causality/modality, relationship/register, plot-critical terminology, or meaningful dub wording.

For `clean` without C, do not label a proposal as source mistranslation because no source evidence exists. Limit proposals to language/OCR/consistency defects unless other evidence is supplied.

A proposal is stale-safe: its `original_text` must still equal the current unit `final_text` at import and decision time. Approve/reject/custom decisions are durable. Any accepted text change invalidates downstream compile/QA/semantic/visual/release state.

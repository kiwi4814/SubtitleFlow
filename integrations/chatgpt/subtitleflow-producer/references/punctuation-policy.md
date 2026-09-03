# Punctuation and source-notation policy

## Principle

Separate source notation, semantic punctuation/delivery, and release typography. Never infer speech act solely from the target seed's punctuation.

## Japanese-audio Chinese authority

For Japanese-audio releases: `Japanese source semantics/delivery > Chinese translation-seed punctuation`. Do not require terminal-character equality across languages. Calls, exclamatory questions, and emotional fade-outs require contextual judgment.

## Taiwan-dub OCR punctuation

On Taiwan-dub hard-sub OCR cleanup, the OCR/dub source is wording authority, but punctuation and sentence-final particles themselves may be OCR errors. Challenge cases where normal-looking Han changes speech act:

- `吗` vs `嘛` can turn an assertion/insistence into a question;
- a short affirmative `是！` / `好！` can be hallucinated as `是……` / `好……`;
- deictic or lexical OCR corruption can make punctuation appear locally plausible while the sentence is semantically wrong.

Use nearby dub OCR frames plus independent Japanese/other Chinese context to challenge the reading. Do not rewrite genuine dub divergence merely to match Japanese punctuation.

## Ellipsis

Use `……` only for supported hesitation, unfinished speech, trailing voice, interruption, or deliberate lingering pause. Do not preserve `...` or an OCR-generated ellipsis merely because it appears in the seed/source text when stronger context establishes an emphatic short response.

## Release typography for Simplified Chinese

After semantic punctuation is approved:

- ASCII `?` -> `？`
- ASCII `!` -> `！`
- valid ASCII `...`/single `…` ellipsis -> `……`
- ordinary comma/full stop -> active release-profile rule
- preserve meaningful `？`, `！`, `？！`, `……`

Typography normalization must never create or remove a semantic punctuation category.

## Source notation classification

Classify speaker labels, continuation arrows, narration brackets, off-screen markers, lyric marks, quotations, and accessibility annotations before hiding them. Notation can span cues; maintain cross-cue state when needed. Removing speaker metadata must never remove adjacent spoken fragments.

## Semantic punctuation QA

Flag and judge in context: ellipsis vs emphatic source, question vs assertion/exclamation, missing terminal force, inherited seed ellipsis, punctuation copied across split/merge boundaries, dub OCR `吗/嘛` particle ambiguity, and short affirmative replies with suspicious trailing ellipsis.

## Hard acceptance gates

For Simplified-Chinese release text after semantic approval: ASCII `?`, ASCII `!`, ASCII `...`, unbalanced/unclassified non-presentation notation, unaccounted spoken fragments, unresolved high-risk punctuation conflicts, and unresolved seed-ellipsis conflicts must all be zero.

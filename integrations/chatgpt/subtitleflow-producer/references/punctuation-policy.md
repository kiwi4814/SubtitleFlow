# Punctuation and source-notation policy

## Principle

Separate three layers:

1. **Source notation** — markers supplied by the source subtitle: speaker labels, continuation arrows, narration brackets, off-screen markers, lyric marks, quotations, accessibility annotations.
2. **Semantic punctuation / delivery** — the actual speech act: statement, question, exclamation, command, vocative/call, hesitation, trailing-off, interruption, exclamatory question, narration/inner voice.
3. **Release typography** — the exact characters shown to the viewer after semantics are decided.

Never infer layer 2 solely from the target seed's existing punctuation.

## Japanese-audio Chinese authority

For Japanese-audio releases:

`Japanese source semantics/delivery > Chinese translation-seed punctuation`.

This does not mean Chinese and Japanese terminal characters must match mechanically. Translate the speech act naturally.

Examples:

- `ピー助 ピー助！` should not inherit a seed `皮助 皮助...` as `皮助 皮助……`; review as a call/exclamation.
- `何だって！` may naturally become `你说什么？！` rather than mechanically `你说什么！`.
- `さようなら！` may still be `再见……` if scene/context clearly supports a fading, emotional farewell; mismatch itself is a review signal, not an automatic error.

## Ellipsis

Use Chinese `……` only for supported hesitation, unfinished speech, trailing voice, interruption, or deliberate lingering pause. Do not preserve `...` merely because the translation seed contains it.

When a seed ellipsis conflicts with an emphatic/calling Japanese source, require model review.

## Release typography for Simplified Chinese

After semantic punctuation is approved:

- ASCII `?` -> `？`
- ASCII `!` -> `！`
- ASCII `...`/`…` used as an ellipsis -> `……`
- ordinary comma `，` -> release-profile rule (Kiwi collector default: space)
- ordinary full stop `。` -> release-profile rule (Kiwi collector default: omit at terminal dialogue position)
- preserve meaningful `？`, `！`, `？！`, `……`

Typography normalization must never create or remove a semantic punctuation category.

## Source notation classification

Do not delete unfamiliar markers blindly. Parse/classify first.

Typical patterns observed in Japanese broadcast subtitles may include:

- `(人物)` / `（人物）` — speaker metadata; remove from presentation only after preserving speaker identity.
- `→` — continuation/layout marker; usually metadata, not spoken text.
- `《...》` — may encode narration/inner voice in a specific source. Confirm from repeated contextual usage before stripping. Preserve `delivery` metadata even if brackets are hidden in presentation.
- `≪` or similar — may mark off-screen/distant/secondary audio; classify from the source's own repeated usage.
- `♪` — music/lyric or sung delivery marker; do not silently flatten without knowing whether sung content must remain visible.
- `「...」` / `｢...｣` — often literal quotation/read text; preserve when semantically part of the spoken/read content.

Notation can span multiple cues. Maintain open/close state across cues; per-line regex alone is insufficient.

## Speaker cleanup must not delete speech

For `(一同)あっ？ ピー助 ピー助！`:

- `(一同)` is metadata.
- `あっ？` and `ピー助 ピー助！` are spoken fragments.

Removing `(一同)` must not silently remove `あっ？`.

## Semantic punctuation QA

Flag, then let the model judge in context:

- target ellipsis vs emphatic source (`……` / `！`);
- question vs exclamation (`？` / `！`);
- target no terminal punctuation vs source emphatic/question when speech act may have been lost;
- inherited seed ellipsis without source/context support;
- punctuation copied across a split/merge boundary without re-evaluating sentence completion.

Do **not** require literal terminal-punctuation equality across languages.

## Hard acceptance gates

For Simplified-Chinese release text after typography normalization:

- ASCII question marks in target dialogue: `0`
- ASCII exclamation marks in target dialogue: `0`
- ASCII three-dot ellipses in target dialogue: `0`
- unbalanced classified source-notation spans: `0`
- unclassified source-notation leaks designated as non-presentation metadata: `0`
- unaccounted spoken source fragments: `0`
- unresolved high-risk semantic punctuation conflicts: `0`
- unresolved seed-ellipsis conflicts: `0`

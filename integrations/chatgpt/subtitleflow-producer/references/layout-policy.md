# Collector layout policy

Use strong-model judgment to decide semantic segmentation first. Layout may project those decisions; it must not conceal a bad reconciliation.

## Default bilingual presentation — single-line only

For the bundled 640x480 collector reference profile:

- Chinese: exactly one line, `SF-ZH`, `\\an2\\pos(320,430)`.
- Japanese: exactly one line, `SF-JA`, `\\an2\\pos(320,460)`.
- Use `\\q2` so the renderer does not silently rewrap a line.
- Prefer `fscx=100`. Minor compression is acceptable only after semantic/source-fragment review.
- `fscx < 85` is not an acceptable automatic fix.
- Ordinary collector output must contain no explicit `\\N` in Chinese or Japanese dialogue.

The user's collector preference is sequential single-line presentation, not stacked multi-line presentation. Do not introduce a two-line Japanese layout as a rescue mechanism.

## Long-line resolution order

When either language is too wide, investigate in this order:

1. source-fragment over-assembly or false merge;
2. target/source sentence boundary and speaker ownership;
3. unnecessary translation verbosity or removable source formatting spaces;
4. safe one-line compression at or above 85;
5. split the semantic presentation into two or more sequential bilingual events.

A visually long line can expose a reconciliation defect. Never treat geometry as isolated from evidence.

## Sequential presentation splitting

When a genuine source cue contains multiple semantic clauses but must remain one source evidence unit, keep the evidence unit intact and split only the presentation projection.

Each projected segment must:

- contain exactly one Chinese line and one Japanese line;
- remain inside the original source cue time span;
- split at a real semantic/prosodic boundary chosen by strong-model judgment;
- preserve source order and fragment ownership;
- avoid duplicate or missing words across segments;
- keep ordinary geometry (`ZH y=430`, `JA y=460`);
- avoid `\\N` entirely.

If the source provides exact sub-cue timestamps, use them. If it provides only one coarse cue with no internal timing boundary, infer the split conservatively from semantic clause structure and reading burden. Mark every affected presentation event `PRESENTATION_SPLIT_INFERRED` and treat audio-precise timing as deferred until real media is available.

An inferred split must never extend source material outside the original cue interval and must never be represented as source-authored timing.

Do not infer a split if it would create an unreadably short segment. If a semantic split would require a segment below the active minimum-duration/readability policy, stop and report a timing-review requirement rather than restoring a two-line cue or forcing `fscx < 85`.

## Evidence vs presentation

A source cue such as:

```text
A clause\\NB clause
```

may remain one source/evidence unit while the release contains:

```text
[t0, ts]  ZH-A / JA-A
[ts, t1]  ZH-B / JA-B
```

This is a presentation split, not evidence falsification. Record the relationship in provenance/ledger output.

## Renderer evidence without movie media

When no MKV/video is available, an FFmpeg/libass synthetic canvas rendered with the exact registered font files is valid evidence for:

- font selection/fallback diagnostics;
- line count and explicit wrapping;
- horizontal compression;
- Chinese/Japanese spacing;
- clipping and canvas bounds;
- punctuation/source-notation presentation.

It is not evidence for scene occlusion or exact timing against spoken audio. Inferred presentation-split boundaries remain timing-deferred until real media is available.

# Collector layout policy

Use strong-model judgment to decide semantic segmentation first. Layout may project those decisions; it must not conceal a bad reconciliation.

## Select presentation mode before geometry

Presentation geometry is mode-specific. Select `clean` / monolingual, `bilingual`, song, or another explicit profile before emitting ASS positions. Never reuse a bilingual language-row anchor merely because the same `SF-ZH` style is used.

For the bundled 640x480 collector reference profile:

- **clean / monolingual Simplified Chinese:** exactly one line, `SF-ZH`, `\\an2\\pos(320,453)`; this is `round(480 * 0.944)`.
- **bilingual Chinese:** exactly one line, `SF-ZH`, `\\an2\\pos(320,430)`.
- **bilingual Japanese:** exactly one line, `SF-JA`, `\\an2\\pos(320,460)`.
- use `\\q2` so the renderer does not silently rewrap a line;
- prefer `fscx=100`; `fscx < 85` is not an acceptable automatic fix;
- ordinary collector output must contain no explicit `\\N` dialogue line break.

A monolingual release with every Chinese cue still at y=430 is a presentation-profile projection failure, not a harmless stylistic choice. Audit the whole release for mode leakage whenever one cue is found at the wrong anchor.

## Long-line resolution order

When a line is too wide, investigate in this order:

1. source-fragment over-assembly or false merge;
2. sentence boundary and speaker ownership;
3. unnecessary translation verbosity or removable formatting spaces;
4. safe one-line compression at or above 85;
5. split the semantic presentation into sequential events when the active profile permits it.

A visually long line can expose a reconciliation defect. Never treat geometry as isolated from evidence.

## Sequential bilingual presentation splitting

When a genuine source cue contains multiple semantic clauses but must remain one source evidence unit, keep the evidence unit intact and split only the presentation projection.

Each projected segment must contain exactly one Chinese and one Japanese line, stay inside the original source time span, split at a real semantic/prosodic boundary, preserve source order/ownership, avoid duplicate or missing words, keep `ZH y=430` / `JA y=460`, and avoid `\\N`.

Use exact sub-cue timestamps when available. Otherwise infer the boundary conservatively, mark `PRESENTATION_SPLIT_INFERRED`, and defer audio-precise timing. Never represent inferred timing as source-authored timing.

Do not infer a split that creates an unreadably short segment. Report a timing-review requirement rather than restoring two-line dialogue or forcing `fscx < 85`.

## Evidence vs presentation

Evidence units may be N:M while presentation is visually 1:1 or sequential. Record presentation splits and inferred boundaries in provenance rather than altering source evidence identity.

## Renderer evidence without movie media

Synthetic FFmpeg/libass rendering can validate line count, wrapping, spacing, compression, clipping, bounds, punctuation, and font selection/fallback diagnostics.

**Exact-font PASS requires the exact registered font bytes.** If libass falls back because the registered font is unavailable, the render may be retained as supplemental stress evidence but must be labeled fallback-font evidence and cannot certify exact glyph metrics.

Synthetic rendering is never evidence for real-scene occlusion or exact timing against spoken audio.

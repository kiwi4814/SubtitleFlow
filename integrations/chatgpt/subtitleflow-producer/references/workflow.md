# Production workflow

## Intake

1. Inventory every uploaded subtitle/archive member without changing source bytes.
2. Detect format, language, likely audio relationship, timing usefulness, ASS complexity, and duplicates.
3. Identify the title/series from filenames, metadata, user text, or GitHub catalog.
4. Infer the requested output branch from natural language.

Internal concepts may map to SubtitleFlow S/A/B/C/D, but keep that mapping out of the normal user experience.

## Evidence resolution

Use this priority:

1. User's explicit instruction for this production.
2. Bound title-specific Canon/SRP decision.
3. Series Canon/SRP decision.
4. Source-language subtitle/audio-semantic evidence.
5. Relevant official/localized subtitle or dub evidence.
6. Existing fan translation as an editing seed.
7. Inference, clearly marked and never promoted to permanent Canon automatically.

Do not use line number as the primary alignment method. Align by timing and N:M relationships, with text/role signals as secondary evidence.

ASS override tags such as `\\pos`, `\\move`, `\\clip`, karaoke tags, or styling must remain preserved in immutable source/template handling. For semantic alignment, derive a plain-text view by stripping override tags; protection from editing does not make a cue unusable as evidence.

## Alignment and editing

- Keep immutable source files unchanged.
- Prefer KEEP under Minimal Editorial Intervention.
- Correct mistranslation, omission, mistranscribed proper nouns, obsolete terminology, grammar, punctuation, and unnatural Chinese only when supported.
- Preserve authored complex ASS events through hybrid compilation unless the user explicitly requests redesign.
- Never back-translate Chinese to invent missing Japanese evidence.
- For bilingual output, source gaps must remain explicit rather than fabricated.

## QA and rendering

Run, where supported: source integrity, parse/structure validation, unresolved decision checks, timing sanity, terminology/Canon QA, bilingual source coverage/fabrication checks, ASS compile parse checks, font resolution, FFmpeg/libass renderer QA, and visual inspection of representative/high-risk frames.

If full video is available, add scene-aware visual/timing checks. Otherwise label synthetic rendering accurately.

## Blocker policy

Do not stop for recoverable encoding, ASS tags interfering with semantic comparison, format differences, deterministic Canon terminology, or harmless warnings.

Stop only for unresolved credible evidence conflicts, materially ambiguous release intent, genuinely absent evidence that would require fabrication, a required material semantic approval, or an explicit release requirement the runtime cannot satisfy.

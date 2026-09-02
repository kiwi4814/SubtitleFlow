# Production workflow

## Intake

1. Inventory every uploaded subtitle/archive member without changing source bytes.
2. Detect format, language, likely audio relationship, timing usefulness, ASS complexity, and duplicates.
3. Identify the title/series from filenames, metadata, user text, or GitHub catalog.
4. Infer the requested output branch from natural language.
5. Materialize the classified inputs as a Portable Job. Internal roles may map to S/A/B/C/D, but keep that mapping out of the normal user experience.

## Evidence resolution

Use this priority:

1. User's explicit instruction for this production.
2. Bound title-specific Canon/SRP decision.
3. Series Canon/SRP decision.
4. Source-language subtitle/audio-semantic evidence.
5. Relevant official/localized subtitle or dub evidence.
6. Existing translation as an editing seed.
7. Inference, clearly marked and never promoted to permanent Canon automatically.

When repository evidence is enabled, select a compatible immutable SRP snapshot, pin its repository path/ref, and let the Portable Job runner validate/import/bind/resolve it before semantic editing. Do not silently follow a moving “latest” pack, relax series compatibility, or claim a pack was used unless the Research Gate actually passed.

Do not use line number as the primary alignment method. Align by timing and N:M relationships, with text/role signals as secondary evidence.

ASS override tags such as `\\pos`, `\\move`, `\\clip`, karaoke tags, or styling must remain preserved in immutable source/template handling. Protection from editing does not make spoken Dialogue unusable as semantic evidence. Conversely, non-verbal accessibility captions and Ruby/furigana annotations may remain visually preserved while being excluded from language alignment.

## Semantic editing

1. Run deterministic prepare through the Portable Job runner.
2. Confirm the planner's next safe action is semantic editing.
3. Export/consume the branch Semantic Packet. Treat its `packet_input_sha256`, workfile SHA, source manifest SHA, and Effective Research digest as the semantic-pass identity.
4. Review every packet unit, while prioritizing critical/high-risk units rather than skipping normal units.
5. Return only material changes as structured proposals. KEEP is implicit; do not emit cosmetic no-op proposals.
6. Preserve `unit_id`, `original_text`, evidence rationale, confidence, and any Canon/source conflicts.
7. Import proposals through SubtitleFlow's packet-bound proposal importer. The importer must reject a stale Semantic Packet identity before candidates enter Human Review.
8. Stop at Human Review whenever material candidates are pending. Never approve model proposals silently.
9. Present a concise review summary that makes the proposed material changes and evidence visible. A user response such as “按推荐处理” after that summary is an explicit Human Review decision for the displayed recommended set; a generic earlier preference for automation is not.
10. Apply approved/custom decisions through SubtitleFlow's existing Human Review API so the workfile receives durable `ChangeRecord` provenance. Rejected candidates must leave subtitle text unchanged.
11. After all pending candidates are decided, ask the planner for the next safe action. The old Semantic Packet is stale after an approved/custom text mutation and must not be reused for later proposals.

CI/regression fixtures may make controlled review decisions inside an isolated temporary workspace to prove this roundtrip. Such fixture decisions are test evidence only and must never be represented as production user approval.

Editing rules:

- Keep immutable source files unchanged.
- Prefer KEEP under Minimal Editorial Intervention.
- Correct mistranslation, omission, mistranscribed proper nouns, obsolete terminology, grammar, punctuation, and unnatural Chinese only when supported.
- Preserve authored complex ASS events through hybrid compilation unless the user explicitly requests redesign.
- Never back-translate Chinese to invent missing Japanese evidence.
- For bilingual output, source gaps must remain explicit rather than fabricated.

## QA and rendering

After Human Review is complete, continue only through the next-safe-action planner and existing Core gates. Run, where supported: source integrity, parse/structure validation, unresolved decision checks, timing sanity, terminology/Canon QA, bilingual source coverage/fabrication checks, ASS compile parse checks, font resolution, FFmpeg/libass renderer QA, and visual inspection of representative/high-risk frames.

If full video is available, add scene-aware visual/timing checks. Otherwise label synthetic rendering accurately. Never claim full-video, exact-font, or MKV/remux verification when the runtime lacks those capabilities.

## Blocker policy

Do not stop for recoverable encoding, ASS tags interfering with semantic comparison, format differences, deterministic Canon terminology, or harmless warnings.

Stop only for unresolved credible evidence conflicts, materially ambiguous release intent, genuinely absent evidence that would require fabrication, a required material semantic approval, stale semantic-packet/proposal identity, or an explicit release requirement the runtime cannot satisfy.

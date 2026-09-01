# SubtitleFlow repository contract

## Goal

SubtitleFlow is a generic evidence-driven subtitle production system. Never force missing evidence into fake roles.

## Evidence roles and authority

- **S**: self-contained target subtitle. S owns both timing and editable target text.
- **A**: Timing Master for multi-source workflows.
- **B**: existing Chinese translation seed for Japanese audio.
- **C**: source-language/Japanese semantic evidence.
- **D**: Taiwan-dub transcript/wording evidence.

Profiles: `single`, `source-assisted`, `dub`, `bilingual`, `full`, `auto`.

Authority rules:

- single: S timing/text are authoritative; without C do not claim source-faithful translation verification.
- source-assisted: S timing is authoritative; C may correct semantics only through human review.
- TW: actual Taiwan audio > D wording; A supplies time coordinates.
- JP: C controls source meaning, B is only the Chinese editing seed, A supplies time coordinates.

## Non-negotiable rules

1. `projects/*/titles/*/source/` is immutable evidence. Never edit it in place.
2. Verify source hashes before dependent work.
3. Never align by line number; use N:M-aware alignment only when multiple evidence tracks require it.
4. Use Minimal Editorial Intervention. Default decision is KEEP.
5. Project-approved deterministic normalization may auto-apply and must be logged.
6. Any semantic wording change from AI must enter the durable human-review queue before altering `final_text`.
7. AI must not rewrite raw ASS/SSA/SRT files wholesale.
8. Complex ASS events and configured special source styles are protected by default.
9. Styling is a compile-time profile; translation/timing decisions do not live in Style lines.
10. Kiwi Collector v1 generated dialogue uses canonical ASS family `WenQuanYi Micro Hei`, the fixed grey/gold palette, and `\blur2`.
11. Never acquire or redistribute font binaries. User-provided/local-licensed fonts may be imported into ignored `fonts/local/`, but source releases must exclude all font binaries.
12. Production release requires every actually referenced font to be resolved unless the user explicitly relaxes the font gate.
13. The default font registry freezes canonical family/file/SHA identities. A font audit records local path, Name Table metadata, MIME, size and SHA-256; frozen font hashes must match at Remux time.
14. Successful rendering is not visual approval; real frames must be inspected.
15. Never claim Remux passed unless `mkvmerge` actually ran and output attachments were post-verified.
16. Unimported proposal JSON is durable evidence and must not be ignored or deleted to bypass Human Review.
17. Human approvals are valid only for the evidence fingerprint they reviewed and must remain materialized in the current workfile.
18. Research is optional for v0.4-native titles. `off` must remain fully usable; `advisory` consumes resolved SRP without a release-blocking Research Gate; `enforce` requires a current human-approved SRP snapshot.
19. SRP is producer-neutral and offline-consumable. Never assume web research, never merge raw packs in an LLM, and never let import silently activate/update a title binding.
20. Effective SRP precedence is title+branch > series+branch > title > series; local human canon wins at the same scope. `locked` does not imply blind auto-replace.
21. Research, semantic-QA, render and visual-QA approvals must bind their input evidence; upstream edits stale downstream gates.
22. Rendering must use the exact successfully audited font files, not an unverified system fallback.
23. Source replacement must verify the current source hash first and archive the prior bytes under a unique immutable history path.

## Typical commands

```bash
subflow doctor
subflow fonts install /path/to/fonts.zip
subflow fonts verify
subflow project init <project>
subflow title init <project> <title> --profile single|source-assisted|dub|bilingual|full|auto
subflow source add <project> <title> S /path/to/subtitle.ass
subflow research status <project> <title>
# Optional: validate/import/bind/set-mode/resolve/approve SRP when research is enabled.
subflow prepare <project> <title>
subflow compile <project> <title>
subflow qa <project> <title>
subflow fonts audit <project> <title>
subflow status <project> <title>
subflow release <project> <title>
subflow remux <project> <title> --video /path/to/video.mkv
```

## Development verification

Run focused tests first, then:

```bash
python -m compileall -q src
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

For release-impacting changes also build/install the wheel in a fresh environment and run the artifact-from-ZIP verification described in `docs/testing.md`.

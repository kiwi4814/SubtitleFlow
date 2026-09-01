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
10. Kiwi Collector v1 generated dialogue uses 文泉驿微米黑, Doraemon-derived grey/gold colours, and `\blur2`.
11. Never acquire, copy, bundle, or redistribute font binaries. Users provide locally licensed fonts.
12. Production release requires every actually referenced font to be resolved unless the user explicitly relaxes the font gate.
13. A font audit records local path, MIME, size and SHA-256. Frozen font hashes must match at Remux time.
14. Successful rendering is not visual approval; real frames must be inspected.
15. Never claim Remux passed unless `mkvmerge` actually ran and output attachments were post-verified.

## Typical commands

```bash
subflow doctor
subflow project init <project>
subflow title init <project> <title> --profile single|source-assisted|dub|bilingual|full|auto
subflow source add <project> <title> S /path/to/subtitle.ass
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

# SubtitleFlow repository contract

## Product goal

SubtitleFlow is an evidence-driven subtitle production system. It accepts four source roles and produces two independent release branches:

- **A — Timing Master**: video-coordinate timing evidence.
- **B — JP→ZH translation seed**: existing Chinese translation for the Japanese-audio release.
- **C — Japanese source subtitle**: source-language semantic evidence.
- **D — Taiwan-dub transcript**: wording evidence for the Taiwan-dub release.

Outputs:

1. `zh-CN.tw`: Simplified-Chinese subtitle that follows the Taiwan dub.
2. `zh-CN-ja`: Simplified-Chinese + Japanese bilingual subtitle that follows Japanese source semantics.

## Non-negotiable rules

1. Files under `projects/*/titles/*/source/` are immutable evidence. Never edit them in place.
2. Run `subflow source verify <project> <title>` before work that depends on sources.
3. A defines the common video time coordinate system. Do not inherit C's timeline wholesale.
4. Alignment may group 1:N, N:1, or N:M cues. Never assume line N corresponds to line N.
5. TW and JP branches are independent after normalization/alignment. Do not use Taiwan-dub wording to "correct" the JP translation branch.
6. Use **Minimal Editorial Intervention**. Default decision is to keep the existing wording.
7. Deterministic, project-approved terminology changes may be auto-applied and logged.
8. Any semantic change proposed by an LLM must enter `review/candidates.json` and requires human approval before it can alter `final_text`.
9. Do not let an LLM rewrite raw ASS/SSA/SRT files. LLMs may edit research notes and proposal JSON only.
10. Protected ASS events (positioning, drawing, karaoke, transforms, effects, non-dialogue events) must survive compilation unchanged.
11. Translation, timing, styling, visual QA, and remux are separate gates.
12. Never claim visual QA passed unless frames were actually rendered from a video.
13. Never claim remux passed unless `mkvmerge` actually ran successfully.

## Typical commands

```bash
subflow doctor
subflow project init <project>
subflow title init <project> <title>
subflow source add <project> <title> A /path/to/A.ass
subflow source add <project> <title> B /path/to/B.ass
subflow source add <project> <title> C /path/to/C.ass
subflow source add <project> <title> D /path/to/D.ass
subflow prepare <project> <title>
subflow status <project> <title>
subflow review list <project> <title> --status pending --markdown
subflow compile <project> <title>
subflow qa <project> <title>
subflow render <project> <title> jp --video /path/to/video.mkv
subflow release <project> <title>
subflow remux <project> <title> --video /path/to/video.mkv
```

## Development verification

For code changes run, in order:

```bash
python -m compileall -q src
PYTHONPATH=src pytest -q
```

If Ruff is installed:

```bash
ruff check .
ruff format --check .
```

For release-impacting changes also run the synthetic end-to-end fixture and the Doraemon stress fixture described in `docs/testing.md`.

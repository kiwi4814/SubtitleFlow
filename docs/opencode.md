# OpenCode integration

SubtitleFlow keeps deterministic state in files; OpenCode supplies research, semantic judgment and independent QA.

Project resources:

- `AGENTS.md`: non-negotiable repository rules.
- `.opencode/agents/`: orchestrator, researcher, semantic editor, QA reviewer.
- `.opencode/skills/`: intake, clean polish, alignment, canon, TW/JP branches, human review, release QA.
- `.opencode/commands/subtitle/`: task-level entry points.

OpenCode must not assume full A/B/C/D. Read `title.json` and imported roles first.

Useful commands:

```text
/subtitle/init
/subtitle/research
/subtitle/prepare
/subtitle/run
/subtitle/review
/subtitle/style
/subtitle/fonts
/subtitle/semantic-qa
/subtitle/visual-review
/subtitle/release
/subtitle/remux
/subtitle/status
```

`/subtitle/run` advances from persisted state only until the next human gate. AI agents may write research/proposal/QA evidence within their permissions but must not edit immutable source files or silently rewrite final subtitles.

Font files are outside the AI artifact: local legal copies are supplied by the user. Agents may audit paths and report missing families but must not download or redistribute commercial fonts.

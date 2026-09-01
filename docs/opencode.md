# OpenCode integration

SubtitleFlow keeps deterministic state in files; OpenCode supplies orchestration, semantic judgment and independent QA. Research is an optional producer path, not an OpenCode prerequisite.

Project resources:

- `AGENTS.md`: non-negotiable repository rules.
- `.opencode/agents/`: orchestrator, researcher, semantic editor, QA reviewer.
- `.opencode/skills/`: intake, clean polish, alignment, canon, TW/JP branches, human review, release QA.
- `.opencode/commands/subtitle/`: task-level entry points.

OpenCode must not assume full A/B/C/D and must not assume research is enabled. Read `title.json`, imported roles, `subflow status`, and `subflow research status` first.

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

`/subtitle/run` is an orchestration command that reads persisted state and advances only until the next human gate. It skips research in `off`, resolves optional packs in `advisory`, and stops on a missing/stale/blocked Research Gate in `enforce`. The Python engine does not yet implement a standalone deterministic `advance-to-next-gate` planner, so the agent must consult `subflow status`/repository evidence instead of inferring progress from chat history.

`opencode.jsonc` deliberately does **not** blanket-allow `subflow *`. Read-only/safe deterministic commands have narrow shell allow rules; human-impacting actions such as `review decide`, source replacement, gate approval, `release`, `remux`, and style mutation fall back to an explicit permission prompt. AI agents may write research/proposal/QA evidence within their scoped permissions but must not edit immutable source files or silently rewrite final subtitles.

Font files are outside the AI artifact: local legal copies are supplied by the user. Agents may audit paths and report missing families but must not download or redistribute commercial fonts.

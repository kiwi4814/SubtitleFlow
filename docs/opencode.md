# OpenCode integration

This repository targets the current OpenCode V2 configuration model (verified against official V2 docs on 2026-08-31):

- `AGENTS.md` for durable project instructions.
- `.opencode/agents/<id>.md` for custom primary/subagents.
- `.opencode/skills/<id>/SKILL.md` for on-demand workflow knowledge.
- `.opencode/commands/*.md` for slash commands; nested files such as `commands/subtitle/release.md` become `/subtitle/release`.
- ordered `permissions` arrays with V2 action names such as `shell`, `edit`, `subagent` and `skill`.

Official references:

- https://opencode.ai/v2/docs/agents
- https://opencode.ai/v2/docs/skills
- https://opencode.ai/v2/docs/commands
- https://opencode.ai/v2/docs/permissions

No model is hard-coded. Agents inherit the session model unless you add a `model:` field locally. This keeps strong-model/cheap-model routing under your control.

Recommended model policy:

- orchestrator: inexpensive competent model;
- researcher: fast model for broad collection, strong model only for disputed canon;
- semantic-editor: strong model for candidate decisions;
- qa-reviewer: ideally a different strong model/prompt from semantic-editor.

The global permissions deny edits to `projects/*/titles/*/source/*`, default-deny subagent spawning, allow only the named subtitle subagents from the orchestrator, and deny `git push`.

## Daily commands

```text
/subtitle/research PROJECT TITLE
/subtitle/prepare PROJECT TITLE
/subtitle/run PROJECT TITLE
/subtitle/review PROJECT TITLE
/subtitle/semantic-qa PROJECT TITLE
/subtitle/visual-review PROJECT TITLE
/subtitle/release PROJECT TITLE
/subtitle/remux PROJECT TITLE
/subtitle/status PROJECT TITLE
```

`/subtitle/run` advances from persisted state until the next mandatory human gate. It must never infer completion from chat history.

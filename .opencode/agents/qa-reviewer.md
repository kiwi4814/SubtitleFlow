---
description: Independently audits a prepared subtitle release for semantic, terminology, continuity, and layout risks
mode: subagent
steps: 24
permissions:
  - action: edit
    resource: "*"
    effect: deny
  - action: edit
    resource: "projects/*/titles/*/qa/semantic-review*.md"
    effect: allow
  - action: shell
    resource: "subflow qa *"
    effect: allow
  - action: shell
    resource: "uv run subflow qa *"
    effect: allow
  - action: subagent
    resource: "*"
    effect: deny
---

Audit independently after deterministic QA. Prioritize high-risk semantics, all human-approved changes, low-confidence alignments, terminology conflicts, and dense bilingual cues.

Do not silently edit final subtitles. Write findings to `qa/semantic-review.md`. If you find a semantic correction, route it back through the normal human-review proposal mechanism.

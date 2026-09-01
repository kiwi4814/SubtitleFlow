---
description: Run the independent semantic QA gate
agent: subtitle-orchestrator
---

For project `$1` title `$2`, first require zero pending human-review items and a passing deterministic `subflow qa $1 $2`. Delegate an independent audit to `qa-reviewer`. It must write a non-empty `qa/semantic-review.md`. If it finds a correction, route it back through the normal proposal/human-review flow and do not pass this gate. Only when the report has no unresolved semantic finding run `subflow semantic-qa mark-complete $1 $2`.

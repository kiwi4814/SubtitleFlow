---
description: Conduct the human semantic-change review
agent: subtitle-orchestrator
---

For project `$1` title `$2`, display pending items using `subflow review list $1 $2 --status pending --markdown`. Walk the user through unresolved semantic changes. Record each explicit decision with `subflow review decide`. Do not auto-approve based on confidence.

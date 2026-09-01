---
description: Compile, QA, visually verify, and freeze subtitle release
agent: subtitle-orchestrator
---

For project `$1` title `$2`, require zero pending human reviews and a passed research gate. Run `subflow compile $1 $2` and `subflow qa $1 $2`. Delegate independent semantic QA to `qa-reviewer`; require a non-empty `qa/semantic-review.md`, route any correction back through human review, and only then run `subflow semantic-qa mark-complete $1 $2`. If visual QA is required, render each enabled branch, inspect the actual PNG frames, then run `subflow visual-qa mark-complete $1 $2 <branch>`. If any gate fails, stop with the exact blockers. Only after all required gates pass run `subflow release $1 $2`.

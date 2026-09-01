---
description: Compile, audit fonts, QA, visually verify, and freeze the active subtitle release
agent: subtitle-orchestrator
---

For project `$1` title `$2`, require zero pending human reviews. Inspect `subflow research status $1 $2`: `off` has no Research Gate, `advisory` resolves knowledge but does not independently require approval for Release, `enforce` requires current approved SRP evidence, and legacy titles retain the v0.3 gate.

Run `subflow compile $1 $2`, `subflow qa $1 $2`, and `subflow fonts audit $1 $2`. Missing actually referenced fonts are release blockers by default. Delegate independent semantic QA and route any correction through human review. Render and approve each active branch when visual QA is required. Only after all configured gates pass run `subflow release $1 $2`.

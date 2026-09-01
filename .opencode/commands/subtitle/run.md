---
description: Advance a title until the next mandatory human gate
agent: subtitle-orchestrator
---

Advance project `$1` title `$2` from its persisted state. Read `subflow status $1 $2` first. Complete only valid deterministic/research/analysis stages. Delegate semantic anomaly detection to `semantic-editor`, import resulting proposals, then STOP if any pending human review exists. Never bypass a gate merely to finish the command.

---
description: Advance a title from durable state until the next mandatory human gate
agent: subtitle-orchestrator
---

Advance project `$1` title `$2` from persisted state. Read `subflow status` and the workflow profile first. Process only active evidence/branches; never demand absent roles that the selected profile does not require. Delegate semantic anomaly detection, import proposals, and STOP on pending human review. Later gates include deterministic QA, font audit, semantic QA, and visual QA as configured. Never bypass a gate merely to finish the command.

---
description: Advance a title from durable state until the next mandatory human gate
agent: subtitle-orchestrator
---

Advance project `$1` title `$2` from persisted state. Read `subflow status $1 $2`, `subflow research status $1 $2`, and the workflow profile first. Process only active evidence/branches; never demand absent roles that the selected profile does not require.

Research behavior is determined only by persisted `research.mode`:

- `off`: skip SRP entirely.
- `advisory`: resolve bound SRP when present; absence of SRP is not a blocker.
- `enforce`: require a current approved Research Gate before semantic editing. If there is no bound pack, a blocking unresolved item, a cross-pack conflict, or stale approval, STOP and report the exact action needed.
- legacy v0.3 titles continue to use their legacy research evidence gate.

Then run prepare/alignment, delegate semantic anomaly detection, import proposals, and STOP on pending human review. Later gates include deterministic QA, font audit, semantic QA, and visual QA as configured. Never bypass a gate merely to finish the command and never initiate web research unless the user explicitly requests that producer path.

Before semantic editing, read the persisted Editorial Context. If `editing_policy=auto` and `assessment_required=true`, STOP semantic editing after producing/recording the structured Translation Quality Assessment; do not silently choose a policy. Alignment anomalies are review signals, while `bilingual-reconciliation.json` is the release-pairing authority. SOURCE_GAP is legal and must never be back-translated into fabricated Japanese.

---
name: Subtitle Human Review
description: Enforce the approval gate for semantic subtitle changes and record accept/reject/custom decisions durably.
---

LLM semantic output is a proposal, not an edit.

Import proposals with `subflow review import`. Show pending items with `subflow review list --status pending --markdown`. For each item, give the user original text, proposed text, source evidence, reason, confidence, and severity.

Only `subflow review decide ... approve|reject|custom` may resolve a proposal. Never bulk-approve semantic changes without an explicit user decision.

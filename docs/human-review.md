# Human review contract

Semantic changes are never auto-applied.

A proposal must identify branch/unit, exact current text, proposed text, reason, confidence, severity and supporting evidence. `subflow review import` rejects stale proposals whose `original_text` no longer matches the current workfile.

Example proposal:

```json
{
  "branch": "jp",
  "unit_id": "jp-000382",
  "change_type": "negation",
  "original_text": "我不会去。",
  "proposed_text": "也不是说我不去。",
  "reason": "Japanese source is a partial/double negation rather than a categorical refusal.",
  "confidence": 0.97,
  "severity": "high",
  "evidence": {
    "ja": "<source line>",
    "context": "<brief context>"
  }
}
```

Review commands:

```bash
subflow review import PROJECT TITLE review/proposals/model-output.json
subflow review list PROJECT TITLE --status pending --markdown
subflow review decide PROJECT TITLE CANDIDATE approve
subflow review decide PROJECT TITLE CANDIDATE reject
subflow review decide PROJECT TITLE CANDIDATE custom --text "人工版本"
```

Approved/custom edits append a change record to the work unit. Rejected proposals remain as evidence of what was considered. Any post-QA review change invalidates the QA snapshot, so compile/QA must be rerun before release.

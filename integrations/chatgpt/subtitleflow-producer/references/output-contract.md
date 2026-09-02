# Release bundle contract

Default final archive:

```text
SubtitleFlow-<title>-<branch>.zip
├── subtitles/
│   └── <final>.ass
├── renders/
│   └── *.png
├── reports/
│   ├── summary.md
│   ├── qa.json
│   ├── changes.jsonl
│   └── canon-gaps.jsonl        # include only when non-empty
└── manifest.json
```

Include multiple ASS outputs only when the user requested multiple branches or a bilingual companion file.

`manifest.json` should record, when available: title/series identity, requested release intent, input names and SHA-256, engine/runtime version, GitHub repo/ref/commit, Canon/SRP id/version/digest, style profile, output SHA-256 values, QA checks with `passed|failed|warning|deferred`, rendering canvas/media provenance, and Canon-gap count.

Never label a deferred check as passed.

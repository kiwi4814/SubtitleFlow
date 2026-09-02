# SubtitleFlow GitHub layout

Prefer indexed reads and narrow retrieval.

```text
SubtitleFlow/
├── src/subtitleflow/          # production engine
├── contracts/                 # portable job/release schemas
├── evidence/                  # long-term evidence library
│   └── <series>/
│       ├── index.json         # preferred discovery entrypoint when present
│       ├── catalog files
│       ├── research_packs/    # SRP/Canon snapshots
│       └── title folders/
├── styles/                    # ASS style profiles
├── fonts/font-registry.json   # font identity/role registry
└── integrations/
    ├── opencode/
    └── chatgpt/
```

For Doraemon, prefer `evidence/doraemon/index.json` once available; fall back to `MOVIE_CATALOG.json`, `AI_README.md`, title folders, and `research_packs/`.

When recording provenance, capture repository, ref/commit SHA if available, file path, and relevant SRP pack id/version/digest.

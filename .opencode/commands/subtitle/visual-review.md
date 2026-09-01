---
description: Render and approve real playback frames for every active subtitle branch
agent: subtitle-orchestrator
---

For project `$1` title `$2`, discover active branches from `subflow status`/title configuration. Run `subflow render $1 $2 <branch>` for each active `clean`, `tw`, or `jp` branch. Inspect actual PNGs for clipping, collision, safe area, line count, font fallback, readability, and bilingual hierarchy. Rendering alone is not approval. Only after inspection run `subflow visual-qa mark-complete $1 $2 <branch>`.

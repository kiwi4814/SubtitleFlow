---
description: Render and approve real subtitle playback frames
agent: subtitle-orchestrator
---

For project `$1` title `$2`, render every enabled branch with `subflow render $1 $2 tw` and/or `subflow render $1 $2 jp`. Inspect the actual PNG files under `qa/previews/<branch>/` using a vision-capable model or ask the human user to inspect them. Check collisions, safe area, line count, font fallback, readability, and source/target hierarchy. Rendering alone is not approval. Only after real visual inspection run `subflow visual-qa mark-complete $1 $2 <branch>` for each enabled branch. Never mark visual QA from file existence alone.

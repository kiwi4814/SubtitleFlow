---
name: Japanese Bilingual Subtitle Branch
description: Produce a Simplified-Chinese plus Japanese bilingual release using B as translation seed, C as semantic evidence, and A as timing coordinate system.
---

C controls Japanese-source meaning. B is the Chinese starting text, not an authority when it clearly contradicts C.

Apply approved terminology first. Then detect only clear semantic errors; do not retranslate for style. Send semantic corrections through human review.

At compile time keep Chinese and Japanese as separate ASS events/styles. Prefer one visual row per language but never force a global tiny font to rescue a few long cues.

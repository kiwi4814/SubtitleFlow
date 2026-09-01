---
name: Subtitle Canon Research
description: Optionally research or consume series/title/branch canon, terminology, entities, facts, and translation policy using SRP/1.0 without making web research a SubtitleFlow dependency.
---

Research is optional. SubtitleFlow can run with `research.mode=off` and no SRP.

When SRP is used, treat it as a producer-neutral offline knowledge exchange format. A pack may come from a web/high-end model, a local model, a human editor, or another tool. Validate/import/bind/resolve through SubtitleFlow instead of manually merging raw files.

Keep stable series canon separate from title-only knowledge and branch-specific localization. Effective precedence is deterministic: title+branch > series+branch > title > series, with local human canon winning at the same scope.

Separate Entity/Fact knowledge from Term/Decision editing rules and from Source/Evidence provenance. Evidence is optional, but claimed references must be valid. Never promote a title-specific finding to series scope without explicit review.

`locked` means an editor cannot silently override the effective rule; it does not mean deterministic string replacement is safe. `auto_replace` remains a separate local SubtitleFlow policy.

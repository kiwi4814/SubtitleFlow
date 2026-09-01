---
name: Subtitle Intake
description: Classify optional subtitle evidence roles, choose a workflow profile, preserve hashes, and verify immutable source integrity.
---

Do not require A/B/C/D when the title does not have them.

Roles:
- S = self-contained target subtitle with correct timing; used by single/source-assisted polish.
- A = Timing Master for multi-source workflows.
- B = existing Chinese translation for Japanese audio.
- C = source-language/Japanese semantic evidence.
- D = Taiwan-dub transcript.

Profiles:
- `single`: S only.
- `source-assisted`: S + C.
- `dub`: A + D.
- `bilingual`: A + B + C.
- `full`: A + B + C + D.
- `auto`: derive every valid branch from available roles.

Never invent a role or duplicate one file under fake roles merely to satisfy a profile. Import with `subflow source add`, then verify hashes. Source replacement requires explicit re-import, never in-place editing.

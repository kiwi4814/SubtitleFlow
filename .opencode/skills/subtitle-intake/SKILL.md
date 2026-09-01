---
name: Subtitle Intake
description: Import and classify A/B/C/D subtitle evidence, preserve hashes, and verify immutable source integrity before processing.
---

Use for the first stage of any title.

- A = Timing Master.
- B = existing Chinese translation aligned to Japanese audio.
- C = Japanese source subtitle.
- D = Taiwan-dub transcript.

Never infer roles from filenames when the user has not established them. Once known, import with `subflow source add`.

Run `subflow source verify` after import and before later stages. Files under `source/` are immutable; replacement requires an explicit source re-import, never an in-place edit.

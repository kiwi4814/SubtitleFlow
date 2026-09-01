---
name: Subtitle Release QA
description: Compile active ASS branches, audit fonts, run deterministic and semantic QA, visually verify frames, freeze hashes, and remux safely.
---

Order:
1. Require pending human review = 0.
2. `subflow compile`.
3. `subflow qa`.
4. `subflow fonts audit`; production release defaults to all actually referenced fonts resolved.
5. Independently inspect semantic-risk cues.
6. Render each active branch when video/visual QA is required; inspect actual frames.
7. `subflow release` freezes ASS hashes, QA input snapshot, style profile, and font file hashes.
8. `subflow remux` attaches the frozen font files with MKVToolNix and verifies output attachments.

Rendering is not visual approval. A font fallback is not a pass. Do not report Remux success without a successful `mkvmerge` execution and output verification.

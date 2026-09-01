---
name: Subtitle Release QA
description: Compile ASS, run structural/terminology/layout QA, render representative frames, freeze checksums, and remux only after gates pass.
---

Order:

1. Confirm pending human review = 0.
2. `subflow compile`.
3. `subflow qa`.
4. Independently inspect semantic-risk cues.
5. If video exists, `subflow render` for both relevant branches and inspect actual frames.
6. `subflow release` to freeze hashes and provenance.
7. `subflow remux` only when requested.

Do not report visual QA without rendered images. Do not report Remux success without a successful `mkvmerge` run.

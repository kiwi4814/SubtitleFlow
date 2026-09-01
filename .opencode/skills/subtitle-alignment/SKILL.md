---
name: Subtitle Alignment
description: Align subtitle sources against Timing Master A with N:M-aware grouping while preserving branch-specific segmentation.
---

Run deterministic preparation via `subflow prepare` rather than matching by line number.

TW branch aligns A↔D. JP branch aligns A↔B, then attaches C to the JP work units. A defines the video coordinate system, but grouping can be 1:N, N:1, or N:M.

Review low-confidence alignment flags before trusting semantic comparisons. Do not wholesale replace A timing with C timing.

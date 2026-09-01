---
description: Remux frozen subtitle tracks and SHA-verified font attachments into the target MKV
agent: subtitle-orchestrator
---

For project `$1` title `$2`, require a frozen release manifest. Use `subflow remux $1 $2`. Do not transcode video/audio. SubtitleFlow must re-check source/QA/release hashes and each frozen font SHA before invoking MKVToolNix. Existing MKV attachments are preserved by default; resolved subtitle fonts are attached with their MIME/name metadata and verified in the output. Report success only after `mkvmerge` and post-identification succeed.

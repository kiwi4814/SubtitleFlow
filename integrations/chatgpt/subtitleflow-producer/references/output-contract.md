# Portable release bundle contract

Default ChatGPT/Web archive:

```text
SubtitleFlow-<title>-<branch>.zip
├── subtitles/
│   └── <final>.ass
├── renders/
│   └── *.png
├── reports/
│   ├── summary.md
│   ├── qa.json
│   ├── fonts.json
│   ├── registered-fonts.json
│   ├── render.json
│   ├── changes.jsonl
│   └── canon-gaps.jsonl        # include only when non-empty
└── manifest.json
```

Include multiple ASS outputs only when the user requested multiple branches or a bilingual companion file.

Use the Core `release-bundle.schema.json` manifest contract. Record, when available: title/series identity, requested release intent, input names and SHA-256, engine/runtime version, GitHub repo/ref/commit, Canon/SRP id/version/digest, Effective Research digest, Semantic Packet identity, output SHA-256 values, Human Review state, exact-font evidence, renderer evidence, and Canon-gap count.

## Evidence levels

Treat a Portable Release Bundle as a useful subtitle deliverable, not automatically as an Archival Release Freeze.

- `deterministic-qa=passed` means the compiled subtitle passed current structural/terminology/layout/compiled-ASS checks.
- `exact-font-audit=passed` means every font actually referenced by the compiled ASS resolved to approved bytes.
- `registered-font-assets=passed` means the runtime's complete registered SubtitleFlow font asset set matched registry SHA/name identity.
- `synthetic-libass-render=passed` means FFmpeg/libass really rendered PNG frames with the audited fonts on a synthetic canvas. These are real renderer outputs for typography, layout, wrapping, and font-selection verification.
- `full-video-visual-qa=passed` and `scene-occlusion=passed` require real movie-image evidence and the corresponding Core visual gate. Synthetic black-canvas frames can never satisfy them.
- `semantic-qa-signoff=passed` requires the durable Core semantic QA gate; an unfinished sign-off must remain `deferred`.
- `mkv-remux=passed` requires an actual MKV/remux verification path; lack of target media or MKVToolNix must remain `deferred`.

Normalize runtime-specific absolute paths before packaging reports. Use stable labels such as `source-root://`, `workspace://`, or `title://` rather than leaking local runner paths into a portable ZIP. Keep original Core QA files untouched in the workspace; only the packaged projection is path-normalized.

The bundle should be deterministic for identical input bytes and state: stable file ordering, fixed ZIP timestamps, stable JSON/report projection, and output SHA-256 values. Rebuilding the same bundle from the same state should produce the same archive SHA-256.

A package must not imply that an unbound Canon pack, stale Semantic Packet, unreviewed model proposal, missing exact font, missing full-video review, unfinished semantic sign-off, or unexecuted Remux check has passed.

Never label a deferred check as passed.

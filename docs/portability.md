# Portability

## Python

SubtitleFlow supports Python 3.11+ and keeps the deterministic core dependency-light. The `full` extra installs OpenCC, PyYAML and FontTools support.

## Paths

Title configs may use environment variables and `~` for media/font paths. Prefer project-relative paths for portable local assets that are safe to keep outside source control.

## Fonts

For personal workflow usage, default verified fonts are bundled directly in `fonts/local/`. `fonts/font-map.json` remains ignored for optional user-specific overrides. `fonts/font-registry.json` defines the canonical identities. Exact SHA matching makes the asset set reproducible, and `subflow fonts verify` ensures font integrity on any workstation. For strict Name Table verification install FontTools.

Final collector MKVs can be more portable than loose ASS files because `subflow remux` attaches the exact frozen font files into Matroska when enabled. Player support for ASS attachments is still a playback-environment concern, so visual QA on the target player remains authoritative.

## External tools

FFmpeg/libass and MKVToolNix are external executables. `subflow doctor` reports availability. `mkvmerge` is required for Remux; `mkvextract` is additionally required when a same-name existing attachment must be cryptographically compared before reuse. Dry-run command construction is not proof that a real render or Remux succeeded.

Render/visual evidence currently identifies the selected video by normalized path, file size and nanosecond mtime so multi-gigabyte media need not be re-hashed on every status check. That detects ordinary replacement/movement but is not cryptographic provenance. The visual gate should be rerun after moving a project between machines, and a future strict media-hash mode is recommended for archival-grade reproducibility.

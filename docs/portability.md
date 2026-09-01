# Portability

## Python

SubtitleFlow supports Python 3.11+ and keeps the deterministic core dependency-light. The `full` extra installs OpenCC, PyYAML and FontTools support.

## Paths

Title configs may use environment variables and `~` for media/font paths. Prefer project-relative paths for portable local assets that are safe to keep outside source control.

## Fonts

Do not commit or distribute font binaries with SubtitleFlow. `fonts/local/` and `fonts/font-map.json` are intentionally ignored; `fonts/font-registry.json` is committed because it contains only identities/policy, not font bytes. On another workstation, run `subflow fonts install /path/to/user-fonts.zip`, `subflow fonts verify`, then rerun the title-level font audit. Exact SHA matching makes the local asset set reproducible even when incoming filenames differ. For strict Name Table verification install FontTools.

Final collector MKVs can be more portable than loose ASS files because `subflow remux` attaches the exact frozen font files into Matroska when enabled. Player support for ASS attachments is still a playback-environment concern, so visual QA on the target player remains authoritative.

## External tools

FFmpeg/libass and MKVToolNix are external executables. `subflow doctor` reports availability. `mkvmerge` is required for Remux; `mkvextract` is additionally required when a same-name existing attachment must be cryptographically compared before reuse. Dry-run command construction is not proof that a real render or Remux succeeded.

Render/visual evidence currently identifies the selected video by normalized path, file size and nanosecond mtime so multi-gigabyte media need not be re-hashed on every status check. That detects ordinary replacement/movement but is not cryptographic provenance. The visual gate should be rerun after moving a project between machines, and a future strict media-hash mode is recommended for archival-grade reproducibility.

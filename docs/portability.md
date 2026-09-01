# Portability

## Python

SubtitleFlow supports Python 3.11+ and keeps the deterministic core dependency-light. The `full` extra installs OpenCC, PyYAML and FontTools support.

## Paths

Title configs may use environment variables and `~` for media/font paths. Prefer project-relative paths for portable local assets that are safe to keep outside source control.

## Fonts

Do not commit or distribute font binaries with SubtitleFlow. `fonts/local/` and `fonts/font-map.json` are intentionally ignored. On another workstation, supply legally available equivalent font files and rerun `subflow fonts audit` before release.

Final collector MKVs can be more portable than loose ASS files because `subflow remux` attaches the exact frozen font files into Matroska when enabled. Player support for ASS attachments is still a playback-environment concern, so visual QA on the target player remains authoritative.

## External tools

FFmpeg/libass and MKVToolNix are external executables. `subflow doctor` reports availability. `mkvmerge` is required for Remux; `mkvextract` is additionally required when a same-name existing attachment must be cryptographically compared before reuse. Dry-run command construction is not proof that a real render or Remux succeeded.

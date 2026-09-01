from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from .errors import GateError, ValidationError
from .io import read_json
from .qa import qa_input_snapshot
from .state import update_stage
from .util import run_checked, sha256_file, which
from .workspace import TitlePaths, verify_sources


def _expand(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def build_remux_command(
    *,
    video: Path,
    output: Path,
    tw_ass: Path | None,
    jp_ass: Path | None,
    tw_name: str,
    jp_name: str,
    preserve_existing_subtitles: bool = True,
) -> list[str]:
    cmd = ["mkvmerge", "-o", str(output)]
    if not preserve_existing_subtitles:
        cmd.append("--no-subtitles")
    cmd.append(str(video))
    if tw_ass:
        cmd.extend(
            [
                "--language",
                "0:zh-CN",
                "--track-name",
                f"0:{tw_name}",
                "--default-track-flag",
                "0:0",
                str(tw_ass),
            ]
        )
    if jp_ass:
        cmd.extend(
            [
                "--language",
                "0:zh-CN",
                "--track-name",
                f"0:{jp_name}",
                "--default-track-flag",
                "0:0",
                str(jp_ass),
            ]
        )
    return cmd


def remux(
    paths: TitlePaths,
    *,
    video: Path | None = None,
    output: Path | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> Sequence[str]:
    summary = read_json(paths.qa / "summary.json") if (paths.qa / "summary.json").exists() else None
    if not summary or not summary.get("ok"):
        raise GateError("Remux blocked: QA summary is missing or failed")
    release_manifest_path = paths.release / "release-manifest.json"
    if not release_manifest_path.exists():
        raise GateError("Remux blocked: subtitle release has not been frozen with `subflow release`")
    release_manifest = read_json(release_manifest_path)
    verify_sources(paths)
    if release_manifest.get("qa_input_snapshot") != qa_input_snapshot(paths):
        raise GateError("Remux blocked: frozen release is stale because subtitle/canon/config/review inputs changed")
    qa_path = paths.qa / "summary.json"
    if release_manifest.get("qa_summary_sha256") != sha256_file(qa_path):
        raise GateError("Remux blocked: QA summary changed after the release was frozen")
    for record in release_manifest.get("files", []):
        release_file = paths.release / str(record.get("name", ""))
        if not release_file.is_file() or sha256_file(release_file) != record.get("sha256"):
            raise GateError(f"Remux blocked: frozen release file changed: {release_file.name}")
    config = read_json(paths.title_config)
    media_cfg = config.get("media", {})
    if video is None:
        raw_video = media_cfg.get("video")
        if not raw_video:
            raise ValidationError("Video path is not configured; pass --video")
        video = _expand(str(raw_video))
    if not video.is_file():
        raise ValidationError(f"Video file not found: {video}")
    if output is None:
        raw_output = media_cfg.get("output_mkv")
        output = _expand(str(raw_output)) if raw_output else video.with_name(video.stem + ".subtitleflow.mkv")
    if output.exists() and not force:
        raise GateError(f"Output already exists: {output}; use --force explicitly")

    tw_ass = paths.release / f"{paths.title_id}.zh-CN.tw.ass"
    jp_ass = paths.release / f"{paths.title_id}.zh-CN-ja.ass"
    tw_ass = tw_ass if tw_ass.exists() else None
    jp_ass = jp_ass if jp_ass.exists() else None
    if tw_ass is None and jp_ass is None:
        raise GateError("No compiled release ASS files found")
    names = config.get("release_names", {})
    cmd = build_remux_command(
        video=video,
        output=output,
        tw_ass=tw_ass,
        jp_ass=jp_ass,
        tw_name=str(names.get("tw", "简体中文｜台配")),
        jp_name=str(names.get("jp", "简日双语｜日配")),
        preserve_existing_subtitles=bool(media_cfg.get("preserve_existing_tracks", True)),
    )
    if dry_run:
        return cmd
    if not which("mkvmerge"):
        raise GateError("mkvmerge is required. Install MKVToolNix or use --dry-run to inspect the command")
    output.parent.mkdir(parents=True, exist_ok=True)
    run_checked(cmd, timeout=3600, capture=True)
    update_stage(paths, "remux", "passed", output=str(output))
    return cmd

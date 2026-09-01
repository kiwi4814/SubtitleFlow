from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .errors import GateError, ValidationError
from .io import read_json, write_json
from .state import invalidate_stages, update_stage
from .util import run_checked, which
from .workspace import TitlePaths
from .workfile import load_workfile


def expand_media_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def probe_media(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationError(f"Media file not found: {path}")
    if not which("ffprobe"):
        raise GateError("ffprobe is required for media probing")
    proc = run_checked(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ]
    )
    return json.loads(proc.stdout)


def _seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.3f}"


def render_previews(
    paths: TitlePaths,
    branch: str,
    *,
    video: Path | None = None,
    max_frames: int = 12,
) -> list[Path]:
    if not which("ffmpeg"):
        raise GateError("ffmpeg is required for visual preview")
    config = read_json(paths.title_config)
    video = video or expand_media_path(config.get("media", {}).get("video"))
    if video is None or not video.is_file():
        raise ValidationError("A readable video path is required for visual preview")
    if branch == "tw":
        ass_path = paths.release / f"{paths.title_id}.zh-CN.tw.ass"
    elif branch == "jp":
        ass_path = paths.release / f"{paths.title_id}.zh-CN-ja.ass"
    else:
        raise ValidationError("branch must be tw or jp")
    if not ass_path.exists():
        raise ValidationError(f"Compiled ASS not found: {ass_path}")

    media_info = probe_media(video)
    try:
        duration_ms = int(float(media_info.get("format", {}).get("duration", 0)) * 1000)
    except (TypeError, ValueError):
        duration_ms = 0

    layout = read_json(paths.qa / "layout.json") if (paths.qa / "layout.json").exists() else {}
    candidates = [
        int(item["timestamp_ms"])
        for item in layout.get("preview_candidates", [])
        if item.get("branch") == branch
    ]
    if not candidates:
        work = load_workfile(paths, branch)
        if work.units:
            indices = sorted({0, len(work.units) // 2, len(work.units) - 1})
            candidates = [
                work.units[index].start_ms
                + max(0, work.units[index].end_ms - work.units[index].start_ms) // 2
                for index in indices
            ]
        elif duration_ms > 1000:
            candidates = [max(100, int(duration_ms * 0.50))]
        else:
            candidates = [100]
    selected: list[int] = []
    for timestamp in candidates:
        if timestamp < 0:
            continue
        if duration_ms and timestamp >= max(0, duration_ms - 50):
            continue
        if timestamp not in selected:
            selected.append(timestamp)
        if len(selected) >= max_frames:
            break
    if not selected:
        raise ValidationError("No preview timestamp falls within the video duration")

    invalidate_stages(paths, (f"visual_{branch}", "release", "remux"), reason=f"{branch} previews rerendered")
    output_dir = paths.qa / "previews" / branch
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="subtitleflow-render-") as temp:
        temp_dir = Path(temp)
        local_ass = temp_dir / "subs.ass"
        shutil.copy2(ass_path, local_ass)
        for index, timestamp in enumerate(selected, start=1):
            output = output_dir / f"{index:02d}-{timestamp}ms.png"
            run_checked(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-copyts",
                    "-ss",
                    _seconds(timestamp),
                    "-i",
                    str(video),
                    "-vf",
                    "ass=subs.ass",
                    "-frames:v",
                    "1",
                    "-y",
                    str(output),
                ],
                cwd=temp_dir,
                timeout=120,
            )
            if not output.exists() or output.stat().st_size == 0:
                raise GateError(f"FFmpeg returned without producing preview frame: {output}")
            outputs.append(output)
    update_stage(paths, f"render_{branch}", "passed", frames=len(outputs))
    return outputs

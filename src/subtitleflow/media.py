from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .errors import GateError, ValidationError
from .fonts import require_font_attachments
from .io import read_json
from .state import invalidate_stages, update_stage
from .util import file_identity, run_checked, sha256_file, which
from .workfile import load_workfile
from .workflow import branch_release_filename
from .workspace import TitlePaths


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


def _font_evidence(attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "attachment_name": str(item["attachment_name"]),
                "sha256": str(item["sha256"]),
                "size": int(item["size"]),
            }
            for item in attachments
        ],
        key=lambda item: item["attachment_name"].casefold(),
    )


def _frame_evidence(output_dir: Path) -> dict[str, str]:
    return {
        path.name: sha256_file(path)
        for path in sorted(output_dir.glob("*.png"))
        if path.is_file() and path.stat().st_size > 0
    }


def current_render_evidence(paths: TitlePaths, branch: str) -> dict[str, Any]:
    """Validate and return the durable evidence for a previously completed render.

    This is intentionally strict: a passed render is not proof once its ASS, external video,
    audited fonts, or any preview PNG has changed.
    """
    if branch not in {"clean", "tw", "jp"}:
        raise ValidationError("branch must be clean, tw, or jp")
    state = read_json(paths.state)
    stage = state.get("stages", {}).get(f"render_{branch}", {})
    if stage.get("status") != "passed":
        raise GateError(f"render_{branch} is not passed")
    expected = stage.get("evidence")
    if not isinstance(expected, dict):
        raise GateError(f"render_{branch} predates render evidence snapshots; rerender this branch")

    ass_path = paths.release / branch_release_filename(paths.title_id, branch)
    if not ass_path.is_file():
        raise GateError(f"Rendered ASS disappeared: {ass_path}")
    ass_expected = expected.get("ass", {})
    if not isinstance(ass_expected, dict) or sha256_file(ass_path) != ass_expected.get("sha256"):
        raise GateError(f"render_{branch} is stale: compiled ASS changed after rendering")

    video_expected = expected.get("video", {})
    if not isinstance(video_expected, dict) or not video_expected.get("path"):
        raise GateError(f"render_{branch} has no frozen video identity; rerender this branch")
    video = Path(str(video_expected["path"]))
    if not video.is_file() or file_identity(video) != video_expected:
        raise GateError(f"render_{branch} is stale: reviewed video changed or disappeared")

    attachments = require_font_attachments(paths)
    fonts_current = _font_evidence(attachments)
    if fonts_current != expected.get("fonts"):
        raise GateError(f"render_{branch} is stale: audited font set changed after rendering")

    frames_current = _frame_evidence(paths.qa / "previews" / branch)
    if not frames_current or frames_current != expected.get("frames"):
        raise GateError(f"render_{branch} is stale: preview frame evidence changed after rendering")

    return {
        "ass": {"path": str(ass_path.relative_to(paths.title)), "sha256": sha256_file(ass_path)},
        "video": file_identity(video),
        "fonts": fonts_current,
        "frames": frames_current,
    }


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
    video = video.resolve()
    if branch not in {"clean", "tw", "jp"}:
        raise ValidationError("branch must be clean, tw, or jp")
    if max_frames <= 0:
        raise ValidationError("max_frames must be greater than zero")
    ass_path = paths.release / branch_release_filename(paths.title_id, branch)
    if not ass_path.exists():
        raise ValidationError(f"Compiled ASS not found: {ass_path}")

    # Visual QA must render with the exact font files already resolved by the font audit.
    # Without this, libass can silently use an OS font fallback and the screenshot ceases to
    # represent the font-complete release that will be remuxed later.
    attachments = require_font_attachments(paths)

    # From this point onward this invocation is a real rerender attempt. Invalidate the old
    # evidence before calling ffprobe/ffmpeg and remove old frames so a failed rerender cannot
    # be approved accidentally.
    invalidate_stages(
        paths,
        (f"render_{branch}", f"visual_{branch}", "release", "remux"),
        reason=f"{branch} previews rerendered",
    )
    output_dir = paths.qa / "previews" / branch
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_frame in output_dir.glob("*.png"):
        if old_frame.is_file():
            old_frame.unlink()

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

    outputs: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="subtitleflow-render-") as temp:
        temp_dir = Path(temp)
        local_ass = temp_dir / "subs.ass"
        shutil.copy2(ass_path, local_ass)
        fonts_dir = temp_dir / "fonts"
        fonts_dir.mkdir()
        for attachment in attachments:
            source = Path(str(attachment["path"]))
            target = fonts_dir / str(attachment["attachment_name"])
            if target.exists():
                raise GateError(f"Duplicate staged font attachment name: {target.name}")
            shutil.copy2(source, target)
        filter_value = "ass=subs.ass" + (":fontsdir=fonts" if attachments else "")

        staged_frames: list[tuple[Path, Path]] = []
        for index, timestamp in enumerate(selected, start=1):
            final_output = output_dir / f"{index:02d}-{timestamp}ms.png"
            staged_output = temp_dir / final_output.name
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
                    filter_value,
                    "-frames:v",
                    "1",
                    "-y",
                    str(staged_output),
                ],
                cwd=temp_dir,
                timeout=120,
            )
            if not staged_output.exists() or staged_output.stat().st_size == 0:
                raise GateError(f"FFmpeg returned without producing preview frame: {final_output}")
            staged_frames.append((staged_output, final_output))

        for staged_output, final_output in staged_frames:
            shutil.copy2(staged_output, final_output)
            outputs.append(final_output)

    evidence = {
        "ass": {
            "path": str(ass_path.relative_to(paths.title)),
            "sha256": sha256_file(ass_path),
        },
        "video": file_identity(video),
        "fonts": _font_evidence(attachments),
        "frames": _frame_evidence(output_dir),
    }
    update_stage(paths, f"render_{branch}", "passed", frames=len(outputs), evidence=evidence)
    return outputs

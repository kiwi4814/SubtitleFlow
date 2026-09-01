from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .errors import GateError
from .fonts import require_font_attachments
from .io import read_json, write_json
from .style import ass_style_values, load_style_profile
from .util import run_checked, sha256_file, which
from .workflow import active_branches, branch_release_filename
from .workspace import TitlePaths

_FONTSELECT_RE = re.compile(r"fontselect:\s*\((.*?)\)\s*->\s*(.*)$", re.I)


def _candidate_times(paths: TitlePaths, branch: str, max_frames: int) -> list[int]:
    layout_path = paths.qa / "layout.json"
    values: list[int] = []
    if layout_path.is_file():
        layout = read_json(layout_path)
        for item in layout.get("preview_candidates", []):
            if item.get("branch") == branch:
                values.append(int(item.get("timestamp_ms", 0)))
    if not values:
        from .workfile import load_workfile

        work = load_workfile(paths, branch)
        values = [
            unit.start_ms + max(0, unit.end_ms - unit.start_ms) // 2
            for unit in work.units[:max_frames]
        ]
    result: list[int] = []
    for value in values:
        if value >= 0 and value not in result:
            result.append(value)
        if len(result) >= max_frames:
            break
    return result


def _fontselect(stderr: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for line in stderr.splitlines():
        match = _FONTSELECT_RE.search(line)
        if match:
            found.append({"request": match.group(1).strip(), "resolved": match.group(2).strip()})
    return found


def run_renderer_qa(paths: TitlePaths, *, max_frames: int = 12) -> dict[str, Any]:
    """Render high-risk typography frames with libass, using a synthetic canvas if needed.

    This proves font resolution, wrapping and subtitle block geometry. It deliberately does not
    claim face/object/scene-occlusion review; that remains the real-video visual gate.
    """
    if not which("ffmpeg"):
        report = {"schema_version": 1, "status": "not-run", "reason": "ffmpeg unavailable"}
        write_json(paths.qa / "render-summary.json", report)
        return report
    attachments = require_font_attachments(paths)
    branches: dict[str, Any] = {}
    overall_errors: list[dict[str, Any]] = []
    profile = load_style_profile(paths)
    resolution = profile.get("play_resolution", {})
    width = int(resolution.get("x", 1920))
    height = int(resolution.get("y", 1080))
    requested_families = {
        ass_style_values(paths, "SF-ZH").get("Fontname", ""),
        ass_style_values(paths, "SF-JA").get("Fontname", ""),
    }
    requested_families.discard("")

    for branch in active_branches(paths):
        ass_path = paths.release / branch_release_filename(paths.title_id, branch)
        if not ass_path.is_file():
            continue
        output_dir = paths.qa / "previews" / branch
        output_dir.mkdir(parents=True, exist_ok=True)
        times = _candidate_times(paths, branch, max_frames)
        rendered: list[dict[str, Any]] = []
        branch_fontselect: list[dict[str, str]] = []
        errors: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix="subtitleflow-renderqa-") as temp:
            root = Path(temp)
            local_ass = root / "subs.ass"
            shutil.copy2(ass_path, local_ass)
            fonts_dir = root / "fonts"
            fonts_dir.mkdir()
            staged_names: set[str] = set()
            for attachment in attachments:
                source = Path(str(attachment["path"]))
                name = str(attachment["attachment_name"])
                shutil.copy2(source, fonts_dir / name)
                staged_names.add(name.casefold())
            filter_value = "ass=subs.ass" + (":fontsdir=fonts" if attachments else "")
            for index, timestamp in enumerate(times, start=1):
                output = output_dir / f"renderer-{index:02d}-{timestamp}ms.png"
                shifted = timestamp / 1000.0
                proc = run_checked(
                    [
                        "ffmpeg",
                        "-hide_banner",
                        "-loglevel",
                        "verbose",
                        "-f",
                        "lavfi",
                        "-i",
                        f"color=c=black:s={width}x{height}:r=1:d=0.1",
                        "-vf",
                        f"setpts=PTS+{shifted:.3f}/TB,{filter_value}",
                        "-frames:v",
                        "1",
                        "-y",
                        str(output),
                    ],
                    cwd=root,
                    timeout=120,
                )
                selected = _fontselect(proc.stderr or "")
                branch_fontselect.extend(selected)
                if not output.is_file() or output.stat().st_size == 0:
                    errors.append({"kind": "renderer-no-frame", "timestamp_ms": timestamp})
                else:
                    rendered.append(
                        {
                            "timestamp_ms": timestamp,
                            "file": str(output.relative_to(paths.title)),
                            "sha256": sha256_file(output),
                        }
                    )
        for family in sorted(requested_families):
            matches = [item for item in branch_fontselect if family.casefold() in item["request"].casefold()]
            if not matches:
                errors.append({"kind": "font-resolution-unobserved", "family": family})
                continue
            if attachments and not any(
                any(name in item["resolved"].casefold() for name in staged_names) for item in matches
            ):
                errors.append(
                    {
                        "kind": "unexpected-font-fallback",
                        "family": family,
                        "resolved": [item["resolved"] for item in matches],
                    }
                )
        branches[branch] = {
            "ok": not errors,
            "canvas": "synthetic",
            "typography_layout_verified": True,
            "scene_occlusion_verified": False,
            "frames": rendered,
            "fontselect": branch_fontselect,
            "errors": errors,
        }
        overall_errors.extend({"branch": branch, **item} for item in errors)

    report = {
        "schema_version": 1,
        "status": "passed" if not overall_errors else "failed",
        "ok": not overall_errors,
        "renderer": "FFmpeg/libass",
        "canvas": "synthetic",
        "statement": "Typography/layout verified on synthetic canvas. Scene occlusion was not verified.",
        "branches": branches,
        "errors": overall_errors,
    }
    write_json(paths.qa / "render-summary.json", report)
    return report

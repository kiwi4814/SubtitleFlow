from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .errors import GateError, ValidationError
from .gates import (
    validate_research_evidence,
    validate_semantic_qa_evidence,
    validate_visual_qa_evidence,
)
from .io import read_json
from .qa import qa_input_snapshot
from .srp.registry import research_mode
from .state import update_stage
from .util import file_identity, run_checked, sha256_file, which
from .workflow import active_branches, branch_release_filename
from .workspace import TitlePaths, verify_sources


def _expand(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def identify_attachments(path: Path) -> list[dict[str, Any]]:
    if not which("mkvmerge"):
        return []
    proc = run_checked(["mkvmerge", "-J", str(path)], timeout=120)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise GateError(f"mkvmerge returned invalid identification JSON for {path}") from exc
    results: list[dict[str, Any]] = []
    for item in data.get("attachments", []):
        if not isinstance(item, dict):
            continue
        props = item.get("properties", {}) if isinstance(item.get("properties"), dict) else {}
        filename = item.get("file_name") or props.get("file_name") or item.get("name")
        content_type = item.get("content_type") or props.get("content_type")
        size = item.get("size") or props.get("size")
        try:
            size_value = int(size) if size is not None else None
        except (TypeError, ValueError):
            size_value = None
        results.append(
            {
                "id": item.get("id"),
                "file_name": str(filename) if filename else None,
                "content_type": str(content_type) if content_type else None,
                "description": item.get("description"),
                "size": size_value,
            }
        )
    return results


def _attachment_exists(existing: list[dict[str, Any]], attachment: dict[str, Any]) -> bool:
    name = str(attachment.get("attachment_name", ""))
    size = int(attachment.get("size", -1))
    for item in existing:
        if item.get("file_name") != name:
            continue
        current_size = item.get("size")
        if current_size is None or current_size == size:
            return True
    return False


def _existing_attachment_sha256(video: Path, item: dict[str, Any]) -> str:
    attachment_id = item.get("id")
    if not isinstance(attachment_id, int):
        raise GateError("Cannot verify existing MKV attachment: attachment ID is missing")
    if not which("mkvextract"):
        raise GateError(
            "Existing MKV contains a same-name font attachment, but mkvextract is unavailable; "
            "install the full MKVToolNix suite so SubtitleFlow can compare attachment SHA-256"
        )
    with tempfile.TemporaryDirectory(prefix="subtitleflow-attachment-") as tmp:
        output = Path(tmp) / "attachment.bin"
        run_checked(
            ["mkvextract", str(video), "attachments", f"{attachment_id}:{output}"],
            timeout=300,
            capture=True,
        )
        if not output.is_file():
            raise GateError(f"mkvextract did not create the requested attachment: {attachment_id}")
        return sha256_file(output)


def _fonts_to_attach(
    video: Path,
    frozen: list[dict[str, Any]],
    existing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for font in frozen:
        same_name = [
            item
            for item in existing
            if item.get("file_name") == str(font.get("attachment_name", ""))
        ]
        if not same_name:
            selected.append(font)
            continue
        expected = str(font.get("sha256", ""))
        hashes = [_existing_attachment_sha256(video, item) for item in same_name]
        if any(digest != expected for digest in hashes):
            raise GateError(
                "Remux blocked: input MKV already contains a same-name font attachment with "
                f"different content: {font.get('attachment_name')}"
            )
        # Every same-name attachment is byte-identical to the frozen font; reuse it.
    return selected


def _append_subtitle(
    cmd: list[str],
    path: Path | None,
    *,
    language: str,
    name: str,
) -> None:
    if path is None:
        return
    cmd.extend(
        [
            "--language",
            f"0:{language}",
            "--track-name",
            f"0:{name}",
            "--default-track-flag",
            "0:0",
            str(path),
        ]
    )


def build_remux_command(
    *,
    video: Path,
    output: Path,
    clean_ass: Path | None = None,
    tw_ass: Path | None = None,
    jp_ass: Path | None = None,
    clean_name: str = "简体中文｜精校",
    tw_name: str = "简体中文｜台配",
    jp_name: str = "简日双语｜日配",
    font_attachments: list[dict[str, Any]] | None = None,
    preserve_existing_subtitles: bool = True,
    preserve_existing_attachments: bool = True,
) -> list[str]:
    cmd = ["mkvmerge", "-o", str(output)]
    if not preserve_existing_subtitles:
        cmd.append("--no-subtitles")
    if not preserve_existing_attachments:
        cmd.append("--no-attachments")
    cmd.append(str(video))
    _append_subtitle(cmd, clean_ass, language="zh-CN", name=clean_name)
    _append_subtitle(cmd, tw_ass, language="zh-CN", name=tw_name)
    _append_subtitle(cmd, jp_ass, language="zh-CN", name=jp_name)
    for attachment in font_attachments or []:
        path = Path(str(attachment["path"]))
        description = "SubtitleFlow font: " + ", ".join(attachment.get("families", []))
        cmd.extend(
            [
                "--attachment-description",
                description,
                "--attachment-name",
                str(attachment["attachment_name"]),
                "--attach-file",
                str(path),
            ]
        )
    return cmd


def _verify_frozen_fonts(release_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    attachments = list(release_manifest.get("font_attachments", []))
    for item in attachments:
        path = Path(str(item.get("path", "")))
        if not path.is_file():
            raise GateError(f"Remux blocked: frozen font file is missing: {path}")
        if path.stat().st_size != int(item.get("size", -1)):
            raise GateError(f"Remux blocked: frozen font size changed: {path}")
        if sha256_file(path) != item.get("sha256"):
            raise GateError(f"Remux blocked: frozen font hash changed: {path}")
    return attachments


def _verify_output_fonts(output: Path, expected: list[dict[str, Any]]) -> None:
    if not expected:
        return
    existing = identify_attachments(output)
    missing = [
        item["attachment_name"] for item in expected if not _attachment_exists(existing, item)
    ]
    if missing:
        raise GateError(
            "mkvmerge completed but required font attachments were not found in output: "
            + ", ".join(missing)
        )


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
        raise GateError(
            "Remux blocked: subtitle release has not been frozen with `subflow release`"
        )
    release_manifest = read_json(release_manifest_path)
    verify_sources(paths)
    if release_manifest.get("qa_input_snapshot") != qa_input_snapshot(paths):
        raise GateError(
            "Remux blocked: frozen release is stale because subtitle/canon/config/style/font/review inputs changed"
        )
    qa_path = paths.qa / "summary.json"
    if release_manifest.get("qa_summary_sha256") != sha256_file(qa_path):
        raise GateError("Remux blocked: QA summary changed after the release was frozen")
    for record in release_manifest.get("files", []):
        release_file = paths.release / str(record.get("name", ""))
        if not release_file.is_file() or sha256_file(release_file) != record.get("sha256"):
            raise GateError(f"Remux blocked: frozen release file changed: {release_file.name}")
    config = read_json(paths.title_config)
    gates = config.get("quality_gates", {})
    frozen_gate_evidence = release_manifest.get("gate_evidence", {})
    mode = research_mode(paths)
    research_required = mode == "enforce" or (
        mode == "legacy" and gates.get("require_research", True)
    )
    if research_required:
        current = validate_research_evidence(paths)
        if current != frozen_gate_evidence.get("research"):
            raise GateError("Remux blocked: research evidence changed after the release was frozen")
    if gates.get("require_semantic_qa", True):
        current = validate_semantic_qa_evidence(paths)
        if current != frozen_gate_evidence.get("semantic_qa"):
            raise GateError(
                "Remux blocked: semantic QA evidence changed after the release was frozen"
            )
    if gates.get("require_visual_qa", True):
        frozen_visual = frozen_gate_evidence.get("visual", {})
        for branch in active_branches(paths):
            current = validate_visual_qa_evidence(paths, branch)
            if current != frozen_visual.get(branch):
                raise GateError(
                    f"Remux blocked: {branch} visual QA evidence changed after the release was frozen"
                )

    media_cfg = config.get("media", {})
    if video is None:
        raw_video = media_cfg.get("video")
        if not raw_video:
            raise ValidationError("Video path is not configured; pass --video")
        video = _expand(str(raw_video))
    if not video.is_file():
        raise ValidationError(f"Video file not found: {video}")
    video = video.resolve()
    frozen_video = release_manifest.get("media", {}).get("video")
    if frozen_video is not None and file_identity(video) != frozen_video:
        raise GateError(
            "Remux blocked: selected video is not the exact media.video that passed visual QA"
        )
    if output is None:
        raw_output = media_cfg.get("output_mkv")
        output = (
            _expand(str(raw_output))
            if raw_output
            else video.with_name(video.stem + ".subtitleflow.mkv")
        )
    output = output.resolve()
    if os.path.normcase(str(output)) == os.path.normcase(str(video)):
        raise GateError("Remux blocked: output path must not be the same as the input video")
    if output.exists() and not force:
        raise GateError(f"Output already exists: {output}; use --force explicitly")

    subtitle_paths = {
        branch: paths.release / branch_release_filename(paths.title_id, branch)
        for branch in active_branches(paths)
    }
    subtitle_paths = {branch: path for branch, path in subtitle_paths.items() if path.exists()}
    if not subtitle_paths:
        raise GateError("No compiled release ASS files found")

    fonts_cfg = config.get("fonts", {})
    all_fonts = _verify_frozen_fonts(release_manifest)
    attach_fonts = all_fonts if bool(fonts_cfg.get("attach_to_mkv", True)) else []
    preserve_existing_attachments = bool(media_cfg.get("preserve_existing_attachments", True))
    if which("mkvmerge") and preserve_existing_attachments:
        existing = identify_attachments(video)
        attach_fonts = _fonts_to_attach(video, attach_fonts, existing)

    names = config.get("release_names", {})
    cmd = build_remux_command(
        video=video,
        output=output,
        clean_ass=subtitle_paths.get("clean"),
        tw_ass=subtitle_paths.get("tw"),
        jp_ass=subtitle_paths.get("jp"),
        clean_name=str(names.get("clean", "简体中文｜精校")),
        tw_name=str(names.get("tw", "简体中文｜台配")),
        jp_name=str(names.get("jp", "简日双语｜日配")),
        font_attachments=attach_fonts,
        preserve_existing_subtitles=bool(media_cfg.get("preserve_existing_tracks", True)),
        preserve_existing_attachments=preserve_existing_attachments,
    )
    if dry_run:
        return cmd
    if not which("mkvmerge"):
        raise GateError(
            "mkvmerge is required. Install MKVToolNix or use --dry-run to inspect the command"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    run_checked(cmd, timeout=3600, capture=True)
    _verify_output_fonts(output, all_fonts if bool(fonts_cfg.get("attach_to_mkv", True)) else [])
    update_stage(
        paths,
        "remux",
        "passed",
        output=str(output),
        font_attachments=[item["attachment_name"] for item in all_fonts],
    )
    return cmd

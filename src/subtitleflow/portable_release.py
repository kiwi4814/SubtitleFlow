from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from .errors import GateError, ValidationError
from .fonts import verify_registered_fonts
from .io import read_json, write_json
from .util import sha256_file
from .workfile import load_workfile
from .workflow import branch_release_filename
from .workspace import TitlePaths, title_paths


@dataclass(frozen=True, slots=True)
class PortableBundleResult:
    bundle_dir: str
    archive: str | None
    archive_sha256: str | None
    manifest: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _engine_version() -> str | None:
    try:
        return version("subtitleflow")
    except PackageNotFoundError:
        return None


def _bundle_schema(source_root: Path) -> dict[str, Any]:
    path = source_root / "contracts" / "release-bundle.schema.json"
    if not path.is_file():
        raise ValidationError(f"Portable release contract is missing: {path}")
    return read_json(path)


def _validate_manifest(manifest: dict[str, Any], *, source_root: Path) -> None:
    try:
        Draft202012Validator(_bundle_schema(source_root)).validate(manifest)
    except JsonSchemaValidationError as exc:
        location = ".".join(str(item) for item in exc.absolute_path)
        where = f" at {location}" if location else ""
        raise ValidationError(f"Invalid portable release manifest{where}: {exc.message}") from exc


def _portableize_paths(
    value: Any,
    *,
    title_root: Path,
    workspace_root: Path,
    source_root: Path,
) -> Any:
    """Replace runtime-specific absolute paths with stable portable URI-like labels."""
    if isinstance(value, dict):
        return {
            str(key): _portableize_paths(
                item,
                title_root=title_root,
                workspace_root=workspace_root,
                source_root=source_root,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _portableize_paths(
                item,
                title_root=title_root,
                workspace_root=workspace_root,
                source_root=source_root,
            )
            for item in value
        ]
    if not isinstance(value, str):
        return value

    path = Path(value)
    if not path.is_absolute():
        return value
    roots = (
        ("title", title_root.resolve()),
        ("workspace", workspace_root.resolve()),
        ("source-root", source_root.resolve()),
    )
    for label, root in roots:
        try:
            relative = path.resolve().relative_to(root)
        except (ValueError, OSError):
            continue
        suffix = relative.as_posix()
        return f"{label}://{suffix}" if suffix != "." else f"{label}://"
    return f"external://{path.name}"


def _copy_output(
    source: Path,
    destination: Path,
    *,
    bundle_root: Path,
    kind: str,
) -> dict[str, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "path": destination.relative_to(bundle_root).as_posix(),
        "sha256": sha256_file(destination),
        "kind": kind,
    }


def _write_report_output(
    destination: Path,
    payload: Any,
    *,
    bundle_root: Path,
) -> dict[str, str]:
    write_json(destination, payload)
    return {
        "path": destination.relative_to(bundle_root).as_posix(),
        "sha256": sha256_file(destination),
        "kind": "report",
    }


def _source_inputs(paths: TitlePaths) -> list[dict[str, str | None]]:
    manifest = read_json(paths.manifest)
    inputs: list[dict[str, str | None]] = []
    sources = manifest.get("sources", {})
    if not isinstance(sources, dict):
        return inputs
    for role, record in sorted(sources.items()):
        if not isinstance(record, dict):
            continue
        digest = str(record.get("sha256", ""))
        name = str(record.get("original_name") or record.get("path") or role)
        inputs.append(
            {
                "name": name,
                "sha256": digest,
                "role": str(role),
                "provenance": str(record.get("path")) if record.get("path") else None,
            }
        )
    return inputs


def _changes(paths: TitlePaths, branch: str) -> list[dict[str, Any]]:
    work = load_workfile(paths, branch)
    result: list[dict[str, Any]] = []
    for unit in work.units:
        for index, change in enumerate(unit.changes, start=1):
            result.append(
                {
                    "unit_id": unit.id,
                    "change_index": index,
                    **change.to_dict(),
                }
            )
    return result


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    path.write_text(payload, encoding="utf-8", newline="")


def _qa_item(
    check: str,
    status: str,
    *,
    reason: str | None = None,
    evidence: Any = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {"check": check, "status": status, "reason": reason}
    if evidence is not None:
        item["evidence"] = evidence
    return item


def _stage_status(state: dict[str, Any], stage: str) -> str | None:
    stages = state.get("stages", {})
    if not isinstance(stages, dict):
        return None
    value = stages.get(stage, {})
    if not isinstance(value, dict):
        return None
    raw = value.get("status")
    return str(raw) if raw is not None else None


def _qa_contract(
    paths: TitlePaths,
    *,
    branch: str,
    qa_summary: dict[str, Any],
    font_inventory: dict[str, Any],
    runtime_capabilities: dict[str, bool],
) -> tuple[list[dict[str, Any]], list[str]]:
    state = read_json(paths.state)
    renderer = qa_summary.get("renderer", {})
    if not isinstance(renderer, dict):
        renderer = {}
    fonts = qa_summary.get("fonts", {})
    if not isinstance(fonts, dict):
        fonts = {}

    qa: list[dict[str, Any]] = []
    deferred: list[str] = []

    qa.append(
        _qa_item(
            "human-review",
            "passed" if _stage_status(state, "human_review") == "passed" else "failed",
            evidence={"stage": _stage_status(state, "human_review")},
        )
    )
    qa.append(
        _qa_item(
            "deterministic-qa",
            "passed" if bool(qa_summary.get("ok")) else "failed",
            evidence={"qa_stage": _stage_status(state, "qa")},
        )
    )
    qa.append(
        _qa_item(
            "exact-font-audit",
            "passed" if bool(fonts.get("ok")) else "failed",
            evidence={
                "resolved_attachments": len(fonts.get("attachments", [])),
                "missing": len(fonts.get("missing", [])),
            },
        )
    )
    qa.append(
        _qa_item(
            "registered-font-assets",
            "passed" if bool(font_inventory.get("ok")) else "failed",
            evidence={
                "registered": len(font_inventory.get("installed", [])),
                "errors": font_inventory.get("errors", []),
            },
        )
    )

    renderer_status = str(renderer.get("status", "not-run"))
    if renderer_status == "passed" and bool(renderer.get("ok")):
        qa.append(
            _qa_item(
                "synthetic-libass-render",
                "passed",
                reason=str(renderer.get("statement") or "FFmpeg/libass synthetic render passed."),
                evidence={"canvas": renderer.get("canvas"), "renderer": renderer.get("renderer")},
            )
        )
    elif renderer_status == "failed":
        qa.append(
            _qa_item(
                "synthetic-libass-render",
                "failed",
                reason="FFmpeg/libass synthetic renderer QA failed.",
                evidence=renderer.get("errors", []),
            )
        )
    else:
        reason = str(renderer.get("reason") or "FFmpeg/libass synthetic rendering was not run.")
        qa.append(_qa_item("synthetic-libass-render", "deferred", reason=reason))
        deferred.append("synthetic-libass-render")

    semantic_stage = _stage_status(state, "semantic_qa")
    if semantic_stage == "passed":
        qa.append(_qa_item("semantic-qa-signoff", "passed", evidence={"stage": semantic_stage}))
    else:
        qa.append(
            _qa_item(
                "semantic-qa-signoff",
                "deferred",
                reason="Archival semantic QA sign-off is not complete in this portable bundle.",
                evidence={"stage": semantic_stage},
            )
        )
        deferred.append("semantic-qa-signoff")

    visual_stage = _stage_status(state, f"visual_{branch}")
    if runtime_capabilities.get("full_video") and visual_stage == "passed":
        qa.append(_qa_item("full-video-visual-qa", "passed", evidence={"stage": visual_stage}))
        qa.append(_qa_item("scene-occlusion", "passed", evidence={"stage": visual_stage}))
    else:
        reason = "Full-video scene-aware visual QA requires readable source video and explicit approval."
        qa.append(_qa_item("full-video-visual-qa", "deferred", reason=reason))
        qa.append(_qa_item("scene-occlusion", "deferred", reason=reason))
        deferred.extend(["full-video-visual-qa", "scene-occlusion"])

    remux_stage = _stage_status(state, "remux")
    if runtime_capabilities.get("mkvtoolnix") and remux_stage == "passed":
        qa.append(_qa_item("mkv-remux", "passed", evidence={"stage": remux_stage}))
    else:
        qa.append(
            _qa_item(
                "mkv-remux",
                "deferred",
                reason=(
                    "MKV remux/attachment verification belongs to a runtime with the target "
                    "media and MKVToolNix."
                ),
                evidence={"stage": remux_stage},
            )
        )
        deferred.append("mkv-remux")

    return qa, sorted(set(deferred))


def _zip_deterministic(bundle_dir: Path, archive_path: Path) -> str:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in sorted(bundle_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(bundle_dir).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return sha256_file(archive_path)


def build_portable_release_bundle(
    paths: TitlePaths,
    *,
    branch: str,
    source_root: Path,
    bundle_dir: Path,
    runtime: str = "other",
    runtime_capabilities: dict[str, bool] | None = None,
    job: dict[str, Any] | None = None,
    archive_path: Path | None = None,
) -> PortableBundleResult:
    """Build a truthful portable deliverable without weakening archival Release gates.

    The bundle may contain a usable compiled ASS, exact-font evidence and real FFmpeg/libass
    synthetic renders even when full-video visual QA, semantic sign-off, or MKV remux remain
    deferred. It never marks those archival checks as passed unless their durable Core stages are
    actually complete.
    """
    source_root = source_root.expanduser().resolve()
    bundle_dir = bundle_dir.expanduser().resolve()
    runtime_capabilities = dict(runtime_capabilities or {})
    if runtime not in {"local", "chatgpt-web", "other"}:
        raise ValidationError(f"Unknown portable runtime: {runtime}")
    if branch not in {"clean", "tw", "jp"}:
        raise ValidationError(f"Unknown portable release branch: {branch}")

    ass_path = paths.release / branch_release_filename(paths.title_id, branch)
    if not ass_path.is_file():
        raise GateError(f"Compiled ASS is missing for portable bundle: {ass_path}")
    qa_path = paths.qa / "summary.json"
    if not qa_path.is_file():
        raise GateError("Deterministic QA is missing; run QA before building a portable bundle")
    qa_summary = read_json(qa_path)
    if not bool(qa_summary.get("ok")):
        raise GateError("Deterministic QA failed; refusing to package a portable subtitle bundle")

    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)
    outputs: list[dict[str, str]] = []

    subtitle_destination = bundle_dir / "subtitles" / ass_path.name
    outputs.append(
        _copy_output(ass_path, subtitle_destination, bundle_root=bundle_dir, kind="ass")
    )

    render_summary = qa_summary.get("renderer", {})
    if not isinstance(render_summary, dict):
        render_summary = {}
    branch_render = render_summary.get("branches", {}).get(branch, {})
    if isinstance(branch_render, dict):
        for frame in branch_render.get("frames", []):
            if not isinstance(frame, dict) or not frame.get("file"):
                continue
            source = paths.title / str(frame["file"])
            if not source.is_file():
                raise GateError(f"Renderer QA frame is missing: {source}")
            destination = bundle_dir / "renders" / source.name
            outputs.append(
                _copy_output(source, destination, bundle_root=bundle_dir, kind="render")
            )

    portable_qa_summary = _portableize_paths(
        qa_summary,
        title_root=paths.title,
        workspace_root=paths.repo,
        source_root=source_root,
    )
    reports_dir = bundle_dir / "reports"
    outputs.append(
        _write_report_output(
            reports_dir / "qa.json",
            portable_qa_summary,
            bundle_root=bundle_dir,
        )
    )
    font_report = portable_qa_summary.get("fonts", {})
    if not isinstance(font_report, dict):
        font_report = {}
    outputs.append(
        _write_report_output(reports_dir / "fonts.json", font_report, bundle_root=bundle_dir)
    )
    portable_render_summary = portable_qa_summary.get("renderer", {})
    outputs.append(
        _write_report_output(
            reports_dir / "render.json",
            portable_render_summary,
            bundle_root=bundle_dir,
        )
    )

    change_rows = _changes(paths, branch)
    changes_path = reports_dir / "changes.jsonl"
    _write_jsonl(changes_path, change_rows)
    outputs.append(
        {
            "path": changes_path.relative_to(bundle_dir).as_posix(),
            "sha256": sha256_file(changes_path),
            "kind": "report",
        }
    )

    font_inventory_raw = verify_registered_fonts(source_root)
    font_inventory = _portableize_paths(
        font_inventory_raw,
        title_root=paths.title,
        workspace_root=paths.repo,
        source_root=source_root,
    )
    outputs.append(
        _write_report_output(
            reports_dir / "registered-fonts.json",
            font_inventory,
            bundle_root=bundle_dir,
        )
    )

    qa_items, deferred = _qa_contract(
        paths,
        branch=branch,
        qa_summary=qa_summary,
        font_inventory=font_inventory_raw,
        runtime_capabilities=runtime_capabilities,
    )

    title_config = read_json(paths.title_config)
    repository = dict(job.get("repository", {})) if isinstance(job, dict) else {}
    research_snapshot = (
        read_json(paths.research_snapshot) if paths.research_snapshot.is_file() else {}
    )
    research_packs: list[dict[str, Any]] = []
    for digest in research_snapshot.get("pack_digests", []):
        research_packs.append({"digest": digest})
    if repository.get("research_pack_path") and research_packs:
        research_packs[0]["path"] = str(repository["research_pack_path"])

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "created_at": None,
        "title": {
            "project_id": paths.project_id,
            "title_id": paths.title_id,
            "series_id": title_config.get("series_id"),
            "display_name": str(title_config.get("display_name") or paths.title_id),
        },
        "intent": str(job.get("intent", branch) if isinstance(job, dict) else branch),
        "engine": {
            "name": "SubtitleFlow",
            "version": _engine_version(),
            "runtime": runtime,
        },
        "repository_evidence": {
            "full_name": str(repository.get("full_name") or "kiwi4814/SubtitleFlow"),
            "ref": repository.get("ref"),
            "commit_sha": repository.get("commit_sha"),
            "paths": [
                value
                for value in [repository.get("evidence_root"), repository.get("research_pack_path")]
                if isinstance(value, str) and value
            ],
            "research_packs": research_packs,
        },
        "inputs": _source_inputs(paths),
        "outputs": outputs,
        "qa": qa_items,
        "canon_gaps": 0,
        "deferred": deferred,
        "portable": {
            "branch": branch,
            "archival_release_frozen": False,
            "statement": (
                "Portable subtitle deliverable. Deferred archival checks are explicit and Core "
                "Release gates remain authoritative."
            ),
            "runtime_capabilities": runtime_capabilities,
        },
    }

    _validate_manifest(manifest, source_root=source_root)
    write_json(bundle_dir / "manifest.json", manifest)

    summary_lines = [
        f"# SubtitleFlow portable bundle — {manifest['title']['display_name']}",
        "",
        f"- Branch: `{branch}`",
        f"- Intent: `{manifest['intent']}`",
        f"- Runtime: `{runtime}`",
        f"- Compiled ASS: `{subtitle_destination.name}`",
        f"- Renderer frames: {sum(item['kind'] == 'render' for item in outputs)}",
        f"- Recorded changes: {len(change_rows)}",
        f"- Deferred archival checks: {', '.join(deferred) if deferred else 'none'}",
        "",
        "This package does not claim archival Release Freeze while required checks remain deferred.",
        "",
    ]
    summary_path = reports_dir / "summary.md"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8", newline="")
    outputs.append(
        {
            "path": summary_path.relative_to(bundle_dir).as_posix(),
            "sha256": sha256_file(summary_path),
            "kind": "report",
        }
    )

    manifest["outputs"] = outputs
    _validate_manifest(manifest, source_root=source_root)
    write_json(bundle_dir / "manifest.json", manifest)

    archive_sha: str | None = None
    archive_value: str | None = None
    if archive_path is not None:
        archive_path = archive_path.expanduser().resolve()
        archive_sha = _zip_deterministic(bundle_dir, archive_path)
        archive_value = str(archive_path)

    return PortableBundleResult(
        bundle_dir=str(bundle_dir),
        archive=archive_value,
        archive_sha256=archive_sha,
        manifest=manifest,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a SubtitleFlow portable release bundle")
    parser.add_argument("project")
    parser.add_argument("title")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--branch", choices=["clean", "tw", "jp"], default="clean")
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--runtime", choices=["local", "chatgpt-web", "other"], default="other")
    args = parser.parse_args(argv)
    paths = title_paths(args.repo.resolve(), args.project, args.title)
    result = build_portable_release_bundle(
        paths,
        branch=args.branch,
        source_root=args.source_root,
        bundle_dir=args.bundle_dir,
        runtime=args.runtime,
        archive_path=args.archive,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

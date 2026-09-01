from __future__ import annotations

from typing import Any

from . import __version__
from .errors import GateError
from .fonts import require_font_attachments
from .gates import (
    validate_research_evidence,
    validate_semantic_qa_evidence,
    validate_visual_qa_evidence,
)
from .io import read_json, write_json
from .qa import qa_input_snapshot
from .review import list_candidates, unimported_proposal_files
from .srp.registry import load_bindings, research_mode
from .srp.resolver import ensure_resolved
from .state import update_stage
from .style import load_style_profile
from .util import sha256_file, utc_now
from .workflow import active_branches
from .workspace import TitlePaths, effective_series_id, verify_sources


def create_release_manifest(paths: TitlePaths) -> dict[str, Any]:
    mode = research_mode(paths)
    if mode in {"advisory", "enforce"}:
        ensure_resolved(paths)
    qa_path = paths.qa / "summary.json"
    if not qa_path.exists():
        raise GateError("Release blocked: QA summary is missing")
    qa = read_json(qa_path)
    if not qa.get("ok"):
        raise GateError("Release blocked: QA did not pass")
    expected_snapshot = qa.get("input_snapshot")
    current_snapshot = qa_input_snapshot(paths)
    if not isinstance(expected_snapshot, dict) or expected_snapshot != current_snapshot:
        raise GateError(
            "Release blocked: QA is stale because subtitle/canon/config/style/font/review inputs changed; rerun compile and QA"
        )
    decisions = list_candidates(paths)
    if any(item.status == "pending" for item in decisions):
        raise GateError("Release blocked: human review candidates are pending")
    unimported = unimported_proposal_files(paths)
    if unimported:
        names = ", ".join(str(path.relative_to(paths.title)) for path in unimported)
        raise GateError("Release blocked: semantic proposal files have not been imported: " + names)
    integrity = verify_sources(paths)
    project = read_json(paths.project_config)
    title = read_json(paths.title_config)
    state = read_json(paths.state)
    stages = state.get("stages", {})
    gates = title.get("quality_gates", {})
    branches = active_branches(paths)
    blockers: list[str] = []
    research_evidence: dict[str, Any] | None = None
    semantic_evidence: dict[str, Any] | None = None
    visual_evidence: dict[str, dict[str, Any]] = {}
    if stages.get("alignment_and_seed", {}).get("status") != "passed":
        blockers.append("alignment/workfile stage is not passed")
    for branch in branches:
        if stages.get(f"compile_{branch}", {}).get("status") != "passed":
            blockers.append(f"{branch} compile stage is not passed")
    if stages.get("qa", {}).get("status") != "passed":
        blockers.append("deterministic QA stage is not passed")
    research_required = mode == "enforce" or (
        mode == "legacy" and gates.get("require_research", True)
    )
    if research_required:
        try:
            research_evidence = validate_research_evidence(paths)
        except GateError as exc:
            blockers.append(str(exc))
    if gates.get("require_semantic_qa", True):
        try:
            semantic_evidence = validate_semantic_qa_evidence(paths)
        except GateError as exc:
            blockers.append(str(exc))
    if gates.get("require_visual_qa", True):
        for branch in branches:
            try:
                visual_evidence[branch] = validate_visual_qa_evidence(paths, branch)
            except GateError as exc:
                blockers.append(str(exc))

    font_attachments: list[dict[str, Any]] = []
    fonts_required = bool(
        gates.get("require_fonts", True) or title.get("fonts", {}).get("require_for_release", True)
    )
    if stages.get("fonts", {}).get("status") == "passed":
        try:
            font_attachments = require_font_attachments(paths)
        except GateError as exc:
            if fonts_required:
                blockers.append(str(exc))
    elif fonts_required:
        blockers.append("font audit gate is not passed")
    if blockers:
        raise GateError("Release blocked: " + "; ".join(blockers))

    release_files = sorted(
        path for path in paths.release.glob("*.ass") if not path.name.endswith(".preview.ass")
    )
    if not release_files:
        raise GateError("Release blocked: no compiled ASS files")
    files = [
        {"name": path.name, "sha256": sha256_file(path), "size": path.stat().st_size}
        for path in release_files
    ]
    style_profile = load_style_profile(paths)
    research_snapshot = (
        read_json(paths.research_snapshot)
        if mode in {"advisory", "enforce"} and paths.research_snapshot.exists()
        else None
    )
    research_manifest: dict[str, Any] = {"mode": mode}
    if research_snapshot is not None:
        research_manifest.update(
            {
                "bindings": [
                    {
                        "pack_id": item.get("pack_id"),
                        "pack_version": item.get("pack_version"),
                        "pack_digest": item.get("pack_digest"),
                    }
                    for item in load_bindings(paths).get("bindings", [])
                    if item.get("enabled", True)
                ],
                "series_id": research_snapshot.get("series_id", effective_series_id(paths)),
                "effective_semantic_sha256": research_snapshot.get("effective_semantic_sha256"),
                "provenance_sha256": research_snapshot.get("provenance_sha256"),
                "blocking_unresolved": research_snapshot.get("blocking_unresolved", 0),
                "blocking_conflicts": research_snapshot.get("blocking_conflicts", 0),
                "gate": (
                    stages.get("research", {}).get("status") if mode == "enforce" else "advisory"
                ),
            }
        )
    elif mode == "legacy":
        research_manifest["gate"] = stages.get("research", {}).get("status")

    manifest = {
        "schema_version": 4,
        "created_at": utc_now(),
        "project_id": paths.project_id,
        "title_id": paths.title_id,
        "series_id": effective_series_id(paths),
        "display_name": title.get("display_name"),
        "workflow_profile": title.get("workflow", {}).get("profile", "auto"),
        "branches": branches,
        "engine": {"name": "subtitleflow", "version": __version__},
        "research": research_manifest,
        "style": {
            "profile": style_profile.get("id"),
            "display_name": style_profile.get("display_name"),
        },
        "canon_version": project.get("canon_version"),
        "source_integrity": integrity,
        "review": {
            "approved": sum(item.status == "approved" for item in decisions),
            "rejected": sum(item.status == "rejected" for item in decisions),
            "pending": sum(item.status == "pending" for item in decisions),
        },
        "files": files,
        "font_attachments": font_attachments,
        "media": {
            "video": next(iter(visual_evidence.values()))["video"] if visual_evidence else None
        },
        "qa_summary_sha256": sha256_file(qa_path),
        "qa_input_snapshot": current_snapshot,
        "quality_gates": {
            "research": stages.get("research"),
            "semantic_qa": stages.get("semantic_qa"),
            "fonts": stages.get("fonts"),
            "visual": {branch: stages.get(f"visual_{branch}") for branch in branches},
        },
        "gate_evidence": {
            "research": research_evidence,
            "semantic_qa": semantic_evidence,
            "visual": visual_evidence,
        },
    }
    write_json(paths.release / "release-manifest.json", manifest)
    sums = "".join(f"{item['sha256']}  {item['name']}\n" for item in files)
    (paths.release / "SHA256SUMS").write_text(sums, encoding="utf-8")
    update_stage(
        paths,
        "release",
        "passed",
        files=[item["name"] for item in files],
        fonts=[item["attachment_name"] for item in font_attachments],
    )
    return manifest

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import __version__
from .errors import GateError
from .io import read_json, write_json
from .qa import qa_input_snapshot
from .review import list_candidates
from .state import update_stage
from .util import sha256_file, utc_now
from .workspace import TitlePaths, verify_sources


def create_release_manifest(paths: TitlePaths) -> dict[str, Any]:
    qa_path = paths.qa / "summary.json"
    if not qa_path.exists():
        raise GateError("Release blocked: QA summary is missing")
    qa = read_json(qa_path)
    if not qa.get("ok"):
        raise GateError("Release blocked: QA did not pass")
    expected_snapshot = qa.get("input_snapshot")
    current_snapshot = qa_input_snapshot(paths)
    if not isinstance(expected_snapshot, dict) or expected_snapshot != current_snapshot:
        raise GateError("Release blocked: QA is stale because subtitle/canon/config/review inputs changed; rerun compile and QA")
    decisions = list_candidates(paths)
    if any(item.status == "pending" for item in decisions):
        raise GateError("Release blocked: human review candidates are pending")
    integrity = verify_sources(paths)
    project = read_json(paths.project_config)
    title = read_json(paths.title_config)
    state = read_json(paths.state)
    stages = state.get("stages", {})
    gates = title.get("quality_gates", {})
    blockers: list[str] = []
    if stages.get("alignment_and_seed", {}).get("status") != "passed":
        blockers.append("alignment/workfile stage is not passed")
    if title.get("tw_branch", {}).get("enabled", True) and stages.get("compile_tw", {}).get("status") != "passed":
        blockers.append("TW compile stage is not passed")
    if title.get("jp_branch", {}).get("enabled", True) and stages.get("compile_jp", {}).get("status") != "passed":
        blockers.append("JP compile stage is not passed")
    if stages.get("qa", {}).get("status") != "passed":
        blockers.append("deterministic QA stage is not passed")
    if gates.get("require_research", True):
        if stages.get("research", {}).get("status") != "passed":
            blockers.append("research gate is not passed")
        for name in ("context.md", "sources.md"):
            evidence = paths.research / name
            if not evidence.is_file() or not evidence.read_text(encoding="utf-8", errors="replace").strip():
                blockers.append(f"research evidence is missing: {name}")
    if gates.get("require_semantic_qa", True):
        if stages.get("semantic_qa", {}).get("status") != "passed":
            blockers.append("semantic QA gate is not passed")
        semantic_report = paths.qa / "semantic-review.md"
        if not semantic_report.is_file() or not semantic_report.read_text(encoding="utf-8", errors="replace").strip():
            blockers.append("semantic QA evidence is missing: qa/semantic-review.md")
    if gates.get("require_visual_qa", True):
        if not title.get("media", {}).get("video"):
            blockers.append("visual QA requires media.video to be configured")
        if title.get("tw_branch", {}).get("enabled", True):
            if stages.get("visual_tw", {}).get("status") != "passed":
                blockers.append("TW visual QA gate is not passed")
            if not any((paths.qa / "previews" / "tw").glob("*.png")):
                blockers.append("TW visual QA evidence has no preview PNGs")
        if title.get("jp_branch", {}).get("enabled", True):
            if stages.get("visual_jp", {}).get("status") != "passed":
                blockers.append("JP visual QA gate is not passed")
            if not any((paths.qa / "previews" / "jp").glob("*.png")):
                blockers.append("JP visual QA evidence has no preview PNGs")
    if blockers:
        raise GateError("Release blocked: " + "; ".join(blockers))
    release_files = sorted(
        path for path in paths.release.glob("*.ass") if not path.name.endswith(".preview.ass")
    )
    if not release_files:
        raise GateError("Release blocked: no compiled ASS files")
    files = [
        {
            "name": path.name,
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in release_files
    ]
    manifest = {
        "schema_version": 1,
        "created_at": utc_now(),
        "project_id": paths.project_id,
        "title_id": paths.title_id,
        "display_name": title.get("display_name"),
        "engine": {"name": "subtitleflow", "version": __version__},
        "canon_version": project.get("canon_version"),
        "source_integrity": integrity,
        "review": {
            "approved": sum(item.status == "approved" for item in decisions),
            "rejected": sum(item.status == "rejected" for item in decisions),
            "pending": sum(item.status == "pending" for item in decisions),
        },
        "files": files,
        "qa_summary_sha256": sha256_file(qa_path),
        "qa_input_snapshot": current_snapshot,
        "quality_gates": {
            "research": stages.get("research"),
            "semantic_qa": stages.get("semantic_qa"),
            "visual_tw": stages.get("visual_tw"),
            "visual_jp": stages.get("visual_jp"),
        },
    }
    write_json(paths.release / "release-manifest.json", manifest)
    sums = "".join(f"{item['sha256']}  {item['name']}\n" for item in files)
    (paths.release / "SHA256SUMS").write_text(sums, encoding="utf-8")
    update_stage(paths, "release", "passed", files=[item["name"] for item in files])
    return manifest

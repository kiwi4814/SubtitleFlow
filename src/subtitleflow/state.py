from __future__ import annotations

from typing import Any, Iterable

from .io import read_json, write_json
from .util import utc_now
from .workspace import TitlePaths


def update_stage(paths: TitlePaths, stage: str, status: str, **details: Any) -> None:
    data = read_json(paths.state)
    stages = data.setdefault("stages", {})
    stages[stage] = {"status": status, "updated_at": utc_now(), **details}
    data["updated_at"] = utc_now()
    write_json(paths.state, data)


def invalidate_stages(paths: TitlePaths, stages_to_invalidate: Iterable[str], *, reason: str) -> None:
    """Mark only previously-created downstream stages stale; do not fabricate unrun stages."""
    data = read_json(paths.state)
    stages = data.setdefault("stages", {})
    changed = False
    for stage in stages_to_invalidate:
        if stage not in stages:
            continue
        stages[stage] = {
            "status": "stale",
            "updated_at": utc_now(),
            "reason": reason,
        }
        changed = True
    if changed:
        data["updated_at"] = utc_now()
        write_json(paths.state, data)


def invalidate_after_prepare(paths: TitlePaths, *, reason: str = "workfiles regenerated") -> None:
    invalidate_stages(
        paths,
        ("compile_clean", "compile_tw", "compile_jp", "fonts", "qa", "semantic_qa", "render_clean", "render_tw", "render_jp", "visual_clean", "visual_tw", "visual_jp", "release", "remux"),
        reason=reason,
    )


def invalidate_after_compile(paths: TitlePaths, *, reason: str = "compiled ASS regenerated") -> None:
    invalidate_stages(
        paths,
        ("fonts", "qa", "semantic_qa", "render_clean", "render_tw", "render_jp", "visual_clean", "visual_tw", "visual_jp", "release", "remux"),
        reason=reason,
    )


def invalidate_after_qa(paths: TitlePaths, *, reason: str = "deterministic QA rerun") -> None:
    invalidate_stages(
        paths,
        ("semantic_qa", "render_clean", "render_tw", "render_jp", "visual_clean", "visual_tw", "visual_jp", "release", "remux"),
        reason=reason,
    )


def invalidate_after_review_change(paths: TitlePaths, *, reason: str = "human review state changed") -> None:
    invalidate_stages(
        paths,
        ("compile_clean", "compile_tw", "compile_jp", "fonts", "qa", "semantic_qa", "render_clean", "render_tw", "render_jp", "visual_clean", "visual_tw", "visual_jp", "release", "remux"),
        reason=reason,
    )


def invalidate_after_source_or_canon_change(paths: TitlePaths, *, reason: str) -> None:
    invalidate_stages(
        paths,
        ("research_resolve", "research", "normalize", "alignment_and_seed", "compile_clean", "compile_tw", "compile_jp", "fonts", "qa", "semantic_qa", "render_clean", "render_tw", "render_jp", "visual_clean", "visual_tw", "visual_jp", "release", "remux"),
        reason=reason,
    )


def state_summary(paths: TitlePaths) -> dict[str, Any]:
    state = read_json(paths.state)
    manifest = read_json(paths.manifest)
    candidate_file = paths.review / "candidates.json"
    candidates = read_json(candidate_file).get("candidates", []) if candidate_file.exists() else []
    pending = sum(1 for item in candidates if item.get("status") == "pending")
    approved = sum(1 for item in candidates if item.get("status") == "approved")
    rejected = sum(1 for item in candidates if item.get("status") == "rejected")
    config = read_json(paths.title_config)
    research_cfg = config.get("research") if isinstance(config.get("research"), dict) else None
    bindings = (
        read_json(paths.research_bindings).get("bindings", [])
        if paths.research_bindings.exists()
        else []
    )
    return {
        "project_id": paths.project_id,
        "title_id": paths.title_id,
        "sources": sorted(manifest.get("sources", {}).keys()),
        "research": {
            "mode": research_cfg.get("mode", "off") if research_cfg is not None else "legacy",
            "branch_map": research_cfg.get("branch_map", {}) if research_cfg is not None else {},
            "bindings": bindings,
        },
        "stages": state.get("stages", {}),
        "review": {"pending": pending, "approved": approved, "rejected": rejected},
        "release_files": sorted(path.name for path in paths.release.glob("*.ass")),
        "qa_files": sorted(path.name for path in paths.qa.glob("*.json")),
    }

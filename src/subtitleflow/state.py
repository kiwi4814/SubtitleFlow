from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .io import read_json, write_json
from .util import utc_now
from .workspace import TitlePaths, effective_series_id

_RESEARCH_SEMANTIC_DEPENDENTS = (
    "research",
    "human_review",
    "alignment_and_seed",
    "compile_clean",
    "compile_tw",
    "compile_jp",
    "fonts",
    "qa",
    "semantic_qa",
    "render_clean",
    "render_tw",
    "render_jp",
    "visual_clean",
    "visual_tw",
    "visual_jp",
    "release",
    "remux",
)


def _mark_stale(stages: dict[str, Any], names: Iterable[str], *, reason: str) -> bool:
    changed = False
    timestamp = utc_now()
    for stage in names:
        if stage not in stages:
            continue
        stale = {
            "status": "stale",
            "updated_at": timestamp,
            "reason": reason,
        }
        # Only research_resolve needs its prior semantic digest preserved so a later
        # re-resolve can distinguish semantic changes from provenance-only changes.
        previous = stages.get(stage)
        if stage == "research_resolve" and isinstance(previous, dict) and "evidence" in previous:
            stale["evidence"] = previous["evidence"]
        stages[stage] = stale
        changed = True
    return changed


def update_stage(paths: TitlePaths, stage: str, status: str, **details: Any) -> None:
    data = read_json(paths.state)
    stages = data.setdefault("stages", {})

    # research_resolve carries the effective semantic digest. If a re-resolve changes
    # meaning, every persisted edit/review/output that could have depended on the old
    # Effective Knowledge must become stale. research_resolve invalidation preserves only
    # its prior evidence so this comparison survives bind/unbind marking it stale.
    if stage == "research_resolve" and status == "passed":
        previous = stages.get(stage)
        previous_evidence = previous.get("evidence", {}) if isinstance(previous, dict) else {}
        next_evidence = details.get("evidence", {})
        previous_semantic = (
            previous_evidence.get("effective_semantic_sha256")
            if isinstance(previous_evidence, dict)
            else None
        )
        next_semantic = (
            next_evidence.get("effective_semantic_sha256")
            if isinstance(next_evidence, dict)
            else None
        )
        if previous_semantic and next_semantic and previous_semantic != next_semantic:
            _mark_stale(
                stages,
                _RESEARCH_SEMANTIC_DEPENDENTS,
                reason="effective research semantics changed",
            )

    stages[stage] = {"status": status, "updated_at": utc_now(), **details}
    data["updated_at"] = utc_now()
    write_json(paths.state, data)


def invalidate_stages(
    paths: TitlePaths, stages_to_invalidate: Iterable[str], *, reason: str
) -> None:
    """Mark only previously-created downstream stages stale; preserve resolve semantics."""
    data = read_json(paths.state)
    stages = data.setdefault("stages", {})
    if _mark_stale(stages, stages_to_invalidate, reason=reason):
        data["updated_at"] = utc_now()
        write_json(paths.state, data)


def invalidate_after_prepare(paths: TitlePaths, *, reason: str = "workfiles regenerated") -> None:
    invalidate_stages(
        paths,
        (
            "human_review",
            "compile_clean",
            "compile_tw",
            "compile_jp",
            "fonts",
            "qa",
            "semantic_qa",
            "render_clean",
            "render_tw",
            "render_jp",
            "visual_clean",
            "visual_tw",
            "visual_jp",
            "release",
            "remux",
        ),
        reason=reason,
    )


def invalidate_after_compile(
    paths: TitlePaths, *, reason: str = "compiled ASS regenerated"
) -> None:
    invalidate_stages(
        paths,
        (
            "fonts",
            "qa",
            "semantic_qa",
            "render_clean",
            "render_tw",
            "render_jp",
            "visual_clean",
            "visual_tw",
            "visual_jp",
            "release",
            "remux",
        ),
        reason=reason,
    )


def invalidate_after_qa(paths: TitlePaths, *, reason: str = "deterministic QA rerun") -> None:
    invalidate_stages(
        paths,
        (
            "semantic_qa",
            "render_clean",
            "render_tw",
            "render_jp",
            "visual_clean",
            "visual_tw",
            "visual_jp",
            "release",
            "remux",
        ),
        reason=reason,
    )


def invalidate_after_review_change(
    paths: TitlePaths, *, reason: str = "human review state changed"
) -> None:
    invalidate_stages(
        paths,
        (
            "compile_clean",
            "compile_tw",
            "compile_jp",
            "fonts",
            "qa",
            "semantic_qa",
            "render_clean",
            "render_tw",
            "render_jp",
            "visual_clean",
            "visual_tw",
            "visual_jp",
            "release",
            "remux",
        ),
        reason=reason,
    )


def invalidate_after_research_semantic_change(
    paths: TitlePaths,
    *,
    reason: str = "effective research semantics changed",
) -> None:
    """Stale every persisted decision/output that can depend on effective research meaning."""
    invalidate_stages(paths, _RESEARCH_SEMANTIC_DEPENDENTS, reason=reason)


def invalidate_after_source_or_canon_change(paths: TitlePaths, *, reason: str) -> None:
    invalidate_stages(
        paths,
        (
            "research_resolve",
            "research",
            "normalize",
            "alignment_and_seed",
            "human_review",
            "compile_clean",
            "compile_tw",
            "compile_jp",
            "fonts",
            "qa",
            "semantic_qa",
            "render_clean",
            "render_tw",
            "render_jp",
            "visual_clean",
            "visual_tw",
            "visual_jp",
            "release",
            "remux",
        ),
        reason=reason,
    )


def invalidate_after_series_identity_change(
    paths: TitlePaths,
    *,
    reason: str = "title series identity changed",
) -> None:
    """Stale every artifact whose semantic evidence depends on title series."""
    invalidate_stages(paths, ("research_resolve",), reason=reason)
    invalidate_after_research_semantic_change(paths, reason=reason)


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
        "series_id": effective_series_id(paths),
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

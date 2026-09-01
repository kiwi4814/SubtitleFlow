from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import GateError, ValidationError
from .io import read_json
from .media import current_render_evidence, expand_media_path
from .qa import qa_input_snapshot
from .review import pending_count
from .srp.registry import research_mode
from .srp.resolver import approve_research, validate_native_research_evidence
from .state import invalidate_stages, update_stage
from .util import file_identity, sha256_file
from .workspace import TitlePaths


def _require_nonempty_file(path: Path, label: str) -> None:
    if not path.is_file() or not path.read_text(encoding="utf-8", errors="replace").strip():
        raise GateError(f"{label} is missing or empty: {path}")


def research_evidence_snapshot(paths: TitlePaths) -> dict[str, str]:
    context = paths.research / "context.md"
    sources = paths.research / "sources.md"
    _require_nonempty_file(context, "Research context")
    _require_nonempty_file(sources, "Research sources")
    return {
        "research/context.md": sha256_file(context),
        "research/sources.md": sha256_file(sources),
    }


def _validate_legacy_research_evidence(paths: TitlePaths) -> dict[str, str]:
    state = read_json(paths.state)
    stage = state.get("stages", {}).get("research", {})
    if stage.get("status") != "passed":
        raise GateError("research gate is not passed")
    current = research_evidence_snapshot(paths)
    if stage.get("evidence") != current:
        raise GateError("research gate is stale: research evidence changed after approval")
    return current




def validate_research_evidence(paths: TitlePaths) -> dict[str, Any]:
    mode = research_mode(paths)
    if mode == "legacy":
        return _validate_legacy_research_evidence(paths)
    return validate_native_research_evidence(paths)


def _require_current_qa(paths: TitlePaths) -> tuple[dict[str, Any], dict[str, str]]:
    summary_path = paths.qa / "summary.json"
    if not summary_path.is_file():
        raise GateError("Deterministic QA summary is missing")
    summary = read_json(summary_path)
    if not summary.get("ok"):
        raise GateError("Deterministic QA did not pass")
    state = read_json(paths.state)
    if state.get("stages", {}).get("qa", {}).get("status") != "passed":
        raise GateError("Deterministic QA stage is not passed")
    current = qa_input_snapshot(paths)
    if summary.get("input_snapshot") != current:
        raise GateError("Deterministic QA is stale; rerun compile and QA before approval")
    return summary, current


def semantic_qa_evidence_snapshot(paths: TitlePaths) -> dict[str, Any]:
    summary, current_qa = _require_current_qa(paths)
    report = paths.qa / "semantic-review.md"
    _require_nonempty_file(report, "Semantic QA report")
    config = read_json(paths.title_config)
    evidence: dict[str, Any] = {
        "qa_summary_sha256": sha256_file(paths.qa / "summary.json"),
        "qa_input_snapshot": current_qa,
        "semantic_report_sha256": sha256_file(report),
    }
    mode = research_mode(paths)
    if (
        mode == "enforce"
        or (mode == "legacy" and config.get("quality_gates", {}).get("require_research", True))
    ):
        evidence["research"] = validate_research_evidence(paths)
    return evidence


def validate_semantic_qa_evidence(paths: TitlePaths) -> dict[str, Any]:
    state = read_json(paths.state)
    stage = state.get("stages", {}).get("semantic_qa", {})
    if stage.get("status") != "passed":
        raise GateError("semantic QA gate is not passed")
    current = semantic_qa_evidence_snapshot(paths)
    if stage.get("evidence") != current:
        raise GateError("semantic QA gate is stale: its QA/research/report evidence changed")
    return current


def _configured_video_identity(paths: TitlePaths) -> dict[str, int | str]:
    config = read_json(paths.title_config)
    video = expand_media_path(config.get("media", {}).get("video"))
    if video is None or not video.is_file():
        raise GateError("visual QA requires a readable media.video to be configured")
    return file_identity(video)


def visual_qa_evidence_snapshot(paths: TitlePaths, branch: str) -> dict[str, Any]:
    if branch not in {"clean", "tw", "jp"}:
        raise ValidationError("branch must be clean, tw, or jp")
    _require_current_qa(paths)
    render_evidence = current_render_evidence(paths, branch)
    configured_video = _configured_video_identity(paths)
    if render_evidence.get("video") != configured_video:
        raise GateError(
            f"visual QA cannot approve {branch}: rendered video is not the currently configured media.video"
        )
    return render_evidence


def validate_visual_qa_evidence(paths: TitlePaths, branch: str) -> dict[str, Any]:
    state = read_json(paths.state)
    stage = state.get("stages", {}).get(f"visual_{branch}", {})
    if stage.get("status") != "passed":
        raise GateError(f"{branch} visual QA gate is not passed")
    current = visual_qa_evidence_snapshot(paths, branch)
    if stage.get("evidence") != current:
        raise GateError(f"{branch} visual QA gate is stale: render evidence changed after approval")
    return current


def mark_research_complete(paths: TitlePaths, *, note: str | None = None) -> None:
    if research_mode(paths) != "legacy":
        approve_research(paths, note=note)
        return
    evidence = research_evidence_snapshot(paths)
    invalidate_stages(
        paths,
        ("semantic_qa", "release", "remux"),
        reason="research evidence approved or refreshed",
    )
    update_stage(paths, "research", "passed", note=note, evidence=evidence)


def mark_semantic_qa_complete(paths: TitlePaths, *, note: str | None = None) -> None:
    if pending_count(paths):
        raise GateError("Semantic QA cannot pass while human review candidates are pending")
    evidence = semantic_qa_evidence_snapshot(paths)
    invalidate_stages(paths, ("release", "remux"), reason="semantic QA approved or refreshed")
    update_stage(paths, "semantic_qa", "passed", note=note, evidence=evidence)


def mark_visual_qa_complete(paths: TitlePaths, branch: str, *, note: str | None = None) -> None:
    if branch not in {"clean", "tw", "jp"}:
        raise ValidationError("branch must be clean, tw, or jp")
    config = read_json(paths.title_config)
    if config.get("quality_gates", {}).get("require_semantic_qa", True):
        validate_semantic_qa_evidence(paths)
    evidence = visual_qa_evidence_snapshot(paths, branch)
    invalidate_stages(paths, ("release", "remux"), reason=f"{branch} visual QA approved or refreshed")
    update_stage(paths, f"visual_{branch}", "passed", note=note, frames=len(evidence["frames"]), evidence=evidence)

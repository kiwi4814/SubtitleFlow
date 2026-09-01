from pathlib import Path

import pytest

from conftest import write_ass
from subtitleflow.compile import compile_all
from subtitleflow.errors import GateError
from subtitleflow.gates import mark_research_complete, mark_semantic_qa_complete, mark_visual_qa_complete
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.qa import run_all_qa
from subtitleflow.state import update_stage
from subtitleflow.util import file_identity
from subtitleflow.workfile import build_all_workfiles
from subtitleflow.workspace import (
    add_source,
    configure_workflow_profile,
    create_project,
    create_title,
    title_paths,
)


def _paths(tmp_path: Path):
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    return title_paths(tmp_path, "demo", "movie")


def _prepared_single(tmp_path: Path, *, video: Path | None = None):
    paths = _paths(tmp_path)
    config = read_json(paths.title_config)
    configure_workflow_profile(config, "single")
    config["quality_gates"]["require_fonts"] = False
    config["fonts"]["require_for_release"] = False
    if video is not None:
        config["media"]["video"] = str(video)
    write_json(paths.title_config, config)
    add_source(
        paths,
        "S",
        write_ass(tmp_path / "single.ass", [("0:00:01.00", "0:00:02.00", "字幕")]),
    )
    normalize_all(paths)
    build_all_workfiles(paths)
    compile_all(paths)
    assert run_all_qa(paths)["ok"] is True
    return paths

def _enable_legacy_research(paths) -> None:
    config = read_json(paths.title_config)
    config.pop("research", None)
    config.setdefault("quality_gates", {})["require_research"] = True
    write_json(paths.title_config, config)


def test_legacy_research_gate_requires_evidence_files(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    _enable_legacy_research(paths)
    with pytest.raises(GateError):
        mark_research_complete(paths)
    (paths.research / "context.md").write_text("context\n", encoding="utf-8")
    (paths.research / "sources.md").write_text("sources\n", encoding="utf-8")
    mark_research_complete(paths)
    stage = read_json(paths.state)["stages"]["research"]
    assert stage["status"] == "passed"
    assert set(stage["evidence"]) == {"research/context.md", "research/sources.md"}


def test_semantic_gate_requires_current_qa_and_report_when_research_off(tmp_path: Path) -> None:
    paths = _prepared_single(tmp_path)
    with pytest.raises(GateError):
        mark_semantic_qa_complete(paths)
    (paths.qa / "semantic-review.md").write_text("No unresolved semantic findings.\n", encoding="utf-8")
    mark_semantic_qa_complete(paths)
    stage = read_json(paths.state)["stages"]["semantic_qa"]
    assert stage["status"] == "passed"
    assert stage["evidence"]["semantic_report_sha256"]


def test_semantic_gate_becomes_stale_if_report_changes(tmp_path: Path) -> None:
    from subtitleflow.gates import validate_semantic_qa_evidence

    paths = _prepared_single(tmp_path)
    report = paths.qa / "semantic-review.md"
    report.write_text("No unresolved semantic findings.\n", encoding="utf-8")
    mark_semantic_qa_complete(paths)
    report.write_text("Changed after approval.\n", encoding="utf-8")
    with pytest.raises(GateError, match="stale"):
        validate_semantic_qa_evidence(paths)


def test_visual_gate_requires_current_render_evidence(monkeypatch, tmp_path: Path) -> None:
    import subtitleflow.gates as gates_module

    video = tmp_path / "movie.mkv"
    video.write_bytes(b"video-fixture")
    paths = _prepared_single(tmp_path, video=video)
    config = read_json(paths.title_config)
    config["quality_gates"]["require_research"] = False
    config["quality_gates"]["require_semantic_qa"] = False
    write_json(paths.title_config, config)
    # title.json changed after QA; rerun QA before visual approval.
    assert run_all_qa(paths)["ok"] is True

    with pytest.raises(GateError):
        mark_visual_qa_complete(paths, "clean")

    evidence = {
        "ass": {"path": "release/movie.zh-CN.ass", "sha256": "ass-sha"},
        "video": file_identity(video),
        "fonts": [],
        "frames": {"01.png": "frame-sha"},
    }
    update_stage(paths, "render_clean", "passed", frames=1, evidence=evidence)
    monkeypatch.setattr(gates_module, "current_render_evidence", lambda _paths, _branch: evidence)
    mark_visual_qa_complete(paths, "clean", note="inspected")
    stage = read_json(paths.state)["stages"]["visual_clean"]
    assert stage["status"] == "passed"
    assert stage["evidence"] == evidence

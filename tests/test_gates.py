from pathlib import Path

import pytest

from subtitleflow.errors import GateError
from subtitleflow.gates import mark_research_complete, mark_semantic_qa_complete, mark_visual_qa_complete
from subtitleflow.io import read_json
from subtitleflow.state import update_stage
from subtitleflow.workspace import create_project, create_title, title_paths


def _paths(tmp_path: Path):
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    return title_paths(tmp_path, "demo", "movie")


def test_research_gate_requires_evidence_files(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    with pytest.raises(GateError):
        mark_research_complete(paths)
    (paths.research / "context.md").write_text("context\n", encoding="utf-8")
    (paths.research / "sources.md").write_text("sources\n", encoding="utf-8")
    mark_research_complete(paths)
    assert read_json(paths.state)["stages"]["research"]["status"] == "passed"


def test_semantic_gate_requires_report(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    with pytest.raises(GateError):
        mark_semantic_qa_complete(paths)
    (paths.qa / "semantic-review.md").write_text("No unresolved semantic findings.\n", encoding="utf-8")
    mark_semantic_qa_complete(paths)
    assert read_json(paths.state)["stages"]["semantic_qa"]["status"] == "passed"


def test_visual_gate_requires_rendered_frames(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    with pytest.raises(GateError):
        mark_visual_qa_complete(paths, "jp")
    update_stage(paths, "render_jp", "passed", frames=1)
    with pytest.raises(GateError):
        mark_visual_qa_complete(paths, "jp")
    preview = paths.qa / "previews" / "jp"
    preview.mkdir(parents=True)
    (preview / "01.png").write_bytes(b"not-empty")
    mark_visual_qa_complete(paths, "jp", note="inspected")
    assert read_json(paths.state)["stages"]["visual_jp"]["status"] == "passed"

from pathlib import Path

import pytest

import subtitleflow
from conftest import write_ass
from subtitleflow.compile import compile_all
from subtitleflow.errors import GateError
from subtitleflow.gates import mark_research_complete, mark_semantic_qa_complete
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.qa import run_all_qa
from subtitleflow.release import create_release_manifest
from subtitleflow.workfile import build_all_workfiles
from subtitleflow.workspace import add_source, create_project, create_title, title_paths


def _prepared_title(tmp_path: Path, sample_cues):
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    paths = title_paths(tmp_path, "demo", "movie")
    for role in ("A", "B", "D"):
        add_source(paths, role, write_ass(tmp_path / f"{role}.ass", sample_cues))
    add_source(
        paths,
        "C",
        write_ass(
            tmp_path / "C.ass",
            [(s, e, f"日本語{idx}") for idx, (s, e, _text) in enumerate(sample_cues, start=1)],
        ),
    )
    config = read_json(paths.title_config)
    config["tw_branch"]["traditional_to_simplified"] = False
    write_json(paths.title_config, config)
    normalize_all(paths)
    build_all_workfiles(paths)
    compile_all(paths)
    assert run_all_qa(paths)["ok"] is True
    return paths


def test_release_default_gates_block_incomplete_editorial_work(tmp_path: Path, sample_cues) -> None:
    paths = _prepared_title(tmp_path, sample_cues)
    with pytest.raises(GateError) as exc:
        create_release_manifest(paths)
    message = str(exc.value)
    assert "research gate" in message
    assert "semantic QA gate" in message
    assert "visual QA" in message


def test_release_gates_can_be_explicitly_disabled_for_nonvisual_mechanical_workflow(
    tmp_path: Path, sample_cues
) -> None:
    paths = _prepared_title(tmp_path, sample_cues)
    config = read_json(paths.title_config)
    config["quality_gates"] = {
        "require_research": False,
        "require_semantic_qa": False,
        "require_visual_qa": False,
        "require_fonts": False,
    }
    config["fonts"]["require_for_release"] = False
    write_json(paths.title_config, config)
    assert run_all_qa(paths)["ok"] is True
    manifest = create_release_manifest(paths)
    assert len(manifest["files"]) == 2
    assert manifest["engine"] == {"name": "subtitleflow", "version": subtitleflow.__version__}


def test_release_accepts_completed_nonvisual_gates_when_visual_is_disabled(
    tmp_path: Path, sample_cues
) -> None:
    paths = _prepared_title(tmp_path, sample_cues)
    config = read_json(paths.title_config)
    config["quality_gates"]["require_visual_qa"] = False
    config["quality_gates"]["require_fonts"] = False
    config["fonts"]["require_for_release"] = False
    write_json(paths.title_config, config)
    assert run_all_qa(paths)["ok"] is True
    (paths.research / "context.md").write_text("fixture context\n", encoding="utf-8")
    (paths.research / "sources.md").write_text("fixture sources\n", encoding="utf-8")
    (paths.qa / "semantic-review.md").write_text("no unresolved findings\n", encoding="utf-8")
    mark_research_complete(paths, note="fixture")
    mark_semantic_qa_complete(paths, note="fixture")
    manifest = create_release_manifest(paths)
    assert manifest["quality_gates"]["research"]["status"] == "passed"
    assert manifest["quality_gates"]["semantic_qa"]["status"] == "passed"


def test_release_rejects_stale_qa_after_workfile_change(tmp_path: Path, sample_cues) -> None:
    paths = _prepared_title(tmp_path, sample_cues)
    config = read_json(paths.title_config)
    config["quality_gates"] = {
        "require_research": False,
        "require_semantic_qa": False,
        "require_visual_qa": False,
        "require_fonts": False,
    }
    config["fonts"]["require_for_release"] = False
    write_json(paths.title_config, config)
    assert run_all_qa(paths)["ok"] is True
    work_path = paths.work / "jp.json"
    data = read_json(work_path)
    data["units"][0]["final_text"] += "（changed after QA）"
    write_json(work_path, data)
    with pytest.raises(GateError, match="QA is stale"):
        create_release_manifest(paths)

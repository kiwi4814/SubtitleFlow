from __future__ import annotations

from pathlib import Path

from conftest import write_ass

from subtitleflow.compile import compile_all
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.qa import run_all_qa
from subtitleflow.state import update_stage
from subtitleflow.workfile import build_all_workfiles
from subtitleflow.workspace import add_source, create_project, create_title, title_paths


def _prepared(tmp_path: Path, sample_cues):
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
        write_ass(tmp_path / "C.ass", [(s, e, "日本語") for s, e, _text in sample_cues]),
    )
    cfg = read_json(paths.title_config)
    cfg["tw_branch"]["traditional_to_simplified"] = False
    write_json(paths.title_config, cfg)
    normalize_all(paths)
    build_all_workfiles(paths)
    compile_all(paths)
    run_all_qa(paths)
    return paths


def test_prepare_invalidates_downstream_completed_stages(tmp_path: Path, sample_cues) -> None:
    paths = _prepared(tmp_path, sample_cues)
    update_stage(paths, "semantic_qa", "passed")
    update_stage(paths, "visual_tw", "passed")
    build_all_workfiles(paths)
    stages = read_json(paths.state)["stages"]
    assert stages["alignment_and_seed"]["status"] == "passed"
    assert stages["compile_tw"]["status"] == "stale"
    assert stages["qa"]["status"] == "stale"
    assert stages["semantic_qa"]["status"] == "stale"
    assert stages["visual_tw"]["status"] == "stale"


def test_qa_rerun_invalidates_semantic_and_visual_approvals(tmp_path: Path, sample_cues) -> None:
    paths = _prepared(tmp_path, sample_cues)
    update_stage(paths, "semantic_qa", "passed")
    update_stage(paths, "visual_jp", "passed")
    run_all_qa(paths)
    stages = read_json(paths.state)["stages"]
    assert stages["qa"]["status"] == "passed"
    assert stages["semantic_qa"]["status"] == "stale"
    assert stages["visual_jp"]["status"] == "stale"

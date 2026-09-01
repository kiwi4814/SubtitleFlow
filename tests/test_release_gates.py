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


def test_release_rejects_research_evidence_changed_after_mark(tmp_path: Path, sample_cues) -> None:
    paths = _prepared_title(tmp_path, sample_cues)
    config = read_json(paths.title_config)
    config["quality_gates"]["require_visual_qa"] = False
    config["quality_gates"]["require_fonts"] = False
    config["fonts"]["require_for_release"] = False
    write_json(paths.title_config, config)
    assert run_all_qa(paths)["ok"] is True
    context = paths.research / "context.md"
    context.write_text("fixture context\n", encoding="utf-8")
    (paths.research / "sources.md").write_text("fixture sources\n", encoding="utf-8")
    mark_research_complete(paths)
    (paths.qa / "semantic-review.md").write_text("no unresolved findings\n", encoding="utf-8")
    mark_semantic_qa_complete(paths)
    context.write_text("changed after research approval\n", encoding="utf-8")
    with pytest.raises(GateError, match="research gate is stale"):
        create_release_manifest(paths)


def test_release_rejects_semantic_report_changed_after_mark(tmp_path: Path, sample_cues) -> None:
    paths = _prepared_title(tmp_path, sample_cues)
    config = read_json(paths.title_config)
    config["quality_gates"]["require_visual_qa"] = False
    config["quality_gates"]["require_fonts"] = False
    config["fonts"]["require_for_release"] = False
    write_json(paths.title_config, config)
    assert run_all_qa(paths)["ok"] is True
    (paths.research / "context.md").write_text("fixture context\n", encoding="utf-8")
    (paths.research / "sources.md").write_text("fixture sources\n", encoding="utf-8")
    mark_research_complete(paths)
    semantic = paths.qa / "semantic-review.md"
    semantic.write_text("no unresolved findings\n", encoding="utf-8")
    mark_semantic_qa_complete(paths)
    semantic.write_text("changed after semantic approval\n", encoding="utf-8")
    with pytest.raises(GateError, match="semantic QA gate is stale"):
        create_release_manifest(paths)


def test_release_blocks_unimported_semantic_proposal_even_if_qa_ran_after_it(
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
    proposal = paths.review_proposals / "forgotten.json"
    proposal.write_text('{"not": "imported"}\n', encoding="utf-8")
    assert run_all_qa(paths)["ok"] is True
    with pytest.raises(GateError, match="proposal files have not been imported"):
        create_release_manifest(paths)


def test_new_proposal_after_qa_makes_release_snapshot_stale(tmp_path: Path, sample_cues) -> None:
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
    (paths.review_proposals / "late.json").write_text('{"late": true}\n', encoding="utf-8")
    with pytest.raises(GateError, match="QA is stale"):
        create_release_manifest(paths)


def test_reprepare_after_approval_cannot_silently_release_without_reapplying_decision(
    tmp_path: Path, sample_cues
) -> None:
    from subtitleflow.review import decide_candidate, import_proposals
    from subtitleflow.workfile import load_workfile

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

    unit = load_workfile(paths, "jp").units[0]
    proposal = tmp_path / "approved.json"
    write_json(
        proposal,
        {
            "branch": "jp",
            "unit_id": unit.id,
            "original_text": unit.final_text,
            "proposed_text": unit.final_text + "！",
            "reason": "approved semantic change",
            "confidence": 0.9,
        },
    )
    candidate = import_proposals(paths, proposal)[0]
    decide_candidate(paths, candidate.candidate_id, "approve")
    compile_all(paths)
    assert run_all_qa(paths)["ok"] is True

    # Regenerating workfiles currently rebuilds from deterministic seeds. The approval
    # ledger survives, so QA must detect that its accepted edit is no longer materialized.
    build_all_workfiles(paths)
    compile_all(paths)
    report = run_all_qa(paths)
    assert report["ok"] is False
    assert any(
        error["kind"] == "approved-review-not-materialized"
        for error in report["structural"]["errors"]
    )
    with pytest.raises(GateError):
        create_release_manifest(paths)


def test_manual_series_canon_change_stales_qa_snapshot(tmp_path: Path, sample_cues) -> None:
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

    decisions = read_json(paths.project_canon / "decisions.json")
    decisions["decisions"].append({"decision": "changed canon context"})
    write_json(paths.project_canon / "decisions.json", decisions)
    with pytest.raises(GateError, match="QA is stale"):
        create_release_manifest(paths)


def test_font_map_change_stales_qa_snapshot(tmp_path: Path, sample_cues) -> None:
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
    font_map = tmp_path / "fonts" / "font-map.json"
    font_map.parent.mkdir(parents=True, exist_ok=True)
    write_json(font_map, {"schema_version": 1, "families": {}})
    assert run_all_qa(paths)["ok"] is True

    write_json(font_map, {"schema_version": 1, "families": {"changed": []}})
    with pytest.raises(GateError, match="QA is stale"):
        create_release_manifest(paths)

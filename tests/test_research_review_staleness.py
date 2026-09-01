from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import write_ass

from subtitleflow.compile import compile_all
from subtitleflow.errors import GateError
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.qa import run_all_qa
from subtitleflow.review import decide_candidate, import_proposals
from subtitleflow.srp.archive import import_pack
from subtitleflow.srp.registry import bind_pack, map_branch, set_mode, unbind_pack
from subtitleflow.srp.resolver import resolve_research
from subtitleflow.workfile import build_all_workfiles, load_workfile
from subtitleflow.workspace import add_source, create_project, create_title, title_paths


def _repo(tmp_path: Path):
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    paths = title_paths(tmp_path, "demo", "movie")
    config = read_json(paths.title_config)
    config["workflow"]["profile"] = "single"
    config["quality_gates"]["require_semantic_qa"] = False
    config["quality_gates"]["require_visual_qa"] = False
    config["quality_gates"]["require_fonts"] = False
    config["fonts"]["require_for_release"] = False
    write_json(paths.title_config, config)
    add_source(
        paths,
        "S",
        write_ass(tmp_path / "source.ass", [("0:00:01.00", "0:00:02.00", "任意门")]),
    )
    normalize_all(paths)
    return paths


def _pack(root: Path, *, pack_id: str, canonical: str, source_title: str | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    write_json(
        root / "manifest.json",
        {
            "format": "subtitle-research-pack",
            "schema_version": "1.0",
            "pack_id": pack_id,
            "pack_version": "1.0.0",
            "scope": {"series_id": "demo"},
        },
    )
    term = {
        "id": f"term:{pack_id}",
        "key": "gadget.door",
        "scope": {"level": "series", "series_id": "demo"},
        "source": {"language": "ja-JP", "forms": ["どこでもドア"]},
        "target": {"language": "zh-CN", "value": canonical},
        "enforcement": "locked",
        "status": "accepted",
    }
    (root / "terms.jsonl").write_text(json.dumps(term, ensure_ascii=False) + "\n", encoding="utf-8")
    if source_title is not None:
        source = {
            "id": f"source:{pack_id}",
            "source_class": "official_primary",
            "title": source_title,
            "locator": {"type": "url", "value": f"https://example.com/{pack_id}"},
        }
        evidence = {
            "id": f"evidence:{pack_id}",
            "source_id": source["id"],
            "stance": "supports",
            "claim": "canonical term",
            "related_records": [term["id"]],
        }
        (root / "sources.jsonl").write_text(
            json.dumps(source, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (root / "evidence.jsonl").write_text(
            json.dumps(evidence, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return root


def _import_ref(paths, pack: Path) -> str:
    imported = import_pack(paths, pack)
    return f"{imported['pack_id']}@{imported['pack_version']}#{imported['pack_digest']}"


def _prepare_advisory(paths, pack_ref: str) -> None:
    bind_pack(paths, pack_ref)
    set_mode(paths, "advisory")
    resolve_research(paths)
    build_all_workfiles(paths)
    compile_all(paths)
    assert run_all_qa(paths)["ok"] is True


def test_semantic_rebind_stales_prepare_review_compile_and_qa_chain(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    ref_a = _import_ref(paths, _pack(tmp_path / "a", pack_id="a", canonical="任意门"))
    ref_b = _import_ref(paths, _pack(tmp_path / "b", pack_id="b", canonical="随意门"))
    _prepare_advisory(paths, ref_a)

    state = read_json(paths.state)
    state["stages"]["human_review"] = {"status": "passed", "updated_at": "test"}
    write_json(paths.state, state)

    old_resolve_evidence = read_json(paths.state)["stages"]["research_resolve"]["evidence"]
    unbind_pack(paths, ref_a)
    bind_pack(paths, ref_b)

    stale_resolve = read_json(paths.state)["stages"]["research_resolve"]
    assert stale_resolve["status"] == "stale"
    assert stale_resolve["evidence"] == old_resolve_evidence

    resolve_research(paths)
    stages = read_json(paths.state)["stages"]
    for name in ("alignment_and_seed", "human_review", "compile_clean", "qa"):
        assert stages[name]["status"] == "stale"


def test_provenance_only_rebind_keeps_prepare_and_qa_current_after_resolve(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    ref_a = _import_ref(
        paths,
        _pack(tmp_path / "a", pack_id="a", canonical="任意门", source_title="source-a"),
    )
    ref_b = _import_ref(
        paths,
        _pack(tmp_path / "b", pack_id="b", canonical="任意门", source_title="source-b"),
    )
    _prepare_advisory(paths, ref_a)

    unbind_pack(paths, ref_a)
    bind_pack(paths, ref_b)
    resolve_research(paths)

    stages = read_json(paths.state)["stages"]
    assert stages["alignment_and_seed"]["status"] == "passed"
    assert stages["compile_clean"]["status"] == "passed"
    assert stages["qa"]["status"] == "passed"


def test_pending_proposal_is_bound_to_effective_srp_semantics(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    ref_a = _import_ref(paths, _pack(tmp_path / "a", pack_id="a", canonical="任意门"))
    ref_b = _import_ref(paths, _pack(tmp_path / "b", pack_id="b", canonical="随意门"))
    bind_pack(paths, ref_a)
    set_mode(paths, "advisory")
    resolve_research(paths)
    build_all_workfiles(paths)

    unit = load_workfile(paths, "clean").units[0]
    proposal = tmp_path / "proposal.json"
    write_json(
        proposal,
        {
            "branch": "clean",
            "unit_id": unit.id,
            "original_text": unit.final_text,
            "proposed_text": unit.final_text + "!",
            "reason": "semantic review",
            "confidence": 0.9,
        },
    )
    candidate = import_proposals(paths, proposal)[0]

    unbind_pack(paths, ref_a)
    bind_pack(paths, ref_b)
    resolve_research(paths)

    with pytest.raises(GateError, match="canon, research, or source manifest changed"):
        decide_candidate(paths, candidate.candidate_id, "approve")


def test_research_mode_change_stales_existing_work_chain_immediately(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    ref_a = _import_ref(paths, _pack(tmp_path / "a", pack_id="a", canonical="任意门"))
    _prepare_advisory(paths, ref_a)

    set_mode(paths, "off")
    stages = read_json(paths.state)["stages"]
    assert stages["research_resolve"]["status"] == "stale"
    assert stages["alignment_and_seed"]["status"] == "stale"
    assert stages["compile_clean"]["status"] == "stale"
    assert stages["qa"]["status"] == "stale"


def test_branch_mapping_change_stales_existing_work_chain_immediately(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    ref_a = _import_ref(paths, _pack(tmp_path / "a", pack_id="a", canonical="任意门"))
    _prepare_advisory(paths, ref_a)

    map_branch(paths, "clean", "jp-audio-zh-cn-modern")
    stages = read_json(paths.state)["stages"]
    assert stages["research_resolve"]["status"] == "stale"
    assert stages["alignment_and_seed"]["status"] == "stale"
    assert stages["compile_clean"]["status"] == "stale"
    assert stages["qa"]["status"] == "stale"

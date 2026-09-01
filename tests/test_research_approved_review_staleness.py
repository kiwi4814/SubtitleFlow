from __future__ import annotations

import json
from pathlib import Path

from conftest import write_ass
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.qa import run_all_qa
from subtitleflow.review import decide_candidate, import_proposals
from subtitleflow.srp.archive import import_pack
from subtitleflow.srp.registry import bind_pack, set_mode, unbind_pack
from subtitleflow.srp.resolver import resolve_research
from subtitleflow.workfile import build_all_workfiles, load_workfile
from subtitleflow.workspace import add_source, create_project, create_title, title_paths


def _pack(root: Path, pack_id: str, canonical: str) -> Path:
    root.mkdir(parents=True)
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
    return root


def _import_ref(paths, pack: Path) -> str:
    imported = import_pack(paths, pack)
    return f"{imported['pack_id']}@{imported['pack_version']}#{imported['pack_digest']}"


def test_approved_review_becomes_qa_error_after_srp_semantics_change(tmp_path: Path) -> None:
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

    ref_a = _import_ref(paths, _pack(tmp_path / "a", "a", "任意门"))
    ref_b = _import_ref(paths, _pack(tmp_path / "b", "b", "随意门"))
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
            "proposed_text": unit.final_text + "！",
            "reason": "semantic review",
            "confidence": 0.9,
        },
    )
    candidate = import_proposals(paths, proposal)[0]
    decide_candidate(paths, candidate.candidate_id, "approve")

    unbind_pack(paths, ref_a)
    bind_pack(paths, ref_b)
    resolve_research(paths)

    report = run_all_qa(paths)
    assert report["ok"] is False
    assert any(
        item.get("kind") == "approved-review-context-stale"
        for item in report["structural"]["errors"]
    )

import json
from pathlib import Path

import pytest

from subtitleflow.errors import GateError
from subtitleflow.io import read_json, write_json
from subtitleflow.jobs import prepare_portable_job
from subtitleflow.semantic_packet import build_semantic_packet
from subtitleflow.semantic_proposals import import_semantic_proposal_envelope
from subtitleflow.workspace import title_paths

REPO_ROOT = Path(__file__).resolve().parents[1]


def _prepare(tmp_path):
    target = tmp_path / "target.srt"
    source = tmp_path / "source.srt"
    target.write_text("1\n00:00:01,000 --> 00:00:03,000\n你好\n\n", encoding="utf-8")
    source.write_text("1\n00:00:01,000 --> 00:00:03,000\nこんにちは\n\n", encoding="utf-8")
    job = {
        "schema_version": 1,
        "job_id": "proposal-pilot",
        "project_id": "proposal-project",
        "title_id": "m01",
        "series_id": "proposal-series",
        "display_name": "Proposal Pilot",
        "intent": "jp-audio-zh-cn",
        "inputs": [
            {
                "path": str(target),
                "format": "srt",
                "language": "zh-CN",
                "audio_relation": "jp-audio",
                "evidence_kind": "target-subtitle",
                "role_hint": "S",
                "notes": None,
            },
            {
                "path": str(source),
                "format": "srt",
                "language": "ja-JP",
                "audio_relation": "source-language",
                "evidence_kind": "source-language",
                "role_hint": "C",
                "notes": None,
            },
        ],
        "requirements": {
            "style_profile": "kiwi-collector-v1",
            "editing_policy": "proofread",
            "use_repository_evidence": False,
            "require_exact_fonts": True,
            "render_samples": True,
            "release_zip": True,
            "special_instructions": None,
        },
        "repository": {
            "full_name": "kiwi4814/SubtitleFlow",
            "ref": None,
            "commit_sha": None,
            "evidence_root": "evidence",
        },
    }
    job_path = tmp_path / "job.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    workspace = tmp_path / "workspace"
    prepared = prepare_portable_job(job_path, workspace=workspace, source_root=REPO_ROOT)
    paths = title_paths(workspace, prepared.project_id, prepared.title_id)
    return paths, build_semantic_packet(paths, "clean")


def _proposal(packet, path: Path):
    item = packet["units"][0]
    envelope = {
        "schema_version": 1,
        "kind": "subtitleflow-semantic-proposals",
        "project_id": packet["project_id"],
        "title_id": packet["title_id"],
        "branch": packet["branch"],
        "packet_input_sha256": packet["packet_input_sha256"],
        "producer": "test",
        "notes": None,
        "candidates": [
            {
                "branch": packet["branch"],
                "unit_id": item["unit_id"],
                "original_text": item["current_text"],
                "proposed_text": "您好",
                "change_type": "language-quality",
                "reason": "test material change",
                "confidence": 0.9,
                "severity": "low",
            }
        ],
    }
    path.write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")


def test_packet_bound_envelope_imports_through_existing_human_review(tmp_path):
    paths, packet = _prepare(tmp_path)
    proposal_path = tmp_path / "proposal.json"
    _proposal(packet, proposal_path)

    imported = import_semantic_proposal_envelope(paths, proposal_path)

    assert len(imported) == 1
    assert imported[0].unit_id == packet["units"][0]["unit_id"]
    assert imported[0].status == "pending"
    assert read_json(paths.state)["stages"]["human_review"]["status"] == "blocked"


def test_packet_bound_envelope_rejects_stale_semantic_context_before_import(tmp_path):
    paths, packet = _prepare(tmp_path)
    proposal_path = tmp_path / "proposal.json"
    _proposal(packet, proposal_path)

    config = read_json(paths.title_config)
    config["editorial"]["editing_policy"] = "preserve"
    write_json(paths.title_config, config)

    with pytest.raises(GateError, match="Stale semantic proposal envelope"):
        import_semantic_proposal_envelope(paths, proposal_path)

    assert read_json(paths.review / "candidates.json")["candidates"] == []

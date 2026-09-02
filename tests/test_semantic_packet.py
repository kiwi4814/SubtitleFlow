import json
from pathlib import Path

from subtitleflow.jobs import prepare_portable_job
from subtitleflow.semantic_packet import build_semantic_packet
from subtitleflow.workspace import title_paths

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_semantic_packet_contains_adapter_context_without_mutating_review(tmp_path):
    target = tmp_path / "target.srt"
    source = tmp_path / "source.srt"
    target.write_text("1\n00:00:01,000 --> 00:00:03,000\n你好\n\n", encoding="utf-8")
    source.write_text("1\n00:00:01,000 --> 00:00:03,000\nこんにちは\n\n", encoding="utf-8")

    job = {
        "schema_version": 1,
        "job_id": "packet-pilot",
        "project_id": "packet-project",
        "title_id": "m01",
        "series_id": "packet-series",
        "display_name": "Packet Pilot",
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

    packet = build_semantic_packet(paths, "clean")

    assert packet["kind"] == "subtitleflow-semantic-packet"
    assert packet["series_id"] == "packet-series"
    assert packet["editorial"]["effective_policy"] == "proofread"
    assert packet["research"]["mode"] == "off"
    assert packet["workfile"]["unit_count"] == 1
    assert packet["units"][0]["current_text"] == "你好"
    assert packet["units"][0]["source_text"] == "こんにちは"
    assert packet["proposal_contract"]["human_review_required"] is True
    assert len(packet["packet_input_sha256"]) == 64
    assert len(packet["packet_sha256"]) == 64
    assert not (paths.review / "candidates.json").exists()

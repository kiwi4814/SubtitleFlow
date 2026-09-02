import json
from pathlib import Path

from subtitleflow.io import read_json
from subtitleflow.jobs import (
    infer_workflow_profile,
    prepare_portable_job,
    select_srp_branch_id,
)
from subtitleflow.workspace import title_paths

REPO_ROOT = Path(__file__).resolve().parents[1]


def _input(role: str, path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "format": "srt",
        "language": "zh-CN" if role == "S" else "ja-JP",
        "audio_relation": "jp-audio" if role == "S" else "source-language",
        "evidence_kind": "target-subtitle" if role == "S" else "source-language",
        "role_hint": role,
        "notes": None,
    }


def test_infer_workflow_profile_from_classified_roles():
    assert (
        infer_workflow_profile({"intent": "jp-audio-zh-cn", "inputs": [{"role_hint": "S"}]})
        == "single"
    )
    assert (
        infer_workflow_profile(
            {"intent": "jp-audio-zh-cn", "inputs": [{"role_hint": "S"}, {"role_hint": "C"}]}
        )
        == "source-assisted"
    )
    assert (
        infer_workflow_profile(
            {"intent": "tw-dub-zh-cn", "inputs": [{"role_hint": "A"}, {"role_hint": "D"}]}
        )
        == "dub"
    )
    assert (
        infer_workflow_profile(
            {
                "intent": "jp-audio-zh-cn-ja",
                "inputs": [{"role_hint": "A"}, {"role_hint": "B"}, {"role_hint": "C"}],
            }
        )
        == "bilingual"
    )
    assert (
        infer_workflow_profile(
            {
                "intent": "jp-zh-bilingual",
                "inputs": [{"role_hint": "A"}, {"role_hint": "B"}, {"role_hint": "C"}],
            }
        )
        == "bilingual"
    )


def test_select_srp_branch_id_prefers_release_intent_not_candidate():
    branches = [
        "jp-audio-zh-cn-modern",
        "jp-audio-zh-tw-modern",
        "tw-dub-faithful-zh-hans",
        "tw-dub-2026-modern-zh-hans-candidate",
    ]
    assert (
        select_srp_branch_id(branches, intent="jp-audio-zh-cn", internal_branch="clean")
        == "jp-audio-zh-cn-modern"
    )
    assert (
        select_srp_branch_id(branches, intent="tw-dub-zh-cn", internal_branch="tw")
        == "tw-dub-faithful-zh-hans"
    )


def test_prepare_portable_source_assisted_job_stops_at_planner(tmp_path):
    s = tmp_path / "target.srt"
    c = tmp_path / "source.srt"
    s.write_text("1\n00:00:01,000 --> 00:00:03,000\n你好\n\n", encoding="utf-8")
    c.write_text("1\n00:00:01,000 --> 00:00:03,000\nこんにちは\n\n", encoding="utf-8")

    job = {
        "schema_version": 1,
        "job_id": "test-pilot",
        "project_id": "test-project",
        "title_id": "m01",
        "series_id": "test-series",
        "display_name": "Pilot",
        "intent": "jp-audio-zh-cn",
        "inputs": [_input("S", s), _input("C", c)],
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

    result = prepare_portable_job(
        job_path,
        workspace=workspace,
        source_root=REPO_ROOT,
    ).to_dict()
    paths = title_paths(workspace, "test-project", "m01")
    config = read_json(paths.title_config)

    assert result["project_id"] == "test-project"
    assert result["title_id"] == "m01"
    assert result["series_id"] == "test-series"
    assert result["workflow_profile"] == "source-assisted"
    assert sorted(result["imported_sources"]) == ["C", "S"]
    assert result["state"]["stages"]["normalize"]["status"] == "passed"
    assert result["state"]["stages"]["alignment_and_seed"]["status"] == "passed"
    assert result["next_plan"]["next_action"] == "semantic-edit"
    assert result["repository_evidence"]["requested"] is False
    assert result["repository_evidence"]["bound"] is False
    assert config["style"]["profile"] == str(
        (REPO_ROOT / "styles" / "kiwi-collector-v1.json").resolve()
    )
    assert config["fonts"]["directories"] == [str((REPO_ROOT / "fonts" / "local").resolve())]
    assert config["fonts"]["registry_file"] == str(
        (REPO_ROOT / "fonts" / "font-registry.json").resolve()
    )

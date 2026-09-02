from pathlib import Path

from subtitleflow import pipeline
from subtitleflow.pipeline import RuntimeCapabilities
from subtitleflow.workspace import TitlePaths


def _paths() -> TitlePaths:
    return TitlePaths(repo=Path("/repo"), project_id="p", title_id="t")


def _caps(**overrides: bool) -> RuntimeCapabilities:
    values = {
        "ffmpeg": True,
        "ffmpeg_libass": True,
        "mkvtoolnix": False,
        "full_video": False,
        "exact_fonts": True,
    }
    values.update(overrides)
    return RuntimeCapabilities(**values)


def _patch_common(monkeypatch, stages):
    monkeypatch.setattr(
        pipeline,
        "state_summary",
        lambda _paths: {"stages": stages, "review": {}, "sources": ["S", "C"]},
    )
    monkeypatch.setattr(pipeline, "active_branches", lambda _paths: ["clean"])
    monkeypatch.setattr(pipeline, "unimported_proposal_files", lambda _paths: [])
    monkeypatch.setattr(pipeline, "pending_count", lambda _paths: 0)
    monkeypatch.setattr(
        pipeline,
        "read_json",
        lambda _path: {"quality_gates": {"require_semantic_qa": True, "require_visual_qa": True}},
    )


def test_plan_starts_with_prepare(monkeypatch):
    _patch_common(monkeypatch, {})
    plan = pipeline.plan_title(_paths(), capabilities=_caps())
    assert plan.next_action == "prepare"
    assert plan.can_auto_advance is True
    assert plan.requires_human is False
    assert "full-video-timing-qa" in plan.deferred


def test_plan_requires_semantic_scan_before_compile(monkeypatch):
    _patch_common(
        monkeypatch,
        {"normalize": {"status": "passed"}, "alignment_and_seed": {"status": "passed"}},
    )
    plan = pipeline.plan_title(_paths(), capabilities=_caps())
    assert plan.next_action == "semantic-edit"
    assert plan.requires_human is False
    assert plan.can_auto_advance is True


def test_plan_stops_on_human_review(monkeypatch):
    _patch_common(
        monkeypatch,
        {"normalize": {"status": "passed"}, "alignment_and_seed": {"status": "passed"}},
    )
    monkeypatch.setattr(pipeline, "pending_count", lambda _paths: 3)
    plan = pipeline.plan_title(_paths(), capabilities=_caps())
    assert plan.next_action == "human-review"
    assert plan.requires_human is True
    assert plan.can_auto_advance is False


def test_plan_reaches_release_after_configured_gates(monkeypatch):
    _patch_common(
        monkeypatch,
        {
            "normalize": {"status": "passed"},
            "alignment_and_seed": {"status": "passed"},
            "human_review": {"status": "passed"},
            "compile_clean": {"status": "passed"},
            "qa": {"status": "passed"},
            "semantic_qa": {"status": "passed"},
            "visual_clean": {"status": "passed"},
        },
    )
    plan = pipeline.plan_title(_paths(), capabilities=_caps())
    assert plan.next_action == "release"
    assert plan.can_auto_advance is True
    assert plan.command_hint == "subflow release p t"


def test_complete_without_local_media_does_not_claim_remux(monkeypatch):
    _patch_common(
        monkeypatch,
        {
            "normalize": {"status": "passed"},
            "alignment_and_seed": {"status": "passed"},
            "human_review": {"status": "passed"},
            "compile_clean": {"status": "passed"},
            "qa": {"status": "passed"},
            "semantic_qa": {"status": "passed"},
            "visual_clean": {"status": "passed"},
            "release": {"status": "passed"},
        },
    )
    plan = pipeline.plan_title(_paths(), capabilities=_caps())
    assert plan.next_action == "complete"
    assert "mkv-remux-verification" in plan.deferred

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import write_ass

from subtitleflow.canon import add_term
from subtitleflow.cli import main
from subtitleflow.compile import compile_all
from subtitleflow.errors import GateError, ValidationError
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.qa import run_all_qa
from subtitleflow.release import create_release_manifest
from subtitleflow.srp.archive import import_pack
from subtitleflow.srp.registry import bind_pack, map_branch, set_mode
from subtitleflow.srp.resolver import resolve_research, validate_resolved_snapshot
from subtitleflow.state import update_stage
from subtitleflow.workfile import build_all_workfiles
from subtitleflow.workspace import (
    add_source,
    create_project,
    create_title,
    effective_series_id,
    set_title_series_id,
    title_paths,
)


def _make_repo(
    tmp_path: Path,
    *,
    project_id: str = "demo",
    title_id: str = "movie",
    series_id: str | None = None,
):
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, project_id, project_id)
    create_title(tmp_path, project_id, title_id, title_id, series_id=series_id)
    return title_paths(tmp_path, project_id, title_id)


def _term(
    *,
    rec_id: str,
    key: str,
    value: str,
    series_id: str,
    scope: dict | None = None,
) -> dict:
    return {
        "id": rec_id,
        "key": key,
        "scope": scope or {"level": "series", "series_id": series_id},
        "source": {"language": "ja-JP", "forms": ["原文"]},
        "target": {"language": "zh-CN", "value": value},
        "enforcement": "locked",
        "status": "accepted",
    }


def _pack(
    root: Path,
    *,
    pack_id: str,
    series_id: str,
    terms: list[dict] | None = None,
    version: str = "1.0.0",
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    write_json(
        root / "manifest.json",
        {
            "format": "subtitle-research-pack",
            "schema_version": "1.0",
            "pack_id": pack_id,
            "pack_version": version,
            "scope": {"series_id": series_id},
        },
    )
    if terms is not None:
        (root / "terms.jsonl").write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in terms),
            encoding="utf-8",
        )
    return root


def _exact_ref(imported: dict) -> str:
    return f"{imported['pack_id']}@{imported['pack_version']}#{imported['pack_digest']}"


def _add_clean_source(paths, tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    config = read_json(paths.title_config)
    config["workflow"]["profile"] = "single"
    write_json(paths.title_config, config)
    add_source(
        paths,
        "S",
        write_ass(tmp_path / f"{paths.title_id}.ass", [("0:00:01.00", "0:00:02.00", "原文")]),
    )


def _release_ready_title(
    tmp_path: Path,
    *,
    project_id: str = "demo",
    title_id: str = "movie",
    series_id: str | None = None,
):
    paths = _make_repo(
        tmp_path,
        project_id=project_id,
        title_id=title_id,
        series_id=series_id,
    )
    config = read_json(paths.title_config)
    config["workflow"]["profile"] = "single"
    config["quality_gates"] = {
        "require_research": False,
        "require_semantic_qa": False,
        "require_visual_qa": False,
        "require_fonts": False,
    }
    config["fonts"]["require_for_release"] = False
    write_json(paths.title_config, config)
    add_source(
        paths,
        "S",
        write_ass(tmp_path / "input.ass", [("0:00:01.00", "0:00:02.00", "原文")]),
    )
    normalize_all(paths)
    build_all_workfiles(paths)
    compile_all(paths)
    assert run_all_qa(paths)["ok"] is True
    return paths


def test_legacy_title_without_series_id_import_bind_and_resolve(tmp_path: Path) -> None:
    paths = _make_repo(tmp_path)
    config = read_json(paths.title_config)
    config.pop("series_id")
    write_json(paths.title_config, config)
    assert effective_series_id(paths) == "demo"

    pack = _pack(
        tmp_path / "pack",
        pack_id="demo-canon",
        series_id="demo",
        terms=[_term(rec_id="term:demo", key="demo.term", value="甲", series_id="demo")],
    )
    imported = import_pack(paths, pack)
    binding = bind_pack(paths, _exact_ref(imported))
    set_mode(paths, "advisory")
    snapshot = resolve_research(paths)

    assert binding["pack_digest"] == imported["pack_digest"]
    assert snapshot["series_id"] == "demo"
    assert read_json(paths.research_effective)["series_id"] == "demo"


def test_explicit_series_id_import_bind_and_resolve_when_project_differs(tmp_path: Path) -> None:
    paths = _make_repo(
        tmp_path,
        project_id="doraemon",
        title_id="m01",
        series_id="doraemon-theatrical",
    )
    _add_clean_source(paths, tmp_path)
    pack = _pack(
        tmp_path / "pack",
        pack_id="doraemon-canon",
        series_id="doraemon-theatrical",
        terms=[
            _term(
                rec_id="term:doraemon",
                key="character.doraemon",
                value="哆啦A梦",
                series_id="doraemon-theatrical",
            )
        ],
    )
    imported = import_pack(paths, pack)
    bind_pack(paths, _exact_ref(imported))
    set_mode(paths, "advisory")
    snapshot = resolve_research(paths)
    effective = read_json(paths.research_effective)

    assert snapshot["resolver_version"] == 2
    assert snapshot["series_id"] == "doraemon-theatrical"
    assert effective["project_id"] == "doraemon"
    assert effective["series_id"] == "doraemon-theatrical"
    assert effective["resolver_version"] == 2
    assert effective["branches"]["clean"]["terms"][0]["canonical"] == "哆啦A梦"


def test_project_can_import_pack_for_another_series_without_binding(tmp_path: Path) -> None:
    paths = _make_repo(tmp_path, project_id="doraemon", title_id="m01")
    pack = _pack(
        tmp_path / "pack",
        pack_id="side-series-canon",
        series_id="doraemon-theatrical",
    )

    imported = import_pack(paths, pack)
    registry = read_json(paths.project_research_registry)

    assert imported["scope"] == {"series_id": "doraemon-theatrical"}
    assert registry["packs"][0]["scope"] == {"series_id": "doraemon-theatrical"}


def test_bind_rejects_pack_from_other_series(tmp_path: Path) -> None:
    paths = _make_repo(tmp_path, project_id="doraemon", series_id="doraemon-theatrical")
    pack = _pack(tmp_path / "pack", pack_id="other-canon", series_id="other-series")
    imported = import_pack(paths, pack)

    with pytest.raises(ValidationError, match=r"title.*doraemon-theatrical.*other-series"):
        bind_pack(paths, _exact_ref(imported))

    assert read_json(paths.research_bindings)["bindings"] == []


def test_one_project_can_resolve_two_series_without_cross_binding(tmp_path: Path) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "doraemon", "Doraemon")
    create_title(tmp_path, "doraemon", "title-a", "A", series_id="series-a")
    create_title(tmp_path, "doraemon", "title-b", "B", series_id="series-b")
    paths_a = title_paths(tmp_path, "doraemon", "title-a")
    paths_b = title_paths(tmp_path, "doraemon", "title-b")
    _add_clean_source(paths_a, tmp_path / "a")
    _add_clean_source(paths_b, tmp_path / "b")

    pack_a = _pack(
        tmp_path / "pack-a",
        pack_id="canon-a",
        series_id="series-a",
        terms=[_term(rec_id="term:a", key="shared.term", value="甲", series_id="series-a")],
    )
    pack_b = _pack(
        tmp_path / "pack-b",
        pack_id="canon-b",
        series_id="series-b",
        terms=[_term(rec_id="term:b", key="shared.term", value="乙", series_id="series-b")],
    )
    imported_a = import_pack(paths_a, pack_a)
    imported_b = import_pack(paths_b, pack_b)
    bind_pack(paths_a, _exact_ref(imported_a))
    bind_pack(paths_b, _exact_ref(imported_b))
    set_mode(paths_a, "advisory")
    set_mode(paths_b, "advisory")

    resolve_research(paths_a)
    resolve_research(paths_b)
    effective_a = read_json(paths_a.research_effective)
    effective_b = read_json(paths_b.research_effective)

    assert effective_a["series_id"] == "series-a"
    assert effective_b["series_id"] == "series-b"
    assert effective_a["branches"]["clean"]["terms"][0]["canonical"] == "甲"
    assert effective_b["branches"]["clean"]["terms"][0]["canonical"] == "乙"


def test_scope_precedence_uses_title_series_identity(tmp_path: Path) -> None:
    paths = _make_repo(tmp_path, project_id="doraemon", series_id="series-x")
    _add_clean_source(paths, tmp_path)
    series = "series-x"
    title = {"level": "title", "series_id": series, "title_id": "movie"}
    series_branch = {
        "level": "series_branch",
        "series_id": series,
        "branch_id": "jp-audio-zh-cn-modern",
    }
    branch = {
        "level": "branch",
        "series_id": series,
        "title_id": "movie",
        "branch_id": "jp-audio-zh-cn-modern",
    }
    terms = [
        _term(rec_id="series", key="scope.series", value="series", series_id=series),
        _term(rec_id="title-series", key="scope.title", value="series", series_id=series),
        _term(rec_id="title", key="scope.title", value="title", series_id=series, scope=title),
        _term(
            rec_id="series-branch-series",
            key="scope.series-branch",
            value="series",
            series_id=series,
        ),
        _term(
            rec_id="series-branch",
            key="scope.series-branch",
            value="series-branch",
            series_id=series,
            scope=series_branch,
        ),
        _term(rec_id="branch-series", key="scope.branch", value="series", series_id=series),
        _term(
            rec_id="branch-title",
            key="scope.branch",
            value="title",
            series_id=series,
            scope=title,
        ),
        _term(
            rec_id="branch-series-branch",
            key="scope.branch",
            value="series-branch",
            series_id=series,
            scope=series_branch,
        ),
        _term(
            rec_id="branch",
            key="scope.branch",
            value="branch",
            series_id=series,
            scope=branch,
        ),
    ]
    add_term(
        paths,
        scope="project",
        term_id="local-project",
        key="local.project",
        canonical="本地系列",
        aliases=[],
        auto_replace=False,
        context_sensitive=True,
        branches=["clean", "tw", "jp"],
        notes=None,
    )
    add_term(
        paths,
        scope="title",
        term_id="local-title",
        key="local.title",
        canonical="本地作品",
        aliases=[],
        auto_replace=False,
        context_sensitive=True,
        branches=["clean", "tw", "jp"],
        notes=None,
    )
    imported = import_pack(
        paths,
        _pack(tmp_path / "scope-pack", pack_id="scope-canon", series_id=series, terms=terms),
    )
    bind_pack(paths, _exact_ref(imported))
    set_mode(paths, "advisory")
    map_branch(paths, "clean", "jp-audio-zh-cn-modern")
    resolve_research(paths)
    effective = read_json(paths.research_effective)
    resolved = {item["key"]: item for item in effective["branches"]["clean"]["terms"]}

    assert resolved["scope.series"]["canonical"] == "series"
    assert resolved["scope.title"]["canonical"] == "title"
    assert resolved["scope.series-branch"]["canonical"] == "series-branch"
    assert resolved["scope.branch"]["canonical"] == "branch"
    assert resolved["local.project"]["canonical"] == "本地系列"
    assert resolved["local.title"]["canonical"] == "本地作品"
    assert all(item["scope"]["series_id"] == series for item in resolved.values())


def test_old_title_json_series_fallback_is_project_id(tmp_path: Path) -> None:
    paths = _make_repo(tmp_path, project_id="demo", series_id="series-explicit")
    config = read_json(paths.title_config)
    config.pop("series_id")
    write_json(paths.title_config, config)

    assert effective_series_id(paths) == "demo"


def test_set_series_stales_research_and_downstream_without_deleting_files(tmp_path: Path) -> None:
    paths = _make_repo(tmp_path)
    set_mode(paths, "advisory")
    resolve_research(paths)
    for stage in (
        "research",
        "human_review",
        "qa",
        "semantic_qa",
        "release",
        "remux",
    ):
        update_stage(paths, stage, "passed")
    (paths.work / "keep.json").write_text("work", encoding="utf-8")
    (paths.review / "keep.json").write_text("review", encoding="utf-8")
    (paths.release / "keep.ass").write_text("release", encoding="utf-8")

    result = set_title_series_id(paths, "series-new")
    state = read_json(paths.state)

    assert result == {
        "series_id": "series-new",
        "previous_series_id": "demo",
        "changed": True,
    }
    assert effective_series_id(paths) == "series-new"
    for stage in (
        "research_resolve",
        "research",
        "human_review",
        "qa",
        "semantic_qa",
        "release",
        "remux",
    ):
        assert state["stages"][stage]["status"] == "stale"
    with pytest.raises(GateError, match="stale"):
        validate_resolved_snapshot(paths)
    assert paths.research_effective.exists()
    assert paths.research_snapshot.exists()
    assert (paths.work / "keep.json").read_text(encoding="utf-8") == "work"
    assert (paths.review / "keep.json").read_text(encoding="utf-8") == "review"
    assert (paths.release / "keep.ass").read_text(encoding="utf-8") == "release"

    refreshed = resolve_research(paths)
    assert refreshed["series_id"] == "series-new"
    assert read_json(paths.research_effective)["series_id"] == "series-new"
    assert read_json(paths.state)["stages"]["research_resolve"]["status"] == "passed"

    assert set_title_series_id(paths, "series-new")["changed"] is False
    assert read_json(paths.state)["stages"]["research_resolve"]["status"] == "passed"


def test_title_series_cli_init_and_set_are_supported(tmp_path: Path) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    repo = str(tmp_path)
    assert main(["--repo", repo, "project", "init", "doraemon"]) == 0
    assert (
        main(
            [
                "--repo",
                repo,
                "title",
                "init",
                "doraemon",
                "m01",
                "--profile",
                "source-assisted",
                "--series-id",
                "doraemon-theatrical",
            ]
        )
        == 0
    )
    paths = title_paths(tmp_path, "doraemon", "m01")
    assert read_json(paths.title_config)["series_id"] == "doraemon-theatrical"
    assert (
        main(["--repo", repo, "title", "set-series", "doraemon", "m01", "doraemon-theatrical"]) == 0
    )
    assert read_json(paths.title_config)["series_id"] == "doraemon-theatrical"


def test_release_manifest_freezes_explicit_series_identity(tmp_path: Path) -> None:
    paths = _release_ready_title(
        tmp_path,
        project_id="doraemon",
        title_id="m01",
        series_id="doraemon-theatrical",
    )

    manifest = create_release_manifest(paths)

    assert manifest["schema_version"] == 4
    assert manifest["project_id"] == "doraemon"
    assert manifest["title_id"] == "m01"
    assert manifest["series_id"] == "doraemon-theatrical"


def test_release_manifest_legacy_series_falls_back_to_project_id(tmp_path: Path) -> None:
    paths = _release_ready_title(tmp_path, project_id="demo", title_id="movie")
    config = read_json(paths.title_config)
    config.pop("series_id")
    write_json(paths.title_config, config)
    assert run_all_qa(paths)["ok"] is True

    manifest = create_release_manifest(paths)

    assert manifest["project_id"] == "demo"
    assert manifest["title_id"] == "movie"
    assert manifest["series_id"] == "demo"

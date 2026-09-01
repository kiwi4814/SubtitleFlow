from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from conftest import write_ass
from subtitleflow.canon import add_term
from subtitleflow.compile import compile_all
from subtitleflow.errors import GateError, ValidationError
from subtitleflow.gates import mark_research_complete
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.qa import run_all_qa
from subtitleflow.release import create_release_manifest
from subtitleflow.srp.archive import import_pack, materialize_pack_input
from subtitleflow.srp.diff import diff_research
from subtitleflow.srp.registry import bind_pack, map_branch, set_mode, unbind_pack
from subtitleflow.srp.resolver import approve_research, resolve_research
from subtitleflow.workfile import build_all_workfiles
from subtitleflow.workspace import add_source, create_project, create_title, title_paths


def _repo(tmp_path: Path, *, title: str = "movie"):
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", title, title)
    return title_paths(tmp_path, "demo", title)


def _set_profile(paths, profile: str) -> None:
    config = read_json(paths.title_config)
    config["workflow"]["profile"] = profile
    write_json(paths.title_config, config)


def _term(
    *,
    rec_id: str = "term:x",
    key: str = "gadget.x",
    value: str = "任意门",
    scope: dict | None = None,
    forbidden: list[str] | None = None,
) -> dict:
    target = {"language": "zh-CN", "value": value}
    if forbidden:
        target["forbidden"] = forbidden
    return {
        "id": rec_id,
        "key": key,
        "scope": scope or {"level": "series", "series_id": "demo"},
        "source": {"language": "ja-JP", "forms": ["どこでもドア"]},
        "target": target,
        "enforcement": "locked",
        "status": "accepted",
    }


def _pack(
    root: Path,
    *,
    pack_id: str,
    version: str = "1.0.0",
    terms: list[dict] | None = None,
    source_title: str | None = None,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    write_json(
        root / "manifest.json",
        {
            "format": "subtitle-research-pack",
            "schema_version": "1.0",
            "pack_id": pack_id,
            "pack_version": version,
            "scope": {"series_id": "demo"},
        },
    )
    if terms is not None:
        (root / "terms.jsonl").write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in terms),
            encoding="utf-8",
        )
    if source_title is not None:
        source = {
            "id": "source:one",
            "source_class": "official_primary",
            "title": source_title,
            "locator": {"type": "url", "value": "https://example.com/" + source_title},
        }
        evidence = {
            "id": "evidence:one",
            "source_id": "source:one",
            "stance": "supports",
            "claim": "canonical term",
            "related_records": [terms[0]["id"]] if terms else [],
        }
        (root / "sources.jsonl").write_text(
            json.dumps(source, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (root / "evidence.jsonl").write_text(
            json.dumps(evidence, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return root


def _import_and_bind(paths, pack: Path) -> dict:
    imported = import_pack(paths, pack)
    bind_pack(paths, f"{imported['pack_id']}@{imported['pack_version']}")
    return imported


def _single_source(paths, tmp_path: Path, text: str) -> None:
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
        write_ass(tmp_path / f"{paths.title_id}.ass", [("0:00:01.00", "0:00:02.00", text)]),
    )
    normalize_all(paths)


def test_new_title_defaults_to_optional_research_off(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    assert read_json(paths.title_config)["research"] == {"mode": "off", "branch_map": {}}
    assert read_json(paths.project_research_registry) == {"schema_version": 1, "packs": []}
    assert read_json(paths.research_bindings) == {"schema_version": 1, "bindings": []}


def test_import_is_immutable_idempotent_and_registered(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    pack = _pack(tmp_path / "pack", pack_id="canon", terms=[_term()])
    first = import_pack(paths, pack)
    second = import_pack(paths, pack)
    assert first["pack_digest"].startswith("sha256:")
    assert first["already_imported"] is False
    assert second["already_imported"] is True
    registry = read_json(paths.project_research_registry)
    assert len(registry["packs"]) == 1
    stored = paths.project / registry["packs"][0]["path"] / "terms.jsonl"
    assert stored.is_file()


def test_series_branch_resolution_and_title_branch_override(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _set_profile(paths, "full")
    terms = [
        _term(rec_id="term:x:series", key="character.x", value="甲"),
        _term(
            rec_id="term:x:title",
            key="character.x",
            value="乙",
            scope={"level": "title", "series_id": "demo", "title_id": "movie"},
        ),
        _term(
            rec_id="term:x:series-branch",
            key="character.x",
            value="丙",
            scope={"level": "series_branch", "series_id": "demo", "branch_id": "tw-dub-zh-cn"},
        ),
        _term(
            rec_id="term:x:branch",
            key="character.x",
            value="丁",
            scope={
                "level": "branch",
                "series_id": "demo",
                "title_id": "movie",
                "branch_id": "tw-dub-zh-cn",
            },
        ),
    ]
    _import_and_bind(paths, _pack(tmp_path / "scope-pack", pack_id="scope-pack", terms=terms))
    set_mode(paths, "advisory")
    map_branch(paths, "tw", "tw-dub-zh-cn")
    snapshot = resolve_research(paths)
    assert snapshot["blocking_conflicts"] == 0
    effective = read_json(paths.research_effective)
    tw = {item["key"]: item for item in effective["branches"]["tw"]["terms"]}
    jp = {item["key"]: item for item in effective["branches"]["jp"]["terms"]}
    assert tw["character.x"]["canonical"] == "丁"
    assert jp["character.x"]["canonical"] == "乙"


def test_scope_first_then_local_origin_precedence(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _set_profile(paths, "full")
    add_term(
        paths,
        scope="project",
        term_id="local-series",
        key="character.x",
        canonical="甲",
        aliases=[],
        auto_replace=False,
        context_sensitive=True,
        branches=["clean", "tw", "jp"],
        notes=None,
    )
    pack = _pack(
        tmp_path / "title-pack",
        pack_id="title-pack",
        terms=[
            _term(
                rec_id="term:title",
                key="character.x",
                value="乙",
                scope={"level": "title", "series_id": "demo", "title_id": "movie"},
            )
        ],
    )
    _import_and_bind(paths, pack)
    set_mode(paths, "advisory")
    resolve_research(paths)
    effective = read_json(paths.research_effective)
    assert effective["branches"]["jp"]["terms"][0]["canonical"] == "乙"

    add_term(
        paths,
        scope="title",
        term_id="local-title",
        key="character.x",
        canonical="丙",
        aliases=[],
        auto_replace=False,
        context_sensitive=True,
        branches=["clean", "tw", "jp"],
        notes=None,
    )
    resolve_research(paths)
    effective = read_json(paths.research_effective)
    assert effective["branches"]["jp"]["terms"][0]["canonical"] == "丙"
    assert effective["branches"]["jp"]["terms"][0]["origin"] == "local-title"


def test_cross_pack_conflict_blocks_enforce_approval(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _set_profile(paths, "full")
    _import_and_bind(paths, _pack(tmp_path / "a", pack_id="a", terms=[_term(value="甲")]))
    _import_and_bind(paths, _pack(tmp_path / "b", pack_id="b", terms=[_term(rec_id="term:y", value="乙")]))
    set_mode(paths, "enforce")
    snapshot = resolve_research(paths)
    assert snapshot["blocking_conflicts"] == 1
    with pytest.raises(GateError, match="conflicts"):
        approve_research(paths)


def test_advisory_warns_but_enforce_errors_on_srp_forbidden_alias(tmp_path: Path) -> None:
    paths = _repo(tmp_path, title="advisory")
    _single_source(paths, tmp_path, "随意门")
    _import_and_bind(
        paths,
        _pack(
            tmp_path / "advisory-pack",
            pack_id="advisory-pack",
            terms=[_term(forbidden=["随意门"])],
        ),
    )
    set_mode(paths, "advisory")
    build_all_workfiles(paths)
    compile_all(paths)
    report = run_all_qa(paths)
    assert report["ok"] is True
    assert report["terminology"]["warnings"][0]["alias"] == "随意门"

    paths2 = title_paths(tmp_path, "demo", "enforce")
    create_title(tmp_path, "demo", "enforce", "enforce")
    _single_source(paths2, tmp_path, "随意门")
    bind_pack(paths2, "advisory-pack@1.0.0")
    set_mode(paths2, "enforce")
    resolve_research(paths2)
    approve_research(paths2)
    build_all_workfiles(paths2)
    compile_all(paths2)
    report2 = run_all_qa(paths2)
    assert report2["ok"] is False
    assert report2["terminology"]["errors"][0]["alias"] == "随意门"


def test_off_mode_ignores_bound_srp(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _single_source(paths, tmp_path, "随意门")
    _import_and_bind(
        paths,
        _pack(tmp_path / "off-pack", pack_id="off-pack", terms=[_term(forbidden=["随意门"])]),
    )
    build_all_workfiles(paths)
    compile_all(paths)
    report = run_all_qa(paths)
    assert report["ok"] is True
    assert report["terminology"]["hits"] == []


def test_provenance_only_rebind_does_not_stale_qa_after_resolve(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _single_source(paths, tmp_path, "任意门")
    one = _pack(tmp_path / "p1", pack_id="canon-a", terms=[_term()], source_title="source-a")
    two = _pack(tmp_path / "p2", pack_id="canon-b", terms=[_term()], source_title="source-b")
    _import_and_bind(paths, one)
    import_pack(paths, two)
    set_mode(paths, "advisory")
    resolve_research(paths)
    build_all_workfiles(paths)
    compile_all(paths)
    assert run_all_qa(paths)["ok"] is True
    assert read_json(paths.state)["stages"]["qa"]["status"] == "passed"

    unbind_pack(paths, "canon-a@1.0.0")
    bind_pack(paths, "canon-b@1.0.0")
    resolve_research(paths)
    assert read_json(paths.state)["stages"]["qa"]["status"] == "passed"


def test_semantic_rebind_stales_qa_after_resolve(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _single_source(paths, tmp_path, "任意门")
    _import_and_bind(paths, _pack(tmp_path / "p1", pack_id="canon-a", terms=[_term(value="任意门")]))
    import_pack(paths, _pack(tmp_path / "p2", pack_id="canon-b", terms=[_term(value="任意门2")]))
    set_mode(paths, "advisory")
    resolve_research(paths)
    build_all_workfiles(paths)
    compile_all(paths)
    assert run_all_qa(paths)["ok"] is True

    unbind_pack(paths, "canon-a@1.0.0")
    bind_pack(paths, "canon-b@1.0.0")
    resolve_research(paths)
    assert read_json(paths.state)["stages"]["qa"]["status"] == "stale"


def test_enforce_release_freezes_srp_identity(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _single_source(paths, tmp_path, "任意门")
    imported = _import_and_bind(paths, _pack(tmp_path / "release-pack", pack_id="release-pack", terms=[_term()]))
    set_mode(paths, "enforce")
    resolve_research(paths)
    approve_research(paths, note="accepted")
    build_all_workfiles(paths)
    compile_all(paths)
    assert run_all_qa(paths)["ok"] is True
    manifest = create_release_manifest(paths)
    assert manifest["research"]["mode"] == "enforce"
    assert manifest["research"]["bindings"][0]["pack_digest"] == imported["pack_digest"]
    assert manifest["research"]["effective_semantic_sha256"]
    assert manifest["research"]["gate"] == "passed"


def test_legacy_v030_research_gate_remains_supported(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    config = read_json(paths.title_config)
    config.pop("research")
    config["quality_gates"]["require_research"] = True
    write_json(paths.title_config, config)
    (paths.research / "context.md").write_text("context\n", encoding="utf-8")
    (paths.research / "sources.md").write_text("sources\n", encoding="utf-8")
    mark_research_complete(paths)
    assert read_json(paths.state)["stages"]["research"]["status"] == "passed"



def test_cross_pack_alias_policy_conflict_is_blocking(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _set_profile(paths, "full")
    accepted = _term(rec_id="term:a", value="任意门")
    accepted["target"]["accepted_aliases"] = ["随意门"]
    forbidden = _term(rec_id="term:b", value="任意门", forbidden=["随意门"])
    _import_and_bind(paths, _pack(tmp_path / "alias-a", pack_id="alias-a", terms=[accepted]))
    _import_and_bind(paths, _pack(tmp_path / "alias-b", pack_id="alias-b", terms=[forbidden]))
    set_mode(paths, "enforce")
    snapshot = resolve_research(paths)
    assert snapshot["blocking_conflicts"] == 1
    effective = read_json(paths.research_effective)
    assert any(item["kind"] == "srp-term-policy-conflict" for item in effective["conflicts"])


def test_invalid_utf8_jsonl_is_reported_cleanly(tmp_path: Path) -> None:
    from subtitleflow.srp.validate import validate_pack_dir

    pack = _pack(tmp_path / "bad-utf8", pack_id="bad-utf8")
    (pack / "terms.jsonl").write_bytes(b"\xff\xfe\n")
    with pytest.raises(ValidationError, match="invalid UTF-8"):
        validate_pack_dir(pack)

def test_zip_path_traversal_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("../manifest.json", "{}")
    with pytest.raises(ValidationError, match="Unsafe SRP ZIP"):
        with materialize_pack_input(archive):
            pass

def test_diff_detects_noncanonical_semantic_term_change(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _single_source(paths, tmp_path, "任意门")
    first_term = _term(value="任意门")
    first_term["enforcement"] = "preferred"
    first = _pack(tmp_path / "diff-a", pack_id="diff-a", terms=[first_term])
    second_term = _term(value="任意门", forbidden=["随意门"])
    second_term["enforcement"] = "locked"
    second = _pack(tmp_path / "diff-b", pack_id="diff-b", terms=[second_term])

    _import_and_bind(paths, first)
    import_pack(paths, second)
    set_mode(paths, "advisory")
    resolve_research(paths)

    unbind_pack(paths, "diff-a@1.0.0")
    bind_pack(paths, "diff-b@1.0.0")
    result = diff_research(paths)

    assert result["semantic_changed"] is True
    assert result["provenance_changed"] is True
    term_changes = [item for item in result["changes"] if item["kind"] == "term"]
    assert term_changes
    assert term_changes[0]["before"]["canonical"] == "任意门"
    assert term_changes[0]["after"]["canonical"] == "任意门"
    assert term_changes[0]["before"]["enforcement"] == "preferred"
    assert term_changes[0]["after"]["enforcement"] == "locked"


def test_inactive_series_branch_conflict_does_not_block_single_profile(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _set_profile(paths, "single")
    map_branch(paths, "tw", "tw-dub-zh-cn")
    term_a = _term(
        rec_id="term:tw:a",
        key="character.x",
        value="甲",
        scope={
            "level": "series_branch",
            "series_id": "demo",
            "branch_id": "tw-dub-zh-cn",
        },
    )
    term_b = _term(
        rec_id="term:tw:b",
        key="character.x",
        value="乙",
        scope={
            "level": "series_branch",
            "series_id": "demo",
            "branch_id": "tw-dub-zh-cn",
        },
    )
    _import_and_bind(paths, _pack(tmp_path / "inactive-a", pack_id="inactive-a", terms=[term_a]))
    _import_and_bind(paths, _pack(tmp_path / "inactive-b", pack_id="inactive-b", terms=[term_b]))
    set_mode(paths, "enforce")

    snapshot = resolve_research(paths)
    effective = read_json(paths.research_effective)

    assert set(effective["branches"]) == {"clean"}
    assert snapshot["blocking_conflicts"] == 0
    approve_research(paths)
    assert read_json(paths.state)["stages"]["research"]["status"] == "passed"


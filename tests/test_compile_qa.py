from pathlib import Path

from conftest import ass_dialogue, write_ass

from subtitleflow.canon import add_term
from subtitleflow.compile import compile_all
from subtitleflow.formats.ass import parse_ass
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.qa import run_all_qa
from subtitleflow.release import create_release_manifest
from subtitleflow.workfile import build_all_workfiles
from subtitleflow.workspace import add_source, create_project, create_title, title_paths


def test_compile_preserves_protected_and_release_passes(tmp_path: Path, sample_cues) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    paths = title_paths(tmp_path, "demo", "movie")
    protected = ass_dialogue("0:00:08.00", "0:00:10.00", r"{\pos(300,100)}SIGN")
    a = write_ass(tmp_path / "a.ass", sample_cues, extra=[protected])
    b = write_ass(tmp_path / "b.ass", sample_cues)
    c = write_ass(
        tmp_path / "c.ass",
        [(s, e, f"日本語{idx}") for idx, (s, e, _t) in enumerate(sample_cues, start=1)],
    )
    d = write_ass(tmp_path / "d.ass", sample_cues)
    for role, path in [("A", a), ("B", b), ("C", c), ("D", d)]:
        add_source(paths, role, path)
    add_term(
        paths,
        scope="project",
        term_id="doraemon",
        canonical="哆啦A梦",
        aliases=["小叮当"],
        auto_replace=True,
        context_sensitive=False,
        branches=["tw", "jp"],
        notes=None,
    )
    config = read_json(paths.title_config)
    config["tw_branch"]["traditional_to_simplified"] = False
    config["quality_gates"] = {
        "require_research": False,
        "require_semantic_qa": False,
        "require_visual_qa": False,
        "require_fonts": False,
    }
    config["fonts"]["require_for_release"] = False
    write_json(paths.title_config, config)
    normalize_all(paths)
    build_all_workfiles(paths)
    outputs = compile_all(paths)
    tw = parse_ass(Path(outputs["tw"]))
    jp = parse_ass(Path(outputs["jp"]))
    assert any("SIGN" in event.raw_line for event in tw.events)
    assert any("SIGN" in event.raw_line for event in jp.events)
    assert any(event.fields.get("Style") == "SF-ZH" for event in tw.events)
    assert any(event.fields.get("Style") == "SF-JA" for event in jp.events)
    qa = run_all_qa(paths)
    assert qa["ok"] is True
    manifest = create_release_manifest(paths)
    assert len(manifest["files"]) == 2
    accounting = read_json(paths.release / "source-accounting.json")
    assert accounting["coverage"]["source_spoken_fragments_unresolved"] == 0
    assert accounting["source_events"]

    coverage_path = paths.work / "bilingual-coverage.json"
    coverage = read_json(coverage_path)
    coverage["source_spoken_fragments_unresolved"] = 1
    write_json(coverage_path, coverage)
    blocked = run_all_qa(paths)
    assert blocked["ok"] is False
    assert any(
        item["kind"] == "unresolved-source-fragments" for item in blocked["structural"]["errors"]
    )

    reconciliation_path = paths.work / "bilingual-reconciliation.json"
    reconciliation = read_json(reconciliation_path)
    coverage["schema_version"] = 1
    reconciliation["schema_version"] = 1
    reconciliation["coverage"] = coverage
    write_json(coverage_path, coverage)
    write_json(reconciliation_path, reconciliation)
    legacy = run_all_qa(paths)
    assert any(
        item["kind"] == "source-accounting-migration-required"
        for item in legacy["structural"]["errors"]
    )

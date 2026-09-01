from __future__ import annotations

from pathlib import Path

from conftest import write_ass
from subtitleflow.cli import main
from subtitleflow.io import read_json, write_json


def test_cli_end_to_end(tmp_path: Path, sample_cues) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    repo = str(tmp_path)
    assert main(["--repo", repo, "project", "init", "demo", "--name", "Demo"]) == 0
    assert main(["--repo", repo, "title", "init", "demo", "movie", "--name", "Movie"]) == 0
    paths = tmp_path / "projects" / "demo" / "titles" / "movie"
    sources = {}
    sources["A"] = write_ass(tmp_path / "a.ass", sample_cues)
    sources["B"] = write_ass(tmp_path / "b.ass", sample_cues)
    sources["C"] = write_ass(
        tmp_path / "c.ass",
        [(s, e, f"日本語{idx}") for idx, (s, e, _t) in enumerate(sample_cues, start=1)],
    )
    sources["D"] = write_ass(tmp_path / "d.ass", sample_cues)
    for role, path in sources.items():
        assert main(["--repo", repo, "source", "add", "demo", "movie", role, str(path)]) == 0
    # Test fixture is simplified already; disable OpenCC at project title config level.
    cfg = read_json(paths / "title.json")
    cfg["tw_branch"]["traditional_to_simplified"] = False
    # This integration test verifies deterministic mechanics, not editorial gates.
    cfg["quality_gates"] = {
        "require_research": False,
        "require_semantic_qa": False,
        "require_visual_qa": False,
        "require_fonts": False,
    }
    cfg["fonts"]["require_for_release"] = False
    write_json(paths / "title.json", cfg)
    assert main(["--repo", repo, "canon", "add-term", "demo", "movie", "--id", "doraemon", "--canonical", "哆啦A梦", "--alias", "小叮当", "--auto"]) == 0
    assert main(["--repo", repo, "prepare", "demo", "movie"]) == 0
    assert main(["--repo", repo, "compile", "demo", "movie"]) == 0
    assert main(["--repo", repo, "qa", "demo", "movie"]) == 0
    assert main(["--repo", repo, "release", "demo", "movie"]) == 0
    assert (paths / "release" / "movie.zh-CN.tw.ass").exists()
    assert (paths / "release" / "movie.zh-CN-ja.ass").exists()
    assert (paths / "release" / "release-manifest.json").exists()


def test_style_set_invalid_profile_is_transactional(tmp_path: Path) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    repo = str(tmp_path)
    assert main(["--repo", repo, "project", "init", "demo", "--name", "Demo"]) == 0
    assert main(["--repo", repo, "title", "init", "demo", "movie", "--name", "Movie"]) == 0
    config_path = tmp_path / "projects" / "demo" / "titles" / "movie" / "title.json"
    before = read_json(config_path)

    assert main(["--repo", repo, "style", "set", "demo", "movie", "missing-profile"]) == 2
    assert read_json(config_path) == before


def test_cli_srp_import_bind_resolve_and_approve(tmp_path: Path) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    repo = str(tmp_path)
    assert main(["--repo", repo, "project", "init", "demo", "--name", "Demo"]) == 0
    assert main(["--repo", repo, "title", "init", "demo", "movie", "--name", "Movie"]) == 0

    pack = tmp_path / "srp"
    pack.mkdir()
    write_json(
        pack / "manifest.json",
        {
            "format": "subtitle-research-pack",
            "schema_version": "1.0",
            "pack_id": "canon",
            "pack_version": "1.0.0",
            "scope": {"series_id": "demo"},
        },
    )
    (pack / "terms.jsonl").write_text(
        '{"id":"term:x","key":"gadget.x","scope":{"level":"series","series_id":"demo"},'
        '"source":{"language":"ja-JP","forms":["X"]},'
        '"target":{"language":"zh-CN","value":"甲"},'
        '"enforcement":"locked","status":"accepted"}\n',
        encoding="utf-8",
    )

    assert main(["--repo", repo, "research", "validate-pack", str(pack)]) == 0
    assert main(["--repo", repo, "research", "import", "demo", str(pack)]) == 0
    assert main(["--repo", repo, "research", "bind", "demo", "movie", "canon@1.0.0"]) == 0
    assert main(["--repo", repo, "research", "set-mode", "demo", "movie", "enforce"]) == 0
    assert main(["--repo", repo, "research", "map-branch", "demo", "movie", "jp", "jp-zh-cn"]) == 0
    assert main(["--repo", repo, "research", "resolve", "demo", "movie"]) == 0
    assert main(["--repo", repo, "research", "approve", "demo", "movie", "--note", "accepted"]) == 0

    title = tmp_path / "projects" / "demo" / "titles" / "movie"
    snapshot = read_json(title / "research" / "snapshot.json")
    state = read_json(title / "state.json")
    assert snapshot["pack_digests"]
    assert state["stages"]["research"]["status"] == "passed"

from pathlib import Path

from subtitleflow.portable_release import _portableize_paths, _zip_deterministic


def test_portableize_paths_removes_runtime_specific_absolute_roots(tmp_path):
    workspace = tmp_path / "workspace"
    title = workspace / "projects" / "demo" / "titles" / "m01"
    source_root = tmp_path / "checkout"
    title.mkdir(parents=True)
    (source_root / "fonts" / "local").mkdir(parents=True)

    payload = {
        "title_file": str(title / "qa" / "summary.json"),
        "workspace_file": str(workspace / "projects" / "demo" / "project.json"),
        "font_file": str(source_root / "fonts" / "local" / "demo.ttf"),
        "nested": [str(source_root / "styles" / "collector.json")],
        "relative": "qa/summary.json",
    }

    portable = _portableize_paths(
        payload,
        title_root=title,
        workspace_root=workspace,
        source_root=source_root,
    )

    assert portable["title_file"] == "title://qa/summary.json"
    assert portable["workspace_file"] == "workspace://projects/demo/project.json"
    assert portable["font_file"] == "source-root://fonts/local/demo.ttf"
    assert portable["nested"] == ["source-root://styles/collector.json"]
    assert portable["relative"] == "qa/summary.json"
    assert str(tmp_path) not in repr(portable)


def test_deterministic_zip_has_stable_sha_for_identical_bundle_bytes(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "subtitles").mkdir(parents=True)
    (bundle / "reports").mkdir()
    (bundle / "subtitles" / "m01.ass").write_text("[Script Info]\n", encoding="utf-8")
    (bundle / "reports" / "summary.md").write_text("stable\n", encoding="utf-8")

    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    first_sha = _zip_deterministic(bundle, first)
    second_sha = _zip_deterministic(bundle, second)

    assert first_sha == second_sha
    assert first.read_bytes() == second.read_bytes()

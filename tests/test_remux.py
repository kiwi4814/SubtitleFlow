from pathlib import Path

from subtitleflow.remux import build_remux_command


def test_remux_command_is_argument_safe() -> None:
    cmd = build_remux_command(
        video=Path("/tmp/My Movie.mkv"),
        output=Path("/tmp/Out Movie.mkv"),
        tw_ass=Path("/tmp/tw subtitle.ass"),
        jp_ass=Path("/tmp/jp subtitle.ass"),
        tw_name="简体中文｜台配",
        jp_name="简日双语｜日配",
        preserve_existing_subtitles=False,
    )
    assert cmd[0] == "mkvmerge"
    assert "--no-subtitles" in cmd
    assert "/tmp/My Movie.mkv" in cmd
    assert "0:zh-CN" in cmd
    assert "--default-track-flag" in cmd
    assert "0:0" in cmd
    assert "0:简体中文｜台配" in cmd
    assert "0:简日双语｜日配" in cmd


def test_same_name_existing_font_is_reused_only_after_sha_verification(
    monkeypatch, tmp_path: Path
) -> None:
    import subtitleflow.remux as remux_module

    frozen_path = tmp_path / "font.ttf"
    frozen_path.write_bytes(b"font-content")
    frozen = {
        "path": str(frozen_path),
        "attachment_name": "font.ttf",
        "mime_type": "font/ttf",
        "sha256": remux_module.sha256_file(frozen_path),
        "size": frozen_path.stat().st_size,
        "families": ["Example Font"],
    }
    existing = [{"id": 7, "file_name": "font.ttf", "size": frozen["size"]}]
    monkeypatch.setattr(
        remux_module, "_existing_attachment_sha256", lambda _video, _item: frozen["sha256"]
    )
    assert remux_module._fonts_to_attach(Path("input.mkv"), [frozen], existing) == []


def test_same_name_existing_font_with_different_sha_blocks(monkeypatch, tmp_path: Path) -> None:
    import pytest

    import subtitleflow.remux as remux_module
    from subtitleflow.errors import GateError

    frozen_path = tmp_path / "font.ttf"
    frozen_path.write_bytes(b"font-content")
    frozen = {
        "path": str(frozen_path),
        "attachment_name": "font.ttf",
        "mime_type": "font/ttf",
        "sha256": remux_module.sha256_file(frozen_path),
        "size": frozen_path.stat().st_size,
        "families": ["Example Font"],
    }
    existing = [{"id": 7, "file_name": "font.ttf", "size": frozen["size"]}]
    monkeypatch.setattr(
        remux_module, "_existing_attachment_sha256", lambda _video, _item: "different"
    )
    with pytest.raises(GateError, match="different content"):
        remux_module._fonts_to_attach(Path("input.mkv"), [frozen], existing)


def _released_single(tmp_path: Path):
    from conftest import write_ass

    from subtitleflow.compile import compile_all
    from subtitleflow.io import read_json, write_json
    from subtitleflow.normalize import normalize_all
    from subtitleflow.qa import run_all_qa
    from subtitleflow.release import create_release_manifest
    from subtitleflow.workfile import build_all_workfiles
    from subtitleflow.workspace import (
        add_source,
        configure_workflow_profile,
        create_project,
        create_title,
        title_paths,
    )

    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    paths = title_paths(tmp_path, "demo", "movie")
    config = read_json(paths.title_config)
    configure_workflow_profile(config, "single")
    config["quality_gates"] = {
        "require_research": False,
        "require_semantic_qa": False,
        "require_visual_qa": False,
        "require_fonts": False,
    }
    config["fonts"]["require_for_release"] = False
    write_json(paths.title_config, config)
    add_source(paths, "S", write_ass(tmp_path / "S.ass", [("0:00:01.00", "0:00:02.00", "字幕")]))
    normalize_all(paths)
    build_all_workfiles(paths)
    compile_all(paths)
    assert run_all_qa(paths)["ok"] is True
    create_release_manifest(paths)
    return paths


def test_remux_blocks_same_input_and_output_even_with_force(tmp_path: Path) -> None:
    import pytest

    from subtitleflow.errors import GateError
    from subtitleflow.remux import remux

    paths = _released_single(tmp_path)
    video = tmp_path / "input.mkv"
    video.write_bytes(b"not-a-real-mkv-needed-for-dry-run")
    with pytest.raises(GateError, match="must not be the same"):
        remux(paths, video=video, output=video, dry_run=True, force=True)


def test_remux_blocks_video_different_from_visual_frozen_media(tmp_path: Path) -> None:
    import pytest

    from subtitleflow.errors import GateError
    from subtitleflow.io import read_json, write_json
    from subtitleflow.remux import remux
    from subtitleflow.util import file_identity

    paths = _released_single(tmp_path)
    reviewed = tmp_path / "reviewed.mkv"
    other = tmp_path / "other.mkv"
    reviewed.write_bytes(b"reviewed-video")
    other.write_bytes(b"different-video")
    manifest_path = paths.release / "release-manifest.json"
    manifest = read_json(manifest_path)
    manifest["media"]["video"] = file_identity(reviewed)
    write_json(manifest_path, manifest)
    with pytest.raises(GateError, match=r"exact media\.video"):
        remux(paths, video=other, output=tmp_path / "out.mkv", dry_run=True)

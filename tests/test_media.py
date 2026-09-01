from pathlib import Path

from subtitleflow.media import expand_media_path


def test_expand_media_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    assert expand_media_path("${MEDIA_ROOT}/movie.mkv") == (tmp_path / "movie.mkv").resolve()


def _prepared_render_title(tmp_path: Path):
    from conftest import write_ass
    from subtitleflow.compile import compile_all
    from subtitleflow.io import read_json, write_json
    from subtitleflow.normalize import normalize_all
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
    write_json(paths.title_config, config)
    add_source(paths, "S", write_ass(tmp_path / "S.ass", [("0:00:01.00", "0:00:02.00", "字幕")]))
    normalize_all(paths)
    build_all_workfiles(paths)
    compile_all(paths)
    return paths


def test_failed_rerender_invalidates_old_render_and_removes_old_frames(monkeypatch, tmp_path: Path) -> None:
    import pytest
    import subtitleflow.media as media_module
    from subtitleflow.errors import SubtitleFlowError
    from subtitleflow.io import read_json
    from subtitleflow.state import update_stage

    paths = _prepared_render_title(tmp_path)
    video = tmp_path / "movie.mkv"
    video.write_bytes(b"video")
    preview_dir = paths.qa / "previews" / "clean"
    preview_dir.mkdir(parents=True)
    old = preview_dir / "01-old.png"
    old.write_bytes(b"old-frame")
    update_stage(paths, "render_clean", "passed", frames=1, evidence={"legacy": True})
    update_stage(paths, "visual_clean", "passed", frames=1, evidence={"legacy": True})

    monkeypatch.setattr(media_module, "which", lambda _name: "/usr/bin/fake")
    monkeypatch.setattr(media_module, "require_font_attachments", lambda _paths: [])
    monkeypatch.setattr(media_module, "probe_media", lambda _video: {"format": {"duration": "10.0"}})

    def fail_run(*_args, **_kwargs):
        raise SubtitleFlowError("synthetic ffmpeg failure")

    monkeypatch.setattr(media_module, "run_checked", fail_run)
    with pytest.raises(SubtitleFlowError, match="synthetic ffmpeg failure"):
        media_module.render_previews(paths, "clean", video=video)

    state = read_json(paths.state)["stages"]
    assert state["render_clean"]["status"] == "stale"
    assert state["visual_clean"]["status"] == "stale"
    assert not list(preview_dir.glob("*.png"))


def test_render_stages_audited_fonts_and_records_evidence(monkeypatch, tmp_path: Path) -> None:
    import subtitleflow.media as media_module
    from subtitleflow.io import read_json
    from subtitleflow.util import sha256_file

    paths = _prepared_render_title(tmp_path)
    video = tmp_path / "movie.mkv"
    video.write_bytes(b"video")
    font = tmp_path / "Exact Font.ttf"
    font.write_bytes(b"font-bytes")
    attachments = [
        {
            "path": str(font),
            "attachment_name": font.name,
            "sha256": sha256_file(font),
            "size": font.stat().st_size,
        }
    ]
    calls: list[list[str]] = []

    monkeypatch.setattr(media_module, "which", lambda _name: "/usr/bin/fake")
    monkeypatch.setattr(media_module, "require_font_attachments", lambda _paths: attachments)
    monkeypatch.setattr(media_module, "probe_media", lambda _video: {"format": {"duration": "10.0"}})

    def fake_run(args, **_kwargs):
        calls.append(list(args))
        Path(args[-1]).write_bytes(b"png-frame")
        return None

    monkeypatch.setattr(media_module, "run_checked", fake_run)
    outputs = media_module.render_previews(paths, "clean", video=video, max_frames=1)
    assert len(outputs) == 1
    ffmpeg = calls[0]
    assert ffmpeg[ffmpeg.index("-vf") + 1] == "ass=subs.ass:fontsdir=fonts"
    stage = read_json(paths.state)["stages"]["render_clean"]
    assert stage["status"] == "passed"
    assert stage["evidence"]["fonts"] == [
        {"attachment_name": font.name, "sha256": sha256_file(font), "size": font.stat().st_size}
    ]
    assert stage["evidence"]["frames"]

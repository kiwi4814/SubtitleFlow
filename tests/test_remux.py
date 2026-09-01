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


def test_same_name_existing_font_is_reused_only_after_sha_verification(monkeypatch, tmp_path: Path) -> None:
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
    monkeypatch.setattr(remux_module, "_existing_attachment_sha256", lambda _video, _item: frozen["sha256"])
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
    monkeypatch.setattr(remux_module, "_existing_attachment_sha256", lambda _video, _item: "different")
    with pytest.raises(GateError, match="different content"):
        remux_module._fonts_to_attach(Path("input.mkv"), [frozen], existing)

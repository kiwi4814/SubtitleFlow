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

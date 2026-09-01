from pathlib import Path

from subtitleflow.formats.srt import parse_srt


def test_parse_srt(tmp_path: Path) -> None:
    path = tmp_path / "a.srt"
    path.write_text("1\n00:00:01,000 --> 00:00:02,500\nHello\nWorld\n\n", encoding="utf-8")
    cues = parse_srt(path)
    assert len(cues) == 1
    assert cues[0].plain_text == "Hello\nWorld"
    assert cues[0].start_ms == 1000

from pathlib import Path

from conftest import ass_dialogue, write_ass
from subtitleflow.formats.ass import build_event_line, make_dialogue_values, parse_ass, render_from_template


def test_parse_ass_and_protect_complex(tmp_path: Path) -> None:
    path = write_ass(
        tmp_path / "in.ass",
        [("0:00:01.00", "0:00:03.00", "普通对白")],
        extra=[ass_dialogue("0:00:04.00", "0:00:06.00", r"{\pos(100,100)}屏幕字")],
    )
    doc = parse_ass(path)
    assert len(doc.events) == 2
    assert doc.events[0].protected is False
    assert doc.events[1].protected is True


def test_render_preserves_protected_event(tmp_path: Path) -> None:
    protected = ass_dialogue("0:00:04.00", "0:00:06.00", r"{\pos(100,100)}屏幕字")
    path = write_ass(tmp_path / "in.ass", [("0:00:01.00", "0:00:03.00", "旧对白")], extra=[protected])
    doc = parse_ass(path)
    values = make_dialogue_values(
        doc.events_format,
        start_ms=1000,
        end_ms=3000,
        text="新对白",
        style="SF-ZH",
    )
    output = render_from_template(doc, [(1000, 1_000_001, build_event_line(doc.events_format, values))])
    assert "新对白" in output
    assert "旧对白" not in output
    assert protected in output
    assert "Style: SF-ZH" in output
    assert "Style: SF-JA" in output


def test_parse_protects_high_order_drawing_mode(tmp_path: Path) -> None:
    drawing = ass_dialogue("0:00:04.00", "0:00:06.00", r"{\p5}m 0 0 l 10 0 10 10")
    path = write_ass(tmp_path / "drawing.ass", [("0:00:01.00", "0:00:03.00", "普通对白")], extra=[drawing])
    doc = parse_ass(path)
    assert doc.events[-1].protected is True
    assert doc.events[-1].protected_reason == "ASS drawing mode"


def test_zero_duration_comment_is_preserved_as_protected(tmp_path: Path) -> None:
    path = tmp_path / "comment.ass"
    path.write_text(
        "[Script Info]\n"
        "ScriptType: v4.00+\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,42,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,30,30,40,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,,metadata\n",
        encoding="utf-8",
    )
    doc = parse_ass(path)
    assert len(doc.events) == 1
    assert doc.events[0].event_type == "Comment"
    assert doc.events[0].protected is True
    assert doc.cues[0].start_ms == doc.cues[0].end_ms == 0

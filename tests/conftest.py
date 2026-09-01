from __future__ import annotations

from pathlib import Path

import pytest


ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,40,40,50,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ass_dialogue(start: str, end: str, text: str, *, style: str = "Default", effect: str = "") -> str:
    return f"Dialogue: 0,{start},{end},{style},,0,0,0,{effect},{text}"


def write_ass(path: Path, cues: list[tuple[str, str, str]], *, extra: list[str] | None = None) -> Path:
    lines = [ASS_HEADER.rstrip()]
    for start, end, text in cues:
        lines.append(ass_dialogue(start, end, text))
    lines.extend(extra or [])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def sample_cues() -> list[tuple[str, str, str]]:
    return [
        ("0:00:01.00", "0:00:03.00", "小叮当，你来了。"),
        ("0:00:03.10", "0:00:05.20", "阿福也在这里。"),
        ("0:00:05.30", "0:00:07.50", "技安说快走。"),
    ]

from __future__ import annotations

import re
from pathlib import Path

from ..errors import ValidationError
from ..models import Cue
from ..text import normalize_dialogue_text
from ..timecode import parse_srt_time

_TIME_LINE = re.compile(r"^\s*(.*?)\s*-->\s*(.*?)\s*$")


def _read_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "gb18030", "big5"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValidationError(f"Unable to decode subtitle: {path}")


def parse_srt(path: Path) -> list[Cue]:
    text, _encoding = _read_text(path)
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip())
    cues: list[Cue] = []
    for block_index, block in enumerate(blocks, start=1):
        lines = block.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if not lines or not any(line.strip() for line in lines):
            continue
        time_index = 0
        if "-->" not in lines[0] and len(lines) > 1:
            time_index = 1
        if time_index >= len(lines):
            raise ValidationError(f"SRT block {block_index}: missing timing")
        match = _TIME_LINE.match(lines[time_index])
        if not match:
            raise ValidationError(f"SRT block {block_index}: invalid timing line")
        start_ms = parse_srt_time(match.group(1))
        end_ms = parse_srt_time(match.group(2))
        dialogue = normalize_dialogue_text("\n".join(lines[time_index + 1 :]))
        cue = Cue(
            id=f"srt-{len(cues)+1:06d}",
            index=len(cues),
            start_ms=start_ms,
            end_ms=end_ms,
            text=dialogue,
            plain_text=dialogue,
            style="Default",
            event_type="Dialogue",
            protected=False,
        )
        cue.validate()
        cues.append(cue)
    return cues

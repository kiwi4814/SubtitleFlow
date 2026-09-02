from __future__ import annotations

import re

from .errors import ValidationError

_ASS_RE = re.compile(r"^(?P<h>\d+):(?P<m>\d{2}):(?P<s>\d{2})\.(?P<cs>\d{2})$")
_SRT_RE = re.compile(r"^(?P<h>\d{1,3}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{3})$")


def parse_ass_time(value: str) -> int:
    match = _ASS_RE.match(value.strip())
    if not match:
        raise ValidationError(f"Invalid ASS timestamp: {value!r}")
    return (
        int(match["h"]) * 3_600_000
        + int(match["m"]) * 60_000
        + int(match["s"]) * 1_000
        + int(match["cs"]) * 10
    )


def format_ass_time(milliseconds: int) -> str:
    if milliseconds < 0:
        raise ValidationError("Negative ASS timestamp")
    total_cs = round(milliseconds / 10)
    hours, rem = divmod(total_cs, 360_000)
    minutes, rem = divmod(rem, 6_000)
    seconds, centiseconds = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def parse_srt_time(value: str) -> int:
    match = _SRT_RE.match(value.strip())
    if not match:
        raise ValidationError(f"Invalid SRT timestamp: {value!r}")
    return (
        int(match["h"]) * 3_600_000
        + int(match["m"]) * 60_000
        + int(match["s"]) * 1_000
        + int(match["ms"])
    )


def format_srt_time(milliseconds: int) -> str:
    if milliseconds < 0:
        raise ValidationError("Negative SRT timestamp")
    hours, rem = divmod(milliseconds, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

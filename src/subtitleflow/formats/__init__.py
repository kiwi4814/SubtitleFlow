from __future__ import annotations

from pathlib import Path

from ..errors import ValidationError
from ..models import Cue
from .ass import AssDocument, parse_ass
from .srt import parse_srt


def parse_subtitle(path: Path) -> tuple[list[Cue], dict[str, object]]:
    suffix = path.suffix.lower()
    if suffix == ".ass" or suffix == ".ssa":
        doc = parse_ass(path)
        return doc.cues, {"ass": doc.metadata()}
    if suffix == ".srt":
        cues = parse_srt(path)
        return cues, {}
    raise ValidationError(f"Unsupported subtitle format: {path.suffix}")


__all__ = ["AssDocument", "parse_ass", "parse_srt", "parse_subtitle"]

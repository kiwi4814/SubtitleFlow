from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import ValidationError
from ..models import Cue
from ..text import normalize_dialogue_text, strip_ass_tags
from ..timecode import format_ass_time, parse_ass_time

_COMPLEX_MARKERS = (
    r"\pos(",
    r"\move(",
    r"\clip(",
    r"\iclip(",
    r"\org(",
    r"\fad(",
    r"\fade(",
    r"\t(",
    r"\k",
    r"\K",
    r"\kf",
    r"\ko",
)


@dataclass(slots=True)
class AssEvent:
    index: int
    event_type: str
    fields: dict[str, str]
    raw_line: str
    start_ms: int
    end_ms: int
    protected: bool
    protected_reason: str | None


@dataclass(slots=True)
class AssDocument:
    path: Path
    encoding: str
    lines: list[str]
    events_format: list[str]
    style_format: list[str]
    events: list[AssEvent]
    cues: list[Cue]
    section_bounds: dict[str, tuple[int, int]] = field(default_factory=dict)

    def metadata(self) -> dict[str, Any]:
        return {
            "encoding": self.encoding,
            "events_format": self.events_format,
            "style_format": self.style_format,
            "event_count": len(self.events),
            "protected_event_count": sum(event.protected for event in self.events),
        }


def _read_text(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "gb18030", "big5"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValidationError(f"Unable to decode ASS/SSA file: {path}")


def _sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    starts: list[tuple[str, int]] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            starts.append((stripped.lower(), idx))
    bounds: dict[str, tuple[int, int]] = {}
    for pos, (name, start) in enumerate(starts):
        end = starts[pos + 1][1] if pos + 1 < len(starts) else len(lines)
        bounds[name] = (start, end)
    return bounds


def _parse_format(line: str) -> list[str]:
    _, _, payload = line.partition(":")
    return [part.strip() for part in payload.split(",")]


def _event_protection(event_type: str, fields: dict[str, str]) -> tuple[bool, str | None]:
    if event_type.lower() != "dialogue":
        return True, "non-dialogue event"
    effect = fields.get("Effect", "").strip()
    if effect:
        return True, "non-empty ASS Effect field"
    text = fields.get("Text", "")
    lowered = text.lower()
    for marker in _COMPLEX_MARKERS:
        if marker.lower() in lowered:
            return True, f"complex ASS tag {marker}"
    if re.search(r"\\p[1-9]\d*", text, flags=re.IGNORECASE):
        return True, "ASS drawing mode"
    return False, None


def parse_ass(path: Path) -> AssDocument:
    text, encoding = _read_text(path)
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    bounds = _sections(lines)
    if "[events]" not in bounds:
        raise ValidationError(f"ASS file has no [Events] section: {path}")

    style_format: list[str] = []
    styles_bound = bounds.get("[v4+ styles]") or bounds.get("[v4 styles]")
    if styles_bound:
        for line in lines[styles_bound[0] + 1 : styles_bound[1]]:
            if line.lstrip().lower().startswith("format:"):
                style_format = _parse_format(line)
                break

    start, end = bounds["[events]"]
    events_format: list[str] = []
    format_line_index: int | None = None
    for idx in range(start + 1, end):
        if lines[idx].lstrip().lower().startswith("format:"):
            events_format = _parse_format(lines[idx])
            format_line_index = idx
            break
    if not events_format or format_line_index is None:
        raise ValidationError(f"ASS [Events] has no Format line: {path}")

    events: list[AssEvent] = []
    cues: list[Cue] = []
    for line_index in range(format_line_index + 1, end):
        raw = lines[line_index]
        if ":" not in raw:
            continue
        event_type, sep, payload = raw.partition(":")
        if not sep or event_type.strip().lower() not in {"dialogue", "comment"}:
            continue
        parts = payload.lstrip().split(",", maxsplit=len(events_format) - 1)
        if len(parts) != len(events_format):
            raise ValidationError(
                f"ASS event field count mismatch at line {line_index + 1}: {path}"
            )
        fields = {name: value for name, value in zip(events_format, parts, strict=True)}
        try:
            start_ms = parse_ass_time(fields["Start"])
            end_ms = parse_ass_time(fields["End"])
        except KeyError as exc:
            raise ValidationError(f"ASS Format missing Start/End: {path}") from exc
        protected, reason = _event_protection(event_type.strip(), fields)
        event = AssEvent(
            index=len(events),
            event_type=event_type.strip(),
            fields=fields,
            raw_line=raw,
            start_ms=start_ms,
            end_ms=end_ms,
            protected=protected,
            protected_reason=reason,
        )
        events.append(event)
        plain = normalize_dialogue_text(strip_ass_tags(fields.get("Text", "")))
        cue = Cue(
            id=f"ass-{len(events):06d}",
            index=len(events) - 1,
            start_ms=start_ms,
            end_ms=end_ms,
            text=fields.get("Text", ""),
            plain_text=plain,
            style=fields.get("Style", "Default").strip() or "Default",
            event_type=event.event_type,
            protected=protected,
            protected_reason=reason,
            raw_line=raw,
        )
        cue.validate()
        cues.append(cue)

    return AssDocument(
        path=path,
        encoding=encoding,
        lines=lines,
        events_format=events_format,
        style_format=style_format,
        events=events,
        cues=cues,
        section_bounds=bounds,
    )


def build_event_line(event_format: list[str], values: dict[str, str]) -> str:
    payload = ",".join(values.get(field, "") for field in event_format)
    return f"Dialogue: {payload}"


def _style_values(name: str, *, font: str, size: int, margin_v: int, bold: bool) -> dict[str, str]:
    return {
        "Name": name,
        "Fontname": font,
        "Fontsize": str(size),
        "PrimaryColour": "&H00FFFFFF",
        "SecondaryColour": "&H000000FF",
        "OutlineColour": "&H00000000",
        "BackColour": "&H64000000",
        "Bold": "-1" if bold else "0",
        "Italic": "0",
        "Underline": "0",
        "StrikeOut": "0",
        "ScaleX": "100",
        "ScaleY": "100",
        "Spacing": "0",
        "Angle": "0",
        "BorderStyle": "1",
        "Outline": "2.2",
        "Shadow": "0",
        "Alignment": "2",
        "MarginL": "40",
        "MarginR": "40",
        "MarginV": str(margin_v),
        "Encoding": "1",
    }


def build_style_line(style_format: list[str], values: dict[str, str]) -> str:
    if not style_format:
        style_format = [
            "Name",
            "Fontname",
            "Fontsize",
            "PrimaryColour",
            "SecondaryColour",
            "OutlineColour",
            "BackColour",
            "Bold",
            "Italic",
            "Underline",
            "StrikeOut",
            "ScaleX",
            "ScaleY",
            "Spacing",
            "Angle",
            "BorderStyle",
            "Outline",
            "Shadow",
            "Alignment",
            "MarginL",
            "MarginR",
            "MarginV",
            "Encoding",
        ]
    return "Style: " + ",".join(values.get(field, "0") for field in style_format)


def inject_styles(
    lines: list[str],
    *,
    target_font: str,
    target_size: int,
    target_margin_v: int,
    source_font: str,
    source_size: int,
    source_margin_v: int,
) -> list[str]:
    output = list(lines)
    bounds = _sections(output)
    styles_bound = bounds.get("[v4+ styles]") or bounds.get("[v4 styles]")
    if not styles_bound:
        # Insert a modern style section before Events.
        events_start = bounds["[events]"][0]
        block = [
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        ]
        output[events_start:events_start] = block + [""]
        bounds = _sections(output)
        styles_bound = bounds["[v4+ styles]"]

    style_start, style_end = styles_bound
    style_format: list[str] = []
    insert_at = style_end
    existing_names: set[str] = set()
    for idx in range(style_start + 1, style_end):
        line = output[idx]
        if line.lstrip().lower().startswith("format:"):
            style_format = _parse_format(line)
        elif line.lstrip().lower().startswith("style:"):
            payload = line.partition(":")[2].lstrip()
            if payload:
                existing_names.add(payload.split(",", 1)[0].strip())

    additions: list[str] = []
    if "SF-ZH" not in existing_names:
        additions.append(
            build_style_line(
                style_format,
                _style_values(
                    "SF-ZH",
                    font=target_font,
                    size=target_size,
                    margin_v=target_margin_v,
                    bold=True,
                ),
            )
        )
    if "SF-JA" not in existing_names:
        additions.append(
            build_style_line(
                style_format,
                _style_values(
                    "SF-JA",
                    font=source_font,
                    size=source_size,
                    margin_v=source_margin_v,
                    bold=False,
                ),
            )
        )
    if additions:
        output[insert_at:insert_at] = additions
    return output


def render_from_template(
    template: AssDocument,
    generated_events: list[tuple[int, int, str]],
    *,
    target_font: str = "Noto Sans CJK SC",
    target_size: int = 48,
    target_margin_v: int = 52,
    source_font: str = "Noto Sans CJK JP",
    source_size: int = 38,
    source_margin_v: int = 106,
) -> str:
    lines = inject_styles(
        template.lines,
        target_font=target_font,
        target_size=target_size,
        target_margin_v=target_margin_v,
        source_font=source_font,
        source_size=source_size,
        source_margin_v=source_margin_v,
    )
    bounds = _sections(lines)
    start, end = bounds["[events]"]
    format_idx: int | None = None
    event_format: list[str] = []
    for idx in range(start + 1, end):
        if lines[idx].lstrip().lower().startswith("format:"):
            format_idx = idx
            event_format = _parse_format(lines[idx])
            break
    if format_idx is None:
        raise ValidationError("Template Events Format line disappeared")

    preserved: list[tuple[int, int, str]] = []
    for event in template.events:
        if event.protected:
            preserved.append((event.start_ms, event.index, event.raw_line))

    merged = preserved + generated_events
    merged.sort(key=lambda item: (item[0], item[1]))
    new_lines = lines[: format_idx + 1] + [item[2] for item in merged] + lines[end:]
    return "\n".join(new_lines).rstrip() + "\n"


def make_dialogue_values(
    event_format: list[str],
    *,
    start_ms: int,
    end_ms: int,
    text: str,
    style: str,
    layer: str = "0",
) -> dict[str, str]:
    values = {field: "" for field in event_format}
    values.update(
        {
            "Layer": layer,
            "Marked": "0",
            "Start": format_ass_time(start_ms),
            "End": format_ass_time(end_ms),
            "Style": style,
            "Name": "",
            "MarginL": "0",
            "MarginR": "0",
            "MarginV": "0",
            "Effect": "",
            "Text": text,
        }
    )
    return values


def minimal_ass_document() -> AssDocument:
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,40,40,52,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    return AssDocument(
        path=Path("<generated>"),
        encoding="utf-8",
        lines=lines,
        events_format=["Layer", "Start", "End", "Style", "Name", "MarginL", "MarginR", "MarginV", "Effect", "Text"],
        style_format=[
            "Name", "Fontname", "Fontsize", "PrimaryColour", "SecondaryColour",
            "OutlineColour", "BackColour", "Bold", "Italic", "Underline", "StrikeOut",
            "ScaleX", "ScaleY", "Spacing", "Angle", "BorderStyle", "Outline", "Shadow",
            "Alignment", "MarginL", "MarginR", "MarginV", "Encoding",
        ],
        events=[],
        cues=[],
        section_bounds=_sections(lines),
    )

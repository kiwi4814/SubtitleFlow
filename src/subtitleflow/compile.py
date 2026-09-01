from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .errors import GateError, ValidationError
from .formats.ass import (
    AssDocument,
    build_event_line,
    make_dialogue_values,
    minimal_ass_document,
    parse_ass,
    render_from_template,
)
from .io import read_json
from .review import pending_count
from .state import invalidate_after_compile, update_stage
from .text import ass_text
from .workfile import load_workfile
from .workspace import TitlePaths, require_roles, verify_sources


def _template(paths: TitlePaths) -> AssDocument:
    record = require_roles(paths, {"A"})["A"]
    source = paths.title / record["path"]
    if source.suffix.lower() in {".ass", ".ssa"}:
        return parse_ass(source)
    return minimal_ass_document()


def _style_args(config: dict) -> dict[str, object]:
    ass = config.get("ass", {})
    return {
        "target_font": str(ass.get("target_font", "Noto Sans CJK SC")),
        "target_size": int(ass.get("target_size", 48)),
        "target_margin_v": int(ass.get("target_margin_v", 52)),
        "source_font": str(ass.get("source_font", "Noto Sans CJK JP")),
        "source_size": int(ass.get("source_size", 38)),
        "source_margin_v": int(ass.get("source_margin_v", 106)),
    }


def _ensure_compile_gate(paths: TitlePaths, *, preview: bool) -> None:
    verify_sources(paths)
    pending = pending_count(paths)
    if pending and not preview:
        raise GateError(f"Compile blocked: {pending} human review candidate(s) are still pending")


def _write_rendered(paths: TitlePaths, filename: str, text: str) -> Path:
    output = paths.release / filename
    output.write_text(text, encoding="utf-8", newline="")
    return output


def compile_tw(paths: TitlePaths, *, preview: bool = False) -> Path:
    _ensure_compile_gate(paths, preview=preview)
    work = load_workfile(paths, "tw")
    config = read_json(paths.title_config)
    template = _template(paths)
    events: list[tuple[int, int, str]] = []
    for index, unit in enumerate(work.units, start=1):
        if not unit.final_text.strip():
            raise ValidationError(f"TW unit {unit.id} has empty final_text")
        values = make_dialogue_values(
            template.events_format,
            start_ms=unit.start_ms,
            end_ms=unit.end_ms,
            text=ass_text(unit.final_text),
            style="SF-ZH",
        )
        events.append((unit.start_ms, 1_000_000 + index, build_event_line(template.events_format, values)))
    rendered = render_from_template(template, events, **_style_args(config))
    suffix = ".preview.ass" if preview else ".ass"
    output = _write_rendered(paths, f"{paths.title_id}.zh-CN.tw{suffix}", rendered)
    update_stage(paths, "compile_tw", "preview" if preview else "passed", output=str(output.relative_to(paths.title)))
    return output


def _contiguous_source_groups(units: Iterable) -> list[tuple[int, int, str]]:
    units = list(units)
    groups: list[tuple[int, int, str]] = []
    i = 0
    while i < len(units):
        unit = units[i]
        if not unit.source_text or not unit.source_text_cue_ids:
            i += 1
            continue
        ids = tuple(unit.source_text_cue_ids)
        text = unit.source_text
        start_ms = unit.start_ms
        end_ms = unit.end_ms
        j = i + 1
        while j < len(units):
            other = units[j]
            if tuple(other.source_text_cue_ids) != ids or other.source_text != text:
                break
            end_ms = other.end_ms
            j += 1
        groups.append((start_ms, end_ms, text))
        i = j
    return groups


def compile_jp_bilingual(paths: TitlePaths, *, preview: bool = False) -> Path:
    _ensure_compile_gate(paths, preview=preview)
    work = load_workfile(paths, "jp")
    config = read_json(paths.title_config)
    template = _template(paths)
    events: list[tuple[int, int, str]] = []
    serial = 0
    for unit in work.units:
        if not unit.final_text.strip():
            raise ValidationError(f"JP unit {unit.id} has empty Chinese final_text")
        serial += 1
        values = make_dialogue_values(
            template.events_format,
            start_ms=unit.start_ms,
            end_ms=unit.end_ms,
            text=ass_text(unit.final_text),
            style="SF-ZH",
        )
        events.append((unit.start_ms, 1_000_000 + serial, build_event_line(template.events_format, values)))

    for start_ms, end_ms, text in _contiguous_source_groups(work.units):
        if not text.strip():
            continue
        serial += 1
        values = make_dialogue_values(
            template.events_format,
            start_ms=start_ms,
            end_ms=end_ms,
            text=ass_text(text),
            style="SF-JA",
        )
        events.append((start_ms, 2_000_000 + serial, build_event_line(template.events_format, values)))

    rendered = render_from_template(template, events, **_style_args(config))
    suffix = ".preview.ass" if preview else ".ass"
    output = _write_rendered(paths, f"{paths.title_id}.zh-CN-ja{suffix}", rendered)
    update_stage(paths, "compile_jp", "preview" if preview else "passed", output=str(output.relative_to(paths.title)))
    return output


def compile_all(paths: TitlePaths, *, preview: bool = False) -> dict[str, str]:
    if not preview:
        invalidate_after_compile(paths)
    config = read_json(paths.title_config)
    outputs: dict[str, str] = {}
    if config.get("tw_branch", {}).get("enabled", True):
        outputs["tw"] = str(compile_tw(paths, preview=preview))
    if config.get("jp_branch", {}).get("enabled", True):
        outputs["jp"] = str(compile_jp_bilingual(paths, preview=preview))
    return outputs

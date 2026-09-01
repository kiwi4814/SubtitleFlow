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
from .review import pending_count
from .state import invalidate_after_compile, update_stage
from .style import ass_style_values, event_override_tag, is_special_source_style
from .text import ass_text
from .workfile import load_workfile
from .workflow import active_branches
from .workspace import TitlePaths, require_roles, verify_sources


def _template(paths: TitlePaths, role: str) -> AssDocument:
    record = require_roles(paths, {role})[role]
    source = paths.title / record["path"]
    if source.suffix.lower() in {".ass", ".ssa"}:
        return parse_ass(source)
    return minimal_ass_document()


def _profile_styles(paths: TitlePaths) -> dict[str, dict[str, str]]:
    return {
        "SF-ZH": ass_style_values(paths, "SF-ZH"),
        "SF-JA": ass_style_values(paths, "SF-JA"),
    }


def _preserved_style_names(paths: TitlePaths, template: AssDocument) -> set[str]:
    return {
        event.fields.get("Style", "").strip()
        for event in template.events
        if is_special_source_style(paths, event.fields.get("Style", ""))
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


def _target_events(template: AssDocument, units: Iterable, *, paths: TitlePaths | None = None, serial_base: int = 1_000_000) -> list[tuple[int, int, str]]:
    events: list[tuple[int, int, str]] = []
    for index, unit in enumerate(units, start=1):
        if not unit.final_text.strip():
            raise ValidationError(f"{unit.id} has empty final_text")
        target_text = ass_text(unit.final_text)
        override = event_override_tag(paths, "SF-ZH") if paths is not None else None
        if override:
            target_text = "{" + override + "}" + target_text
        values = make_dialogue_values(
            template.events_format,
            start_ms=unit.start_ms,
            end_ms=unit.end_ms,
            text=target_text,
            style="SF-ZH",
        )
        events.append((unit.start_ms, serial_base + index, build_event_line(template.events_format, values)))
    return events


def compile_clean(paths: TitlePaths, *, preview: bool = False) -> Path:
    _ensure_compile_gate(paths, preview=preview)
    work = load_workfile(paths, "clean")
    template = _template(paths, "S")
    rendered = render_from_template(
        template,
        _target_events(template, work.units, paths=paths),
        style_values=_profile_styles(paths),
        preserve_style_names=_preserved_style_names(paths, template),
    )
    suffix = ".preview.ass" if preview else ".ass"
    output = _write_rendered(paths, f"{paths.title_id}.zh-CN{suffix}", rendered)
    update_stage(paths, "compile_clean", "preview" if preview else "passed", output=str(output.relative_to(paths.title)))
    return output


def compile_tw(paths: TitlePaths, *, preview: bool = False) -> Path:
    _ensure_compile_gate(paths, preview=preview)
    work = load_workfile(paths, "tw")
    template = _template(paths, "A")
    rendered = render_from_template(
        template,
        _target_events(template, work.units, paths=paths),
        style_values=_profile_styles(paths),
        preserve_style_names=_preserved_style_names(paths, template),
    )
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
    template = _template(paths, "A")
    events = _target_events(template, work.units, paths=paths)
    serial = len(events)
    for start_ms, end_ms, text in _contiguous_source_groups(work.units):
        if not text.strip():
            continue
        serial += 1
        source_text = ass_text(text)
        override = event_override_tag(paths, "SF-JA")
        if override:
            source_text = "{" + override + "}" + source_text
        values = make_dialogue_values(
            template.events_format,
            start_ms=start_ms,
            end_ms=end_ms,
            text=source_text,
            style="SF-JA",
        )
        events.append((start_ms, 2_000_000 + serial, build_event_line(template.events_format, values)))

    rendered = render_from_template(
        template,
        events,
        style_values=_profile_styles(paths),
        preserve_style_names=_preserved_style_names(paths, template),
    )
    suffix = ".preview.ass" if preview else ".ass"
    output = _write_rendered(paths, f"{paths.title_id}.zh-CN-ja{suffix}", rendered)
    update_stage(paths, "compile_jp", "preview" if preview else "passed", output=str(output.relative_to(paths.title)))
    return output


def compile_all(paths: TitlePaths, *, preview: bool = False) -> dict[str, str]:
    if not preview:
        invalidate_after_compile(paths)
    outputs: dict[str, str] = {}
    for branch in active_branches(paths):
        if branch == "clean":
            outputs["clean"] = str(compile_clean(paths, preview=preview))
        elif branch == "tw":
            outputs["tw"] = str(compile_tw(paths, preview=preview))
        elif branch == "jp":
            outputs["jp"] = str(compile_jp_bilingual(paths, preview=preview))
    return outputs

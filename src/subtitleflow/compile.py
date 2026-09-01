from __future__ import annotations

from pathlib import Path
from collections.abc import Iterable
from typing import Any

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
from .layout import block_geometry, positioned_override
from .review import pending_count
from .roles import is_release_dialogue_role
from .state import invalidate_after_compile, update_stage
from .style import ass_style_values, event_override_tag, layout_settings, load_style_profile
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


def _play_resolution(paths: TitlePaths, template: AssDocument) -> tuple[int, int]:
    x: int | None = None
    y: int | None = None
    for line in template.lines:
        key, sep, raw = line.partition(":")
        if not sep:
            continue
        if key.strip().casefold() == "playresx":
            try:
                x = int(raw.strip())
            except ValueError:
                pass
        elif key.strip().casefold() == "playresy":
            try:
                y = int(raw.strip())
            except ValueError:
                pass
    profile_res = load_style_profile(paths).get("play_resolution", {})
    return int(x or profile_res.get("x", 1920)), int(y or profile_res.get("y", 1080))


def _excluded_event_indices(template: AssDocument) -> set[int]:
    return {cue.index for cue in template.cues if not cue.include_in_release}


def _preserved_event_indices(template: AssDocument) -> set[int]:
    """Preserve authored non-dialogue semantics, not arbitrary source style names.

    A style name is classification evidence only. Generic names such as Style2 do not imply
    screen text or top placement. Translator notes/credits classified with
    include_in_release=False are omitted unless a project explicitly reclassifies them.
    """
    preserved: set[int] = set()
    for cue in template.cues:
        if not cue.include_in_release:
            continue
        if cue.protected or not is_release_dialogue_role(cue.semantic_role):
            preserved.add(cue.index)
    return preserved


def _ensure_compile_gate(paths: TitlePaths, *, preview: bool) -> None:
    verify_sources(paths)
    pending = pending_count(paths)
    if pending and not preview:
        raise GateError(f"Compile blocked: {pending} human review candidate(s) are still pending")


def _write_rendered(paths: TitlePaths, filename: str, text: str) -> Path:
    output = paths.release / filename
    output.write_text(text, encoding="utf-8", newline="")
    return output


def _event(
    template: AssDocument,
    *,
    start_ms: int,
    end_ms: int,
    text: str,
    style: str,
    override: str | None,
    margin_v: int | None = None,
) -> str:
    rendered_text = ass_text(text)
    if override:
        rendered_text = "{" + override + "}" + rendered_text
    values = make_dialogue_values(
        template.events_format,
        start_ms=start_ms,
        end_ms=end_ms,
        text=rendered_text,
        style=style,
    )
    if margin_v is not None:
        values["MarginV"] = str(max(0, margin_v))
    return build_event_line(template.events_format, values)


def _target_events(
    template: AssDocument,
    units: Iterable[Any],
    *,
    paths: TitlePaths,
    mode: str,
    serial_base: int = 1_000_000,
) -> list[tuple[int, int, str]]:
    events: list[tuple[int, int, str]] = []
    styles = _profile_styles(paths)
    layout = layout_settings(paths)
    play_x, play_y = _play_resolution(paths, template)
    for index, unit in enumerate(units, start=1):
        if not unit.final_text.strip():
            raise ValidationError(f"{unit.id} has empty final_text")
        geometry = block_geometry(
            play_res_x=play_x,
            play_res_y=play_y,
            target_style=styles["SF-ZH"],
            source_style=None,
            layout=layout,
            target_text=unit.final_text,
            mode=mode,
            semantic_role=getattr(unit, "semantic_role", "dialogue"),
        )
        # Clean/TW have no second language block, so event MarginV is deterministic without
        # introducing an absolute \pos override. Bilingual events use explicit coordinates to
        # defeat libass collision reordering.
        override = event_override_tag(paths, "SF-ZH")
        margin_v = max(0, play_y - geometry.target_y)
        events.append(
            (
                unit.start_ms,
                serial_base + index,
                _event(
                    template,
                    start_ms=unit.start_ms,
                    end_ms=unit.end_ms,
                    text=unit.final_text,
                    style="SF-ZH",
                    override=override,
                    margin_v=margin_v,
                ),
            )
        )
    return events


def _render_standard(paths: TitlePaths, *, branch: str, template_role: str, filename: str, preview: bool) -> Path:
    _ensure_compile_gate(paths, preview=preview)
    work = load_workfile(paths, branch)
    template = _template(paths, template_role)
    rendered = render_from_template(
        template,
        _target_events(template, work.units, paths=paths, mode="clean"),
        style_values=_profile_styles(paths),
        preserve_style_names=set(),
        preserve_event_indices=_preserved_event_indices(template),
        exclude_event_indices=_excluded_event_indices(template),
    )
    suffix = ".preview.ass" if preview else ".ass"
    output = _write_rendered(paths, filename + suffix, rendered)
    update_stage(
        paths,
        f"compile_{branch}",
        "preview" if preview else "passed",
        output=str(output.relative_to(paths.title)),
    )
    return output


def compile_clean(paths: TitlePaths, *, preview: bool = False) -> Path:
    return _render_standard(
        paths,
        branch="clean",
        template_role="S",
        filename=f"{paths.title_id}.zh-CN",
        preview=preview,
    )


def compile_tw(paths: TitlePaths, *, preview: bool = False) -> Path:
    return _render_standard(
        paths,
        branch="tw",
        template_role="A",
        filename=f"{paths.title_id}.zh-CN.tw",
        preview=preview,
    )


def _reconciliation(paths: TitlePaths) -> dict[str, Any]:
    path = paths.work / "bilingual-reconciliation.json"
    if not path.is_file():
        raise GateError(
            "JP workfile predates bilingual reconciliation; rerun `subflow prepare` before compiling"
        )
    data = read_json(path)
    if not isinstance(data.get("pairs"), list):
        raise ValidationError("bilingual-reconciliation.json has no pairs array")
    return data


def compile_jp_bilingual(paths: TitlePaths, *, preview: bool = False) -> Path:
    _ensure_compile_gate(paths, preview=preview)
    work = load_workfile(paths, "jp")
    template = _template(paths, "A")
    reconciliation = _reconciliation(paths)
    units = {item.id: item for item in work.units}
    styles = _profile_styles(paths)
    layout = layout_settings(paths)
    play_x, play_y = _play_resolution(paths, template)
    events: list[tuple[int, int, str]] = []
    serial = 0

    for pair in reconciliation["pairs"]:
        unit_id = str(pair.get("target_unit_id", ""))
        unit = units.get(unit_id)
        if unit is None:
            raise GateError(f"Reconciliation references missing target unit: {unit_id}")
        operation = str(pair.get("operation", "unresolved"))
        if operation == "unresolved":
            raise GateError(f"JP compile blocked: unresolved bilingual reconciliation for {unit_id}")
        source_text = pair.get("source_text")
        if operation != "source-gap" and not str(source_text or "").strip():
            raise GateError(f"JP compile blocked: {operation} pair {unit_id} has no source text")

        # The workfile remains authoritative for target text after Human Review; reconciliation
        # owns only source relation/provenance. Both events use the target unit's final timing.
        geometry = block_geometry(
            play_res_x=play_x,
            play_res_y=play_y,
            target_style=styles["SF-ZH"],
            source_style=styles["SF-JA"],
            layout=layout,
            target_text=unit.final_text,
            source_text=str(source_text) if source_text else None,
            mode="bilingual",
            semantic_role=unit.semantic_role,
        )
        zh_override = positioned_override(
            event_override_tag(paths, "SF-ZH"), geometry.target_x, geometry.target_y
        )
        serial += 1
        events.append(
            (
                unit.start_ms,
                1_000_000 + serial,
                _event(
                    template,
                    start_ms=unit.start_ms,
                    end_ms=unit.end_ms,
                    text=unit.final_text,
                    style="SF-ZH",
                    override=zh_override,
                ),
            )
        )
        if source_text:
            ja_override = positioned_override(
                event_override_tag(paths, "SF-JA"),
                int(geometry.source_x or geometry.target_x),
                int(geometry.source_y or geometry.target_y),
            )
            serial += 1
            events.append(
                (
                    unit.start_ms,
                    2_000_000 + serial,
                    _event(
                        template,
                        start_ms=unit.start_ms,
                        end_ms=unit.end_ms,
                        text=str(source_text),
                        style="SF-JA",
                        override=ja_override,
                    ),
                )
            )

    rendered = render_from_template(
        template,
        events,
        style_values=styles,
        preserve_style_names=set(),
        preserve_event_indices=_preserved_event_indices(template),
        exclude_event_indices=_excluded_event_indices(template),
    )
    suffix = ".preview.ass" if preview else ".ass"
    output = _write_rendered(paths, f"{paths.title_id}.zh-CN-ja{suffix}", rendered)
    update_stage(
        paths,
        "compile_jp",
        "preview" if preview else "passed",
        output=str(output.relative_to(paths.title)),
        paired_events=sum(bool(item.get("source_text")) for item in reconciliation["pairs"]),
        source_gaps=sum(item.get("operation") == "source-gap" for item in reconciliation["pairs"]),
    )
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

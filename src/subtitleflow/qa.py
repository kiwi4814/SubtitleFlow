from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .formats.ass import parse_ass
from .glossary import forbidden_hits, load_glossary
from .io import read_json, write_json
from .review import pending_count
from .state import invalidate_after_qa, update_stage
from .workfile import load_workfile
from .util import sha256_file
from .workspace import TitlePaths, verify_sources




def qa_input_snapshot(paths: TitlePaths) -> dict[str, str]:
    """Hash all durable inputs/outputs whose change makes a QA result stale."""
    candidates = [
        paths.title_config,
        paths.manifest,
        paths.project_canon / "glossary.json",
        paths.title_canon / "glossary.json",
        paths.review / "candidates.json",
        paths.work / "tw.json",
        paths.work / "jp.json",
        paths.release / f"{paths.title_id}.zh-CN.tw.ass",
        paths.release / f"{paths.title_id}.zh-CN-ja.ass",
    ]
    snapshot: dict[str, str] = {}
    for path in candidates:
        if path.is_file():
            snapshot[str(path.relative_to(paths.title if path.is_relative_to(paths.title) else paths.repo))] = sha256_file(path)
    return dict(sorted(snapshot.items()))

def _display_width(text: str, font_size: int) -> float:
    width = 0.0
    for char in text:
        code = ord(char)
        if char in " \t":
            width += font_size * 0.28
        elif 0x2E80 <= code <= 0x9FFF or 0x3040 <= code <= 0x30FF or 0xAC00 <= code <= 0xD7AF:
            width += font_size
        elif char.isupper():
            width += font_size * 0.62
        else:
            width += font_size * 0.52
    return width


def _rows(text: str) -> list[str]:
    return text.replace(r"\N", "\n").split("\n") if text else []


def structural_qa(paths: TitlePaths) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    try:
        integrity = verify_sources(paths)
    except Exception as exc:
        integrity = {"ok": False, "error": str(exc)}
        errors.append({"kind": "source-integrity", "message": str(exc)})

    for branch in ("tw", "jp"):
        work_path = paths.work / f"{branch}.json"
        if not work_path.exists():
            continue
        work = load_workfile(paths, branch)
        previous_end = -1
        for unit in work.units:
            if unit.end_ms <= unit.start_ms:
                errors.append({"branch": branch, "unit": unit.id, "kind": "invalid-timing"})
            if not unit.final_text.strip():
                errors.append({"branch": branch, "unit": unit.id, "kind": "empty-final-text"})
            if branch == "jp" and not (unit.source_text or "").strip():
                errors.append({"branch": branch, "unit": unit.id, "kind": "missing-japanese-source"})
            if previous_end > unit.start_ms:
                warnings.append(
                    {
                        "branch": branch,
                        "unit": unit.id,
                        "kind": "overlap",
                        "overlap_ms": previous_end - unit.start_ms,
                    }
                )
            previous_end = max(previous_end, unit.end_ms)
            if "low-alignment-confidence" in unit.flags or "low-japanese-alignment-confidence" in unit.flags:
                warnings.append({"branch": branch, "unit": unit.id, "kind": "low-alignment-confidence"})
    pending = pending_count(paths)
    if pending:
        errors.append({"kind": "pending-human-review", "count": pending})
    report = {
        "schema_version": 1,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "source_integrity": integrity,
    }
    write_json(paths.qa / "structural.json", report)
    return report


def terminology_qa(paths: TitlePaths) -> dict[str, Any]:
    rules = load_glossary(paths)
    hits: list[dict[str, Any]] = []
    for branch in ("tw", "jp"):
        work_path = paths.work / f"{branch}.json"
        if not work_path.exists():
            continue
        work = load_workfile(paths, branch)
        for unit in work.units:
            for hit in forbidden_hits(unit.final_text, rules, branch):
                hits.append({"branch": branch, "unit": unit.id, **hit})
    report = {"schema_version": 1, "ok": not hits, "hits": hits}
    write_json(paths.qa / "terminology.json", report)
    return report


def layout_qa(paths: TitlePaths) -> dict[str, Any]:
    config = read_json(paths.title_config)
    ass_cfg = config.get("ass", {})
    target_size = int(ass_cfg.get("target_size", 48))
    source_size = int(ass_cfg.get("source_size", 38))
    max_rows_warning = int(ass_cfg.get("max_visual_rows_warning", 4))
    usable_width = 1840.0
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    for branch in ("tw", "jp"):
        path = paths.work / f"{branch}.json"
        if not path.exists():
            continue
        work = load_workfile(paths, branch)
        for unit in work.units:
            target_rows = _rows(unit.final_text)
            source_rows = _rows(unit.source_text or "") if branch == "jp" else []
            visual_rows = len(target_rows) + len(source_rows)
            max_target = max((_display_width(row, target_size) for row in target_rows), default=0.0)
            max_source = max((_display_width(row, source_size) for row in source_rows), default=0.0)
            ratio = max(max_target, max_source) / usable_width if usable_width else 0.0
            severity: str | None = None
            if ratio > 1.0:
                errors.append({"branch": branch, "unit": unit.id, "kind": "estimated-overflow", "width_ratio": round(ratio, 3)})
                severity = "error"
            elif ratio > 0.9:
                warnings.append({"branch": branch, "unit": unit.id, "kind": "very-wide", "width_ratio": round(ratio, 3)})
                severity = "warning"
            elif ratio > 0.82:
                warnings.append({"branch": branch, "unit": unit.id, "kind": "wide", "width_ratio": round(ratio, 3)})
                severity = "warning"
            if visual_rows >= max_rows_warning:
                warnings.append({"branch": branch, "unit": unit.id, "kind": "many-rows", "rows": visual_rows})
                severity = severity or "warning"
            if severity or unit.flags:
                candidates.append(
                    {
                        "branch": branch,
                        "unit": unit.id,
                        "timestamp_ms": unit.start_ms + max(0, unit.end_ms - unit.start_ms) // 2,
                        "severity": severity or "inspect",
                        "rows": visual_rows,
                        "width_ratio": round(ratio, 3),
                        "flags": unit.flags,
                    }
                )
    candidates.sort(key=lambda item: (item["severity"] != "error", -item["width_ratio"]))
    report = {
        "schema_version": 1,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "preview_candidates": candidates[:30],
        "assumptions": {
            "play_res_x": 1920,
            "usable_width": int(usable_width),
            "static_estimate_only": True,
        },
    }
    write_json(paths.qa / "layout.json", report)
    return report


def compiled_ass_qa(paths: TitlePaths) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for ass in sorted(paths.release.glob("*.ass")):
        try:
            doc = parse_ass(ass)
            results.append(
                {
                    "file": ass.name,
                    "events": len(doc.events),
                    "protected_events": sum(event.protected for event in doc.events),
                }
            )
        except Exception as exc:
            errors.append({"file": ass.name, "error": str(exc)})
    report = {"schema_version": 1, "ok": not errors, "results": results, "errors": errors}
    write_json(paths.qa / "compiled-ass.json", report)
    return report


def run_all_qa(paths: TitlePaths) -> dict[str, Any]:
    invalidate_after_qa(paths)
    structural = structural_qa(paths)
    terminology = terminology_qa(paths)
    layout = layout_qa(paths)
    compiled = compiled_ass_qa(paths)
    overall = structural["ok"] and terminology["ok"] and layout["ok"] and compiled["ok"]
    report = {
        "schema_version": 1,
        "ok": overall,
        "structural": structural,
        "terminology": terminology,
        "layout": layout,
        "compiled_ass": compiled,
        "input_snapshot": qa_input_snapshot(paths),
    }
    write_json(paths.qa / "summary.json", report)
    update_stage(paths, "qa", "passed" if overall else "failed")
    return report

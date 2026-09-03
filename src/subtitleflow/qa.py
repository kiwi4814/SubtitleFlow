from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .fonts import audit_fonts, configured_font_map_path, configured_font_registry_path
from .formats.ass import parse_ass
from .glossary import load_glossary, terminology_hits
from .io import read_json, write_json
from .layout import block_geometry
from .normalize import load_normalized
from .renderqa import run_renderer_qa
from .review import approved_review_errors, pending_count, unimported_proposal_files
from .srp.registry import research_mode
from .srp.resolver import effective_semantic_digest, ensure_resolved
from .state import invalidate_after_qa, update_stage
from .style import ass_style_values, layout_settings, load_style_profile
from .util import sha256_file
from .workfile import load_workfile
from .workflow import active_branches, branch_release_filename
from .workspace import TitlePaths, verify_sources


def qa_input_snapshot(paths: TitlePaths) -> dict[str, str]:
    candidates = [
        paths.title_config,
        paths.manifest,
        paths.review / "candidates.json",
        paths.qa / "fonts.json",
        paths.work / "bilingual-reconciliation.json",
        paths.work / "bilingual-coverage.json",
    ]
    candidates.extend(sorted(paths.project_canon.glob("*.json")))
    candidates.extend(sorted(paths.title_canon.glob("*.json")))
    candidates.append(configured_font_map_path(paths))
    candidates.append(configured_font_registry_path(paths))
    for branch in ("clean", "tw", "jp"):
        candidates.append(paths.work / f"{branch}.json")
        candidates.append(paths.release / branch_release_filename(paths.title_id, branch))
    candidates.extend(unimported_proposal_files(paths))
    try:
        profile = load_style_profile(paths)
        candidates.append(Path(str(profile["_profile_path"])))
    except Exception:
        pass
    snapshot: dict[str, str] = {}
    for path in candidates:
        if path.is_file():
            try:
                key = str(path.relative_to(paths.title))
            except ValueError:
                key = (
                    str(path.relative_to(paths.repo))
                    if path.is_relative_to(paths.repo)
                    else str(path)
                )
            snapshot[key] = sha256_file(path)
    try:
        semantic_digest = effective_semantic_digest(paths)
    except Exception:
        semantic_digest = "STALE"
    if semantic_digest is not None:
        snapshot["research:effective-semantic"] = semantic_digest
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


def _duplicate_sign_candidates(paths: TitlePaths) -> list[dict[str, Any]]:
    manifest = read_json(paths.manifest)
    results: list[dict[str, Any]] = []
    for role in ("A", "S"):
        if role not in manifest.get("sources", {}):
            continue
        normalized = load_normalized(paths, role)
        signs = [cue for cue in normalized.cues if cue.semantic_role == "screen-text"]
        dialogue = [cue for cue in normalized.cues if cue.semantic_role == "dialogue"]
        for sign in signs:
            for spoken in dialogue:
                if spoken.end_ms < sign.start_ms - 500 or spoken.start_ms > sign.end_ms + 500:
                    continue
                left = "".join(sign.plain_text.split())
                right = "".join(spoken.plain_text.split())
                if not left or not right:
                    continue
                ratio = SequenceMatcher(None, left, right).ratio()
                if ratio >= 0.88:
                    results.append(
                        {
                            "kind": "duplicate-screen-text-dialogue",
                            "role": role,
                            "screen_cue": sign.id,
                            "dialogue_cue": spoken.id,
                            "similarity": round(ratio, 3),
                        }
                    )
    return results


def structural_qa(paths: TitlePaths) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    try:
        integrity = verify_sources(paths)
    except Exception as exc:
        integrity = {"ok": False, "error": str(exc)}
        errors.append({"kind": "source-integrity", "message": str(exc)})

    for branch in active_branches(paths):
        work_path = paths.work / f"{branch}.json"
        if not work_path.exists():
            errors.append({"branch": branch, "kind": "missing-workfile"})
            continue
        work = load_workfile(paths, branch)
        previous_end = -1
        for unit in work.units:
            if unit.end_ms <= unit.start_ms:
                errors.append({"branch": branch, "unit": unit.id, "kind": "invalid-timing"})
            if not unit.final_text.strip():
                errors.append({"branch": branch, "unit": unit.id, "kind": "empty-final-text"})
            if branch == "jp":
                if unit.source_operation == "source-gap":
                    warnings.append({"branch": branch, "unit": unit.id, "kind": "SOURCE_GAP"})
                elif unit.source_operation == "unresolved":
                    errors.append(
                        {
                            "branch": branch,
                            "unit": unit.id,
                            "kind": "unresolved-bilingual-reconciliation",
                        }
                    )
                elif not (unit.source_text or "").strip():
                    errors.append(
                        {"branch": branch, "unit": unit.id, "kind": "missing-japanese-source"}
                    )
            if (
                branch == "clean"
                and work.metadata.get("source_assisted")
                and not (unit.source_text or "").strip()
            ):
                warnings.append(
                    {"branch": branch, "unit": unit.id, "kind": "missing-source-evidence"}
                )
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
            if any("low-" in flag and "alignment-confidence" in flag for flag in unit.flags):
                warnings.append(
                    {"branch": branch, "unit": unit.id, "kind": "low-alignment-confidence"}
                )

    coverage_path = paths.work / "bilingual-coverage.json"
    reconciliation_path = paths.work / "bilingual-reconciliation.json"
    if "jp" in active_branches(paths) and (
        not coverage_path.is_file() or not reconciliation_path.is_file()
    ):
        errors.append(
            {
                "kind": "missing-source-accounting",
                "message": "rerun `subflow prepare` to generate fragment-level source accounting",
            }
        )
    if coverage_path.is_file() and reconciliation_path.is_file():
        coverage = read_json(coverage_path)
        if int(coverage.get("fabricated", 0)) != 0:
            errors.append(
                {"kind": "source-fabrication", "count": int(coverage.get("fabricated", 0))}
            )
        reconciliation = read_json(reconciliation_path)
        if (
            int(coverage.get("schema_version", 1)) < 2
            or int(reconciliation.get("schema_version", 1)) < 2
        ):
            errors.append(
                {
                    "kind": "source-accounting-migration-required",
                    "message": "rerun `subflow prepare` to generate fragment-level source accounting",
                }
            )
        if reconciliation.get("coverage") != coverage:
            errors.append({"kind": "source-accounting-coverage-mismatch"})
        blocker_fields = {
            "source_spoken_fragments_unresolved": "unresolved-source-fragments",
            "source_events_presented_partial": "partially-presented-source-events",
            "invalid_final_refs": "invalid-final-refs",
            "invalid_fragment_ownership": "invalid-fragment-ownership",
            "substantive_source_order_violations": "substantive-source-order-violations",
            "missing_disposition_reasons": "missing-source-disposition-reasons",
        }
        for field, kind in blocker_fields.items():
            count = int(coverage.get(field, 0))
            if count:
                errors.append({"kind": kind, "count": count})
        directly_blocking_issues = {
            "duplicate-final-ref",
            "presented-fragment-without-final-ref",
            "nonpresented-fragment-with-final-ref",
        }
        for issue in reconciliation.get("accounting_issues", []):
            if isinstance(issue, dict) and issue.get("kind") in directly_blocking_issues:
                errors.append({"kind": "source-accounting-integrity", "issue": issue})
    warnings.extend(_duplicate_sign_candidates(paths))
    errors.extend(approved_review_errors(paths))
    pending = pending_count(paths)
    if pending:
        errors.append({"kind": "pending-human-review", "count": pending})
    report = {
        "schema_version": 2,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "source_integrity": integrity,
    }
    write_json(paths.qa / "structural.json", report)
    return report


def terminology_qa(paths: TitlePaths) -> dict[str, Any]:
    rules = load_glossary(paths)
    mode = research_mode(paths)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    hits: list[dict[str, Any]] = []
    for branch in active_branches(paths):
        work_path = paths.work / f"{branch}.json"
        if not work_path.exists():
            continue
        work = load_workfile(paths, branch)
        for unit in work.units:
            for hit in terminology_hits(unit.final_text, rules, branch):
                item = {"branch": branch, "unit": unit.id, **hit}
                hits.append(item)
                is_srp = hit.get("origin") == "srp"
                kind = hit.get("kind")
                enforcement = hit.get("enforcement")
                if (is_srp and mode == "advisory") or kind == "deprecated":
                    warnings.append(item)
                elif is_srp and mode == "enforce":
                    if kind == "forbidden" or enforcement == "locked":
                        errors.append(item)
                    else:
                        warnings.append(item)
                elif kind == "forbidden" or enforcement == "locked":
                    errors.append(item)
                else:
                    warnings.append(item)
    report = {
        "schema_version": 2,
        "ok": not errors,
        "mode": mode,
        "errors": errors,
        "warnings": warnings,
        "hits": hits,
    }
    write_json(paths.qa / "terminology.json", report)
    return report


def layout_qa(paths: TitlePaths) -> dict[str, Any]:
    zh_style = ass_style_values(paths, "SF-ZH")
    ja_style = ass_style_values(paths, "SF-JA")
    target_size = int(float(zh_style.get("Fontsize", 60)))
    source_size = int(float(ja_style.get("Fontsize", 50)))
    profile = load_style_profile(paths)
    resolution = profile.get("play_resolution", {})
    play_x = int(resolution.get("x", 1920))
    play_y = int(resolution.get("y", 1080))
    layout = layout_settings(paths)
    max_rows_warning = int(layout.get("max_visual_rows_warning", 4))
    usable_width = float(layout.get("usable_width", 1840))
    wide_ratio = float(layout.get("wide_warning_ratio", 0.82))
    very_wide_ratio = float(layout.get("very_wide_warning_ratio", 0.90))
    overflow_ratio = float(layout.get("overflow_ratio", 1.0))
    warnings: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    for branch in active_branches(paths):
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
            reasons: list[str] = []
            if ratio > overflow_ratio:
                errors.append(
                    {
                        "branch": branch,
                        "unit": unit.id,
                        "kind": "estimated-overflow",
                        "width_ratio": round(ratio, 3),
                    }
                )
                severity = "error"
                reasons.append("overflow")
            elif ratio > very_wide_ratio:
                warnings.append(
                    {
                        "branch": branch,
                        "unit": unit.id,
                        "kind": "very-wide",
                        "width_ratio": round(ratio, 3),
                    }
                )
                severity = "warning"
                reasons.append("very-wide")
            elif ratio > wide_ratio:
                warnings.append(
                    {
                        "branch": branch,
                        "unit": unit.id,
                        "kind": "wide",
                        "width_ratio": round(ratio, 3),
                    }
                )
                severity = "warning"
                reasons.append("wide")
            if visual_rows >= max_rows_warning:
                warnings.append(
                    {"branch": branch, "unit": unit.id, "kind": "many-rows", "rows": visual_rows}
                )
                severity = severity or "warning"
                reasons.append("excessive-row-count")
            geometry = block_geometry(
                play_res_x=play_x,
                play_res_y=play_y,
                target_style=zh_style,
                source_style=ja_style if branch == "jp" else None,
                layout=layout,
                target_text=unit.final_text,
                source_text=unit.source_text if branch == "jp" else None,
                mode="bilingual" if branch == "jp" else "clean",
                semantic_role=unit.semantic_role,
            )
            if branch == "jp" and geometry.source_y is not None:
                source_top = geometry.source_y - geometry.source_height
                if geometry.target_y >= source_top:
                    errors.append(
                        {
                            "branch": branch,
                            "unit": unit.id,
                            "kind": "bilingual-order-risk",
                            "geometry": geometry.to_dict(),
                        }
                    )
                    severity = "error"
                    reasons.append("bilingual-order-risk")
                if geometry.target_y - geometry.target_height < 0:
                    warnings.append(
                        {
                            "branch": branch,
                            "unit": unit.id,
                            "kind": "collision-risk",
                            "geometry": geometry.to_dict(),
                        }
                    )
                    severity = severity or "warning"
                    reasons.append("collision-risk")
            if (
                severity
                or unit.flags
                or (source_rows and len(source_rows) > 1)
                or unit.semantic_role.startswith("song-")
            ):
                if len(source_rows) > 1:
                    reasons.append("source-multiline")
                if unit.semantic_role.startswith("song-"):
                    reasons.append(unit.semantic_role)
                candidates.append(
                    {
                        "branch": branch,
                        "unit": unit.id,
                        "timestamp_ms": unit.start_ms + max(0, unit.end_ms - unit.start_ms) // 2,
                        "severity": severity or "inspect",
                        "rows": visual_rows,
                        "width_ratio": round(ratio, 3),
                        "flags": unit.flags,
                        "reasons": sorted(set(reasons)),
                        "geometry": geometry.to_dict(),
                    }
                )
    candidates.sort(key=lambda item: (item["severity"] != "error", -item["width_ratio"]))
    report = {
        "schema_version": 2,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "preview_candidates": candidates[:30],
        "assumptions": {
            "play_res_x": play_x,
            "play_res_y": play_y,
            "usable_width": int(usable_width),
            "static_estimate_only": True,
            "renderer_is_visual_authority": True,
            "style_profile": profile.get("id"),
        },
    }
    write_json(paths.qa / "layout.json", report)
    return report


def compiled_ass_qa(paths: TitlePaths) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    coverage = (
        read_json(paths.work / "bilingual-coverage.json")
        if (paths.work / "bilingual-coverage.json").is_file()
        else {}
    )
    for ass in sorted(paths.release.glob("*.ass")):
        if ass.name.endswith(".preview.ass"):
            continue
        try:
            doc = parse_ass(ass)
            item = {
                "file": ass.name,
                "events": len(doc.events),
                "protected_events": sum(event.protected for event in doc.events),
            }
            if ass.name == branch_release_filename(paths.title_id, "jp") and coverage:
                source_events = sum(
                    event.fields.get("Style", "") == "SF-JA" for event in doc.events
                )
                expected = int(coverage.get("strict_paired", 0))
                item["generated_source_events"] = source_events
                item["expected_paired_source_events"] = expected
                if source_events > expected:
                    errors.append(
                        {
                            "file": ass.name,
                            "kind": "source-fabrication",
                            "actual": source_events,
                            "expected_max": expected,
                        }
                    )
                elif source_events < expected:
                    errors.append(
                        {
                            "file": ass.name,
                            "kind": "missing-paired-source-event",
                            "actual": source_events,
                            "expected": expected,
                        }
                    )
            results.append(item)
        except Exception as exc:
            errors.append({"file": ass.name, "error": str(exc)})
    report = {"schema_version": 2, "ok": not errors, "results": results, "errors": errors}
    write_json(paths.qa / "compiled-ass.json", report)
    return report


def run_all_qa(paths: TitlePaths) -> dict[str, Any]:
    if research_mode(paths) in {"advisory", "enforce"}:
        ensure_resolved(paths)
    invalidate_after_qa(paths)
    structural = structural_qa(paths)
    terminology = terminology_qa(paths)
    layout = layout_qa(paths)
    compiled = compiled_ass_qa(paths)
    fonts = audit_fonts(paths)
    config = read_json(paths.title_config)
    gates = config.get("quality_gates", {})
    font_config = config.get("fonts", {})
    fonts_required = bool(
        gates.get("require_fonts", True) or font_config.get("require_for_release", True)
    )
    if fonts.get("ok"):
        renderer = run_renderer_qa(paths)
    elif fonts_required:
        renderer = {
            "schema_version": 1,
            "status": "not-run",
            "ok": True,
            "reason": "required fonts are unresolved; the separate release font gate remains failed",
        }
        write_json(paths.qa / "render-summary.json", renderer)
    else:
        renderer = {
            "schema_version": 1,
            "status": "not-run",
            "ok": True,
            "reason": "font QA is optional for this project and requested families are unresolved",
        }
        write_json(paths.qa / "render-summary.json", renderer)
    renderer_ok = renderer.get("status") == "not-run" or bool(renderer.get("ok"))
    overall = (
        structural["ok"] and terminology["ok"] and layout["ok"] and compiled["ok"] and renderer_ok
    )
    report = {
        "schema_version": 2,
        "ok": overall,
        "structural": structural,
        "terminology": terminology,
        "layout": layout,
        "compiled_ass": compiled,
        "fonts": fonts,
        "renderer": renderer,
        "input_snapshot": qa_input_snapshot(paths),
    }
    write_json(paths.qa / "summary.json", report)
    update_stage(paths, "qa", "passed" if overall else "failed")
    return report

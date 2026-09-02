#!/usr/bin/env python3
"""Run a reproducible M01 source-assisted prepare pilot from repository evidence."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

from subtitleflow.alignment import editable_cues
from subtitleflow.cli import main as cli_main
from subtitleflow.cue_views import evidence_cues
from subtitleflow.io import read_json
from subtitleflow.normalize import load_normalized
from subtitleflow.workfile import load_workfile
from subtitleflow.workspace import title_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
JOB_PATH = REPO_ROOT / "examples" / "jobs" / "doraemon-m01.jp-audio-zh-cn.json"
JOB_SCHEMA_PATH = REPO_ROOT / "contracts" / "subtitle-job.schema.json"


def _run_cli(argv: list[str]) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli_main(argv)
    if code != 0:
        detail = stderr.getvalue().strip() or stdout.getvalue().strip() or "no diagnostic output"
        raise RuntimeError(f"subflow command failed ({code}): {' '.join(argv)}\n{detail}")


def _input_paths(job: dict[str, object]) -> dict[str, Path]:
    inputs = job.get("inputs")
    if not isinstance(inputs, list):
        raise RuntimeError("job inputs must be a list")
    result: dict[str, Path] = {}
    for item in inputs:
        if not isinstance(item, dict):
            raise RuntimeError("job input must be an object")
        role = item.get("role_hint")
        relative = item.get("path")
        if role not in {"S", "C"} or not isinstance(relative, str):
            continue
        path = (REPO_ROOT / relative).resolve()
        if not path.is_file():
            raise RuntimeError(f"M01 evidence file is missing: {relative}")
        result[str(role)] = path
    missing = {"S", "C"} - set(result)
    if missing:
        raise RuntimeError("M01 pilot job is missing role hints: " + ", ".join(sorted(missing)))
    return result


def _alignment_metrics(alignment: dict[str, object]) -> dict[str, object]:
    groups = alignment.get("groups", [])
    if not isinstance(groups, list):
        raise RuntimeError("alignment report groups must be a list")
    kind_counts: Counter[str] = Counter()
    left_total = 0
    left_matched = 0
    right_total = 0
    right_matched = 0
    for group in groups:
        if not isinstance(group, dict):
            continue
        kind_counts[str(group.get("kind", "unknown"))] += 1
        left_ids = group.get("left_ids", [])
        right_ids = group.get("right_ids", [])
        if not isinstance(left_ids, list) or not isinstance(right_ids, list):
            continue
        left_total += len(left_ids)
        right_total += len(right_ids)
        if left_ids and right_ids:
            left_matched += len(left_ids)
            right_matched += len(right_ids)
    return {
        "kind_counts": dict(sorted(kind_counts.items())),
        "left_cues": left_total,
        "left_matched_cues": left_matched,
        "left_coverage": round(left_matched / left_total, 6) if left_total else 0.0,
        "right_cues": right_total,
        "right_matched_cues": right_matched,
        "right_coverage": round(right_matched / right_total, 6) if right_total else 0.0,
    }


def _cue_diagnostics(cues) -> dict[str, object]:
    style_counts = Counter(cue.style or "<empty>" for cue in cues)
    role_counts = Counter(cue.semantic_role for cue in cues)
    timing_counts = Counter((cue.start_ms, cue.end_ms) for cue in cues)
    return {
        "style_counts": dict(sorted(style_counts.items())),
        "semantic_role_counts": dict(sorted(role_counts.items())),
        "unique_timing_spans": len(timing_counts),
        "multi_event_timing_spans": sum(count > 1 for count in timing_counts.values()),
        "max_events_same_timing_span": max(timing_counts.values(), default=0),
    }


def _matched_right_ids(alignment: dict[str, object]) -> set[str]:
    groups = alignment.get("groups", [])
    if not isinstance(groups, list):
        raise RuntimeError("alignment report groups must be a list")
    result: set[str] = set()
    for group in groups:
        if not isinstance(group, dict):
            continue
        left_ids = group.get("left_ids", [])
        right_ids = group.get("right_ids", [])
        if not isinstance(left_ids, list) or not isinstance(right_ids, list):
            continue
        if left_ids and right_ids:
            result.update(str(cue_id) for cue_id in right_ids)
    return result


def _cue_view(cue) -> dict[str, object]:
    return {
        "id": cue.id,
        "start_ms": cue.start_ms,
        "end_ms": cue.end_ms,
        "style": cue.style,
        "semantic_role": cue.semantic_role,
        "text": cue.plain_text,
    }


def _unit_view(unit) -> dict[str, object]:
    return {
        "id": unit.id,
        "start_ms": unit.start_ms,
        "end_ms": unit.end_ms,
        "semantic_role": unit.semantic_role,
        "text": unit.final_text,
    }


def _diagnostic_samples(alignment: dict[str, object], left_units, right_cues) -> dict[str, object]:
    left_map = {unit.id: unit for unit in left_units}
    right_map = {cue.id: cue for cue in right_cues}
    groups = alignment.get("groups", [])
    if not isinstance(groups, list):
        raise RuntimeError("alignment report groups must be a list")

    unmatched_right: list[dict[str, object]] = []
    low_confidence: list[dict[str, object]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        left_ids = group.get("left_ids", [])
        right_ids = group.get("right_ids", [])
        if not isinstance(left_ids, list) or not isinstance(right_ids, list):
            continue
        if not left_ids and right_ids and len(unmatched_right) < 24:
            for cue_id in right_ids:
                cue = right_map.get(str(cue_id))
                if cue is not None and len(unmatched_right) < 24:
                    unmatched_right.append(_cue_view(cue))
        confidence = float(group.get("confidence", 0.0))
        if left_ids and right_ids and confidence < 0.72 and len(low_confidence) < 16:
            low_confidence.append(
                {
                    "id": group.get("id"),
                    "kind": group.get("kind"),
                    "confidence": confidence,
                    "left": [
                        _unit_view(left_map[str(unit_id)])
                        for unit_id in left_ids
                        if str(unit_id) in left_map
                    ],
                    "right": [
                        _cue_view(right_map[str(cue_id)])
                        for cue_id in right_ids
                        if str(cue_id) in right_map
                    ],
                }
            )
    return {
        "unmatched_right_first_24": unmatched_right,
        "low_confidence_first_16": low_confidence,
    }


def run_pilot() -> dict[str, object]:
    job = read_json(JOB_PATH)
    schema = read_json(JOB_SCHEMA_PATH)
    Draft202012Validator(schema).validate(job)
    sources = _input_paths(job)

    project_id = str(job.get("project_id") or "doraemon")
    title_id = str(job.get("title_id") or "m01")
    series_id = str(job.get("series_id") or project_id)
    display_name = str(job.get("display_name") or title_id)

    with tempfile.TemporaryDirectory(prefix="subtitleflow-m01-pilot-") as temp_dir:
        workspace = Path(temp_dir)
        (workspace / "projects").mkdir()
        (workspace / "pyproject.toml").write_text(
            "[project]\nname='subtitleflow-m01-pilot'\nversion='0'\n", encoding="utf-8"
        )
        repo_arg = str(workspace)
        _run_cli(["--repo", repo_arg, "project", "init", project_id, "--name", "Doraemon"])
        _run_cli(
            [
                "--repo",
                repo_arg,
                "title",
                "init",
                project_id,
                title_id,
                "--name",
                display_name,
                "--profile",
                "source-assisted",
                "--series-id",
                series_id,
            ]
        )
        for role in ("S", "C"):
            _run_cli(
                [
                    "--repo",
                    repo_arg,
                    "source",
                    "add",
                    project_id,
                    title_id,
                    role,
                    str(sources[role]),
                ]
            )
        _run_cli(["--repo", repo_arg, "prepare", project_id, title_id])

        paths = title_paths(workspace, project_id, title_id)
        normalized_s = load_normalized(paths, "S")
        normalized_c = load_normalized(paths, "C")
        clean_work = load_workfile(paths, "clean")
        s_editable = editable_cues(normalized_s.cues)
        c_editable = editable_cues(normalized_c.cues)
        c_evidence = evidence_cues(normalized_c.cues)
        protected_evidence_ids = {cue.id for cue in c_evidence if cue.protected}

        alignment = read_json(paths.work / "alignment-CLEAN-C.json")
        matched_protected_ids = protected_evidence_ids & _matched_right_ids(alignment)
        summary = dict(alignment.get("summary", {}))
        coverage = _alignment_metrics(alignment)
        estimated_offset_ms = int(alignment.get("estimated_offset_ms", 0))

        checks = {
            "target_has_editable_dialogue": bool(s_editable),
            "japanese_has_semantic_evidence": bool(c_evidence),
            "protected_japanese_dialogue_survives_as_evidence": bool(protected_evidence_ids),
            "protected_japanese_evidence_is_actually_matched": bool(matched_protected_ids),
            "global_offset_is_plausible": abs(estimated_offset_ms) <= 5_000,
            "target_alignment_coverage_at_least_99_percent": float(coverage["left_coverage"])
            >= 0.99,
            "source_evidence_coverage_at_least_80_percent": float(coverage["right_coverage"])
            >= 0.80,
            "no_unmatched_target_cues": int(summary.get("unmatched_left", 0)) == 0,
        }

        return {
            "pilot": "doraemon-m01-source-assisted-prepare",
            "status": "passed" if all(checks.values()) else "failed",
            "job": str(JOB_PATH.relative_to(REPO_ROOT)),
            "sources": {
                "S": {
                    "path": str(sources["S"].relative_to(REPO_ROOT)),
                    "sha256": normalized_s.source_sha256,
                },
                "C": {
                    "path": str(sources["C"].relative_to(REPO_ROOT)),
                    "sha256": normalized_c.source_sha256,
                },
            },
            "normalized": {
                "S_total_cues": len(normalized_s.cues),
                "S_editable_cues": len(s_editable),
                "C_total_cues": len(normalized_c.cues),
                "C_protected_cues": normalized_c.protected_count,
                "C_editable_cues": len(c_editable),
                "C_evidence_cues": len(c_evidence),
                "C_accessibility_sfx_cues": sum(
                    cue.semantic_role == "accessibility-sfx" for cue in normalized_c.cues
                ),
                "C_protected_evidence_cues": len(protected_evidence_ids),
                "C_matched_protected_evidence_cues": len(matched_protected_ids),
            },
            "source_diagnostics": {
                "S": _cue_diagnostics(s_editable),
                "C_all": _cue_diagnostics(normalized_c.cues),
                "C_evidence": _cue_diagnostics(c_evidence),
            },
            "alignment": {
                "estimated_offset_ms": estimated_offset_ms,
                "total_cost": alignment.get("total_cost"),
                "summary": summary,
                "coverage": coverage,
                "samples": _diagnostic_samples(alignment, clean_work.units, c_evidence),
            },
            "checks": checks,
        }


def main() -> int:
    result = run_pilot()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

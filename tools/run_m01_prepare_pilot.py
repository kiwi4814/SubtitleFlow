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
    result: dict[str, Path] = {}
    for item in job["inputs"]:  # type: ignore[index]
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
        s_editable = editable_cues(normalized_s.cues)
        c_editable = editable_cues(normalized_c.cues)
        c_evidence = evidence_cues(normalized_c.cues)
        protected_evidence_ids = {cue.id for cue in c_evidence if cue.protected}

        alignment = read_json(paths.work / "alignment-CLEAN-C.json")
        groups = alignment.get("groups", [])
        used_right_ids = {
            str(cue_id)
            for group in groups
            if isinstance(group, dict)
            for cue_id in group.get("right_ids", [])
        }
        matched_protected_ids = protected_evidence_ids & used_right_ids
        summary = dict(alignment.get("summary", {}))
        coverage = _alignment_metrics(alignment)

        checks = {
            "target_has_editable_dialogue": bool(s_editable),
            "japanese_has_semantic_evidence": bool(c_evidence),
            "protected_japanese_dialogue_survives_as_evidence": bool(protected_evidence_ids),
            "alignment_has_matches": int(summary.get("matched", 0)) > 0,
            "alignment_is_not_all_unmatched_left": int(summary.get("unmatched_left", 0))
            < int(summary.get("group_count", 0)),
            "protected_japanese_evidence_is_actually_matched": bool(matched_protected_ids),
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
                "C_protected_evidence_cues": len(protected_evidence_ids),
                "C_matched_protected_evidence_cues": len(matched_protected_ids),
            },
            "alignment_summary": summary,
            "alignment_coverage": coverage,
            "checks": checks,
        }


def main() -> int:
    result = run_pilot()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

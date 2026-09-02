#!/usr/bin/env python3
"""Run the real M01 bilingual Portable Job through the existing JP branch."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from subtitleflow.compile import compile_all
from subtitleflow.formats.ass import parse_ass
from subtitleflow.io import read_json, write_json
from subtitleflow.jobs import load_portable_job, prepare_portable_job
from subtitleflow.pipeline import plan_title
from subtitleflow.portable_release import build_portable_release_bundle
from subtitleflow.qa import run_all_qa
from subtitleflow.review import decide_candidate
from subtitleflow.semantic_packet import build_semantic_packet
from subtitleflow.semantic_proposals import import_semantic_proposal_envelope
from subtitleflow.workfile import load_workfile
from subtitleflow.workspace import title_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
JOB_PATH = REPO_ROOT / "examples" / "jobs" / "doraemon-m01.jp-zh-bilingual.json"
_POS_Y_RE = re.compile(r"\\pos\([^,]+,\s*([-+]?\d+(?:\.\d+)?)\)")


def _event_y(text: str) -> float | None:
    match = _POS_Y_RE.search(text)
    return float(match.group(1)) if match else None


def _style_sizes(ass_path: Path) -> tuple[int, dict[str, float]]:
    play_y = 0
    style_format: list[str] = []
    result: dict[str, float] = {}
    for line in ass_path.read_text(encoding="utf-8").splitlines():
        key, sep, raw = line.partition(":")
        if sep and key.strip().casefold() == "playresy":
            play_y = int(raw.strip())
        if (
            line.lstrip().casefold().startswith("format:")
            and "Fontname" in line
            and "Fontsize" in line
        ):
            style_format = [item.strip() for item in raw.split(",")]
        elif line.lstrip().casefold().startswith("style:") and style_format:
            values = [item.strip() for item in raw.split(",")]
            if len(values) != len(style_format):
                continue
            fields = dict(zip(style_format, values, strict=True))
            if fields.get("Name") in {"SF-ZH", "SF-JA"}:
                result[fields["Name"]] = float(fields["Fontsize"])
    if play_y <= 0 or set(result) != {"SF-ZH", "SF-JA"}:
        raise RuntimeError("Could not inspect generated M01 PlayRes/font sizes")
    return play_y, result


def _compiled_checks(ass_path: Path, reconciliation: dict[str, object]) -> dict[str, object]:
    doc = parse_ass(ass_path)
    zh_events = [event for event in doc.events if event.fields.get("Style") == "SF-ZH"]
    ja_events = [event for event in doc.events if event.fields.get("Style") == "SF-JA"]
    pairs = reconciliation.get("pairs", [])
    if not isinstance(pairs, list):
        raise RuntimeError("bilingual reconciliation pairs must be a list")
    paired_count = sum(
        isinstance(item, dict) and bool(str(item.get("source_text") or "").strip())
        for item in pairs
    )

    ja_by_span: dict[tuple[int, int], list[float]] = {}
    for event in ja_events:
        y = _event_y(event.fields.get("Text", ""))
        if y is not None:
            ja_by_span.setdefault((event.start_ms, event.end_ms), []).append(y)
    paired_zh: list[tuple[object, list[float]]] = []
    for event in zh_events:
        ys = ja_by_span.get((event.start_ms, event.end_ms))
        if ys:
            paired_zh.append((event, ys))
    order_ok = bool(paired_zh) and all(
        (y := _event_y(event.fields.get("Text", ""))) is not None and y < min(ja_ys)
        for event, ja_ys in paired_zh
    )

    play_y, sizes = _style_sizes(ass_path)
    physical = {name: round(size * 1080 / play_y, 3) for name, size in sizes.items()}
    return {
        "play_res_y": play_y,
        "script_font_sizes": sizes,
        "physical_1080p_font_sizes": physical,
        "zh_events": len(zh_events),
        "ja_events": len(ja_events),
        "paired_reconciliation_rows": paired_count,
        "chinese_above_japanese": order_ok,
        "event_count_matches_reconciliation": len(zh_events) == len(pairs)
        and len(ja_events) == paired_count,
        "font_size_target_ok": 58 <= physical["SF-ZH"] <= 62 and 48 <= physical["SF-JA"] <= 52,
    }


def _controlled_human_review_roundtrip(
    paths, semantic_packet: dict[str, object]
) -> dict[str, object]:
    """Exercise one known M01 correction in the temporary CI workspace only."""
    units = semantic_packet.get("units", [])
    if not isinstance(units, list):
        raise RuntimeError("semantic packet units must be a list")
    target = next(
        (
            item
            for item in units
            if isinstance(item, dict)
            and "犹太洲" in str(item.get("current_text", ""))
            and "ユタ州" in str(item.get("source_text", ""))
        ),
        None,
    )
    if target is None:
        raise RuntimeError("M01 controlled review fixture could not find the 犹太洲 / ユタ州 unit")

    original_text = str(target["current_text"])
    corrected_text = original_text.replace("犹太洲", "犹他州")
    source_text = str(target.get("source_text", ""))
    candidate_id = "m01-pilot-utah-state-fix"
    proposal_path = paths.review_proposals / "m01-ci-semantic-proposals.json"
    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        proposal_path,
        {
            "schema_version": 1,
            "kind": "subtitleflow-semantic-proposals",
            "project_id": semantic_packet["project_id"],
            "title_id": semantic_packet["title_id"],
            "branch": semantic_packet["branch"],
            "packet_input_sha256": semantic_packet["packet_input_sha256"],
            "producer": "m01-ci-controlled-fixture",
            "notes": "Regression fixture only; this is not the full production semantic pass.",
            "candidates": [
                {
                    "candidate_id": candidate_id,
                    "branch": semantic_packet["branch"],
                    "unit_id": target["unit_id"],
                    "original_text": original_text,
                    "proposed_text": corrected_text,
                    "change_type": "language-quality",
                    "reason": (
                        "Japanese source evidence explicitly says ユタ州; the Chinese seed "
                        "uses 犹太洲, so the place name should be corrected to 犹他州."
                    ),
                    "confidence": 1.0,
                    "severity": "medium",
                    "evidence": {"source_text": source_text},
                    "primary_evidence": {
                        "role": "C",
                        "text": source_text,
                        "cue_ids": list(target.get("source_text_cue_ids", [])),
                    },
                    "authority_domain": "source-language",
                }
            ],
        },
    )

    imported = import_semantic_proposal_envelope(paths, proposal_path)
    before_decision = plan_title(paths).to_dict()
    if len(imported) != 1 or imported[0].candidate_id != candidate_id:
        raise RuntimeError("M01 controlled review fixture did not import exactly one candidate")

    decided = decide_candidate(
        paths,
        candidate_id,
        "approve",
        note="CI controlled fixture approval; validates Human Review on the JP bilingual branch.",
    )
    reviewed_work = load_workfile(paths, "jp")
    reviewed_unit = next(unit for unit in reviewed_work.units if unit.id == target["unit_id"])
    recorded_change = next(
        (
            change
            for change in reviewed_unit.changes
            if change.rule_id == candidate_id and change.kind == "human-approved-semantic"
        ),
        None,
    )
    after_decision = plan_title(paths).to_dict()
    review_stage = read_json(paths.state).get("stages", {}).get("human_review", {})
    return {
        "controlled_fixture": True,
        "candidate_id": candidate_id,
        "unit_id": target["unit_id"],
        "source_text": source_text,
        "original_text": original_text,
        "approved_text": reviewed_unit.final_text,
        "decision_status": decided.status,
        "change_recorded": recorded_change is not None,
        "before_decision": {
            "next_action": before_decision.get("next_action"),
            "requires_human": before_decision.get("requires_human"),
        },
        "after_decision": {
            "next_action": after_decision.get("next_action"),
            "requires_human": after_decision.get("requires_human"),
        },
        "human_review_stage": review_stage,
    }


def _bundle_roundtrip(paths, job: dict[str, object], workspace: Path) -> dict[str, object]:
    capabilities = {
        "ffmpeg_libass": True,
        "exact_fonts": True,
        "full_video": False,
        "mkvtoolnix": False,
    }
    first = build_portable_release_bundle(
        paths,
        branch="jp",
        source_root=REPO_ROOT,
        bundle_dir=workspace / "bundle-first",
        runtime="chatgpt-web",
        runtime_capabilities=capabilities,
        job=job,
        archive_path=workspace / "SubtitleFlow-M01-JP-ZHCN-Bilingual-Demo-first.zip",
    )
    second = build_portable_release_bundle(
        paths,
        branch="jp",
        source_root=REPO_ROOT,
        bundle_dir=workspace / "bundle-second",
        runtime="chatgpt-web",
        runtime_capabilities=capabilities,
        job=job,
        archive_path=workspace / "SubtitleFlow-M01-JP-ZHCN-Bilingual-Demo-second.zip",
    )
    outputs = [item for item in first.manifest.get("outputs", []) if isinstance(item, dict)]
    qa_status = {
        str(item.get("check")): str(item.get("status"))
        for item in first.manifest.get("qa", [])
        if isinstance(item, dict)
    }
    return {
        "first_sha256": first.archive_sha256,
        "second_sha256": second.archive_sha256,
        "reproducible": first.archive_sha256 == second.archive_sha256,
        "ass_outputs": sum(item.get("kind") == "ass" for item in outputs),
        "render_outputs": sum(item.get("kind") == "render" for item in outputs),
        "qa_status": qa_status,
        "deferred": first.manifest.get("deferred", []),
        "archival_release_frozen": first.manifest.get("portable", {}).get(
            "archival_release_frozen"
        ),
    }


def run_pilot() -> dict[str, object]:
    job = load_portable_job(JOB_PATH, source_root=REPO_ROOT)
    with tempfile.TemporaryDirectory(prefix="subtitleflow-m01-bilingual-pilot-") as temp_dir:
        workspace = Path(temp_dir)
        prepared = prepare_portable_job(JOB_PATH, workspace=workspace, source_root=REPO_ROOT)
        paths = title_paths(workspace, prepared.project_id, prepared.title_id)
        work = load_workfile(paths, "jp")
        packet = build_semantic_packet(paths, "jp")
        review_roundtrip = _controlled_human_review_roundtrip(paths, packet)
        alignment = read_json(paths.work / "alignment-JP-C.json")
        reconciliation = read_json(paths.work / "bilingual-reconciliation.json")
        coverage = read_json(paths.work / "bilingual-coverage.json")

        compiled = compile_all(paths)
        ass_path = Path(compiled["jp"])
        compiled_checks = _compiled_checks(ass_path, reconciliation)
        qa = run_all_qa(paths)
        bundle = _bundle_roundtrip(paths, job, workspace)

        groups = alignment.get("groups", [])
        atomic_target = isinstance(groups, list) and all(
            not isinstance(group, dict)
            or not group.get("left_ids")
            or len(group.get("left_ids", [])) <= 1
            for group in groups
        )
        pairs = reconciliation.get("pairs", [])
        source_provenance = isinstance(pairs, list) and all(
            not isinstance(pair, dict)
            or not str(pair.get("source_text") or "").strip()
            or bool(pair.get("source_text_cue_ids"))
            for pair in pairs
        )
        qa_status = bundle["qa_status"]
        checks = {
            "portable_runner_inferred_bilingual": prepared.workflow_profile == "bilingual",
            "semantic_packet_is_existing_jp_branch": packet.get("branch") == "jp"
            and packet.get("workfile", {}).get("unit_count") == 824,
            "existing_jp_roles_are_reused": work.timing_role == "A"
            and work.language_source_role == "B"
            and work.source_language_role == "C",
            "controlled_review_uses_direct_japanese_evidence": "ユタ州"
            in str(review_roundtrip.get("source_text", "")),
            "controlled_review_materializes_known_m01_fix": "犹他州"
            in str(review_roundtrip.get("approved_text", ""))
            and "犹太洲" not in str(review_roundtrip.get("approved_text", "")),
            "controlled_review_records_change_provenance": review_roundtrip.get("change_recorded")
            is True,
            "jp_reconciliation_keeps_target_atomic": atomic_target
            and alignment.get("group_limits", {}).get("max_left_group") == 1,
            "jp_reconciliation_has_no_unresolved_rows": int(coverage.get("unresolved", -1)) == 0,
            "jp_reconciliation_never_fabricates_source": int(coverage.get("fabricated", -1)) == 0,
            "jp_source_text_has_c_provenance": source_provenance,
            "compiled_contains_both_languages": compiled_checks["zh_events"] == 824
            and int(compiled_checks["ja_events"]) > 0,
            "compiled_keeps_chinese_above_japanese": compiled_checks["chinese_above_japanese"]
            is True,
            "compiled_source_gap_does_not_create_fake_japanese": compiled_checks[
                "event_count_matches_reconciliation"
            ]
            is True,
            "compiled_1080p_font_sizes_are_in_target_range": compiled_checks["font_size_target_ok"]
            is True,
            "deterministic_qa_passes": qa.get("ok") is True,
            "synthetic_libass_render_passes": qa.get("renderer", {}).get("status") == "passed"
            and qa.get("renderer", {}).get("canvas") == "synthetic",
            "exact_font_audit_passes": qa.get("fonts", {}).get("ok") is True,
            "portable_bundle_contains_ass_and_renders": bundle["ass_outputs"] == 1
            and int(bundle["render_outputs"]) > 0,
            "portable_bundle_marks_renderer_and_fonts_passed": qa_status.get("exact-font-audit")
            == "passed"
            and qa_status.get("registered-font-assets") == "passed"
            and qa_status.get("synthetic-libass-render") == "passed",
            "portable_bundle_zip_is_reproducible": bundle["reproducible"] is True,
        }
        return {
            "pilot": "doraemon-m01-jp-zh-bilingual-portable-demo",
            "status": "passed" if all(checks.values()) else "failed",
            "job": str(JOB_PATH.relative_to(REPO_ROOT)),
            "portable_runner": prepared.to_dict(),
            "semantic_packet": {
                "branch": packet.get("branch"),
                "unit_count": packet.get("workfile", {}).get("unit_count"),
                "packet_input_sha256": packet.get("packet_input_sha256"),
            },
            "human_review_roundtrip": review_roundtrip,
            "alignment": {
                "estimated_offset_ms": alignment.get("estimated_offset_ms"),
                "summary": alignment.get("summary"),
                "group_limits": alignment.get("group_limits"),
            },
            "reconciliation": {
                "coverage": coverage,
                "unmatched_source_count": len(reconciliation.get("unmatched_source_cue_ids", [])),
            },
            "compiled": compiled_checks,
            "qa": {
                "ok": qa.get("ok"),
                "renderer_status": qa.get("renderer", {}).get("status"),
                "renderer_canvas": qa.get("renderer", {}).get("canvas"),
                "font_audit_ok": qa.get("fonts", {}).get("ok"),
            },
            "bundle": bundle,
            "checks": checks,
        }


def main() -> int:
    result = run_pilot()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

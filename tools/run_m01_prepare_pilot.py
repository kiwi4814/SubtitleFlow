#!/usr/bin/env python3
"""Run a reproducible M01 portable-job pilot from repository evidence."""

from __future__ import annotations

import json
import tempfile
from collections import Counter
from pathlib import Path

from subtitleflow.alignment import editable_cues
from subtitleflow.cue_views import evidence_cues
from subtitleflow.io import read_json, write_json
from subtitleflow.jobs import load_portable_job, prepare_portable_job
from subtitleflow.normalize import load_normalized
from subtitleflow.pipeline import plan_title
from subtitleflow.review import decide_candidate
from subtitleflow.semantic_packet import build_semantic_packet
from subtitleflow.semantic_proposals import import_semantic_proposal_envelope
from subtitleflow.workfile import load_workfile
from subtitleflow.workspace import title_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
JOB_PATH = REPO_ROOT / "examples" / "jobs" / "doraemon-m01.jp-audio-zh-cn.json"


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
        result[str(role)] = (REPO_ROOT / relative).resolve()
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


def _controlled_human_review_roundtrip(paths, semantic_packet: dict[str, object]) -> dict[str, object]:
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
            "notes": "Regression fixture only; this is not production auto-approval.",
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
        note="CI controlled fixture approval; validates the Human Review materialization path.",
    )
    reviewed_work = load_workfile(paths, "clean")
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
            "can_auto_advance": before_decision.get("can_auto_advance"),
        },
        "after_decision": {
            "next_action": after_decision.get("next_action"),
            "requires_human": after_decision.get("requires_human"),
            "can_auto_advance": after_decision.get("can_auto_advance"),
        },
        "human_review_stage": review_stage,
    }


def run_pilot() -> dict[str, object]:
    job = load_portable_job(JOB_PATH, source_root=REPO_ROOT)
    sources = _input_paths(job)

    with tempfile.TemporaryDirectory(prefix="subtitleflow-m01-pilot-") as temp_dir:
        workspace = Path(temp_dir)
        prepared = prepare_portable_job(
            JOB_PATH,
            workspace=workspace,
            source_root=REPO_ROOT,
        )
        paths = title_paths(workspace, prepared.project_id, prepared.title_id)
        normalized_s = load_normalized(paths, "S")
        normalized_c = load_normalized(paths, "C")
        clean_work = load_workfile(paths, "clean")
        semantic_packet = build_semantic_packet(paths, "clean")
        s_editable = editable_cues(normalized_s.cues)
        c_editable = editable_cues(normalized_c.cues)
        c_evidence = evidence_cues(normalized_c.cues)
        protected_evidence_ids = {cue.id for cue in c_evidence if cue.protected}

        alignment = read_json(paths.work / "alignment-CLEAN-C.json")
        matched_protected_ids = protected_evidence_ids & _matched_right_ids(alignment)
        summary = dict(alignment.get("summary", {}))
        coverage = _alignment_metrics(alignment)
        estimated_offset_ms = int(alignment.get("estimated_offset_ms", 0))
        repository_evidence = prepared.repository_evidence
        research_snapshot = repository_evidence.get("snapshot", {})
        packet_research = semantic_packet.get("research", {})
        packet_branch = (
            packet_research.get("branch", {}) if isinstance(packet_research, dict) else {}
        )
        review_roundtrip = _controlled_human_review_roundtrip(paths, semantic_packet)

        checks = {
            "portable_runner_inferred_source_assisted": prepared.workflow_profile
            == "source-assisted",
            "portable_runner_uses_theatrical_series_identity": prepared.series_id
            == "doraemon-theatrical",
            "repository_evidence_is_bound": repository_evidence.get("bound") is True,
            "repository_evidence_uses_expected_pack": repository_evidence.get("pack_id")
            == "doraemon-theatrical-cn-tw-canon",
            "repository_evidence_maps_clean_branch": repository_evidence.get("branch_map", {}).get(
                "clean"
            )
            == "jp-audio-zh-cn-modern",
            "research_gate_has_no_blockers": research_snapshot.get("blocking_conflicts") == 0
            and research_snapshot.get("blocking_unresolved") == 0,
            "portable_runner_stops_at_semantic_edit": prepared.next_plan.get("next_action")
            == "semantic-edit",
            "semantic_packet_covers_all_target_units": semantic_packet.get("workfile", {}).get(
                "unit_count"
            )
            == 824,
            "semantic_packet_uses_proofread_policy": semantic_packet.get("editorial", {}).get(
                "effective_policy"
            )
            == "proofread",
            "semantic_packet_uses_enforced_research": packet_research.get("mode") == "enforce",
            "semantic_packet_matches_research_digest": packet_research.get(
                "effective_semantic_sha256"
            )
            == research_snapshot.get("effective_semantic_sha256"),
            "semantic_packet_contains_canon_terms": bool(packet_branch.get("terms")),
            "semantic_packet_requires_human_review": semantic_packet.get(
                "proposal_contract", {}
            ).get("human_review_required")
            is True,
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
            "controlled_review_uses_direct_japanese_evidence": "ユタ州"
            in str(review_roundtrip.get("source_text", "")),
            "controlled_review_blocks_for_human_before_decision": review_roundtrip.get(
                "before_decision", {}
            ).get("next_action")
            == "human-review"
            and review_roundtrip.get("before_decision", {}).get("requires_human") is True,
            "controlled_review_materializes_known_m01_fix": "犹他州"
            in str(review_roundtrip.get("approved_text", ""))
            and "犹太洲" not in str(review_roundtrip.get("approved_text", "")),
            "controlled_review_records_change_provenance": review_roundtrip.get(
                "change_recorded"
            )
            is True,
            "controlled_review_advances_to_compile": review_roundtrip.get(
                "after_decision", {}
            ).get("next_action")
            == "compile"
            and review_roundtrip.get("after_decision", {}).get("requires_human") is False,
            "controlled_review_gate_passes_after_decision": review_roundtrip.get(
                "human_review_stage", {}
            ).get("status")
            == "passed",
        }

        return {
            "pilot": "doraemon-m01-portable-job-semantic-review",
            "status": "passed" if all(checks.values()) else "failed",
            "job": str(JOB_PATH.relative_to(REPO_ROOT)),
            "portable_runner": {
                "project_id": prepared.project_id,
                "title_id": prepared.title_id,
                "series_id": prepared.series_id,
                "workflow_profile": prepared.workflow_profile,
                "next_action": prepared.next_plan.get("next_action"),
                "repository_evidence": repository_evidence,
            },
            "semantic_packet": {
                "packet_input_sha256": semantic_packet.get("packet_input_sha256"),
                "packet_sha256": semantic_packet.get("packet_sha256"),
                "unit_count": semantic_packet.get("workfile", {}).get("unit_count"),
                "priority_counts": semantic_packet.get("workfile", {}).get("priority_counts"),
                "editorial_policy": semantic_packet.get("editorial", {}).get("effective_policy"),
                "research_mode": packet_research.get("mode"),
                "effective_semantic_sha256": packet_research.get("effective_semantic_sha256"),
                "srp_branch_id": packet_branch.get("srp_branch_id"),
                "term_count": len(packet_branch.get("terms", [])),
                "decision_count": len(packet_branch.get("decisions", [])),
                "entity_count": len(packet_branch.get("entities", [])),
                "fact_count": len(packet_branch.get("facts", [])),
            },
            "human_review_roundtrip": review_roundtrip,
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

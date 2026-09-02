from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .editorial import editorial_context
from .errors import GateError, ValidationError
from .io import read_json, write_json
from .srp.registry import research_mode
from .srp.resolver import require_research_ready_for_edit, validate_resolved_snapshot
from .state import state_summary
from .util import sha256_file
from .workfile import load_workfile
from .workspace import TitlePaths, effective_series_id, find_repo_root, title_paths


def _canonical_sha(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _source_manifest_summary(paths: TitlePaths) -> dict[str, Any]:
    manifest = read_json(paths.manifest)
    result: dict[str, Any] = {}
    for role, raw in sorted(dict(manifest.get("sources", {})).items()):
        if not isinstance(raw, dict):
            continue
        result[str(role)] = {
            "file": raw.get("file"),
            "sha256": raw.get("sha256"),
            "format": raw.get("format"),
            "encoding": raw.get("encoding"),
        }
    return result


def _research_payload(paths: TitlePaths, branch: str) -> dict[str, Any]:
    mode = research_mode(paths)
    if mode in {"off", "legacy"}:
        return {
            "mode": mode,
            "effective_semantic_sha256": None,
            "pack_digests": [],
            "branch": None,
        }

    snapshot = validate_resolved_snapshot(paths)
    effective = read_json(paths.research_effective)
    branches = effective.get("branches", {})
    branch_data = branches.get(branch) if isinstance(branches, dict) else None
    if not isinstance(branch_data, dict):
        raise GateError(f"Effective Research does not contain active branch {branch!r}")
    return {
        "mode": mode,
        "effective_semantic_sha256": snapshot.get("effective_semantic_sha256"),
        "provenance_sha256": snapshot.get("provenance_sha256"),
        "input_sha256": snapshot.get("input_sha256"),
        "pack_digests": list(snapshot.get("pack_digests", [])),
        "blocking_conflicts": int(snapshot.get("blocking_conflicts", 0)),
        "blocking_unresolved": int(snapshot.get("blocking_unresolved", 0)),
        "branch": branch_data,
    }


def _unit_priority(unit) -> str:
    flags = set(unit.flags)
    if flags & {
        "SOURCE_GAP",
        "missing-source-evidence",
        "missing-language-source",
        "missing-translation-source",
    }:
        return "critical"
    if unit.alignment_confidence < 0.72 or any("confidence" in flag for flag in flags):
        return "high"
    if "context-terminology-review" in flags:
        return "high"
    if unit.source_operation not in {None, "exact", "1:1"}:
        return "medium"
    return "normal"


def _unit_payload(unit) -> dict[str, Any]:
    return {
        "unit_id": unit.id,
        "start_ms": unit.start_ms,
        "end_ms": unit.end_ms,
        "semantic_role": unit.semantic_role,
        "current_text": unit.final_text,
        "normalized_seed_text": unit.normalized_text,
        "source_text": unit.source_text,
        "source_text_cue_ids": list(unit.source_text_cue_ids),
        "timing_cue_ids": list(unit.timing_cue_ids),
        "translation_seed_cue_ids": list(unit.source_cue_ids),
        "parent_source_cue_ids": list(unit.parent_source_cue_ids),
        "source_operation": unit.source_operation,
        "alignment_confidence": unit.alignment_confidence,
        "flags": list(unit.flags),
        "priority": _unit_priority(unit),
    }


def semantic_packet_fingerprint(paths: TitlePaths, branch: str) -> str:
    require_research_ready_for_edit(paths)
    workfile_path = paths.work / f"{branch}.json"
    if not workfile_path.is_file():
        raise ValidationError(f"Workfile does not exist for branch {branch!r}; run prepare first")
    mode = research_mode(paths)
    research_sha: str | None = None
    if mode not in {"off", "legacy"}:
        research_sha = str(validate_resolved_snapshot(paths)["effective_semantic_sha256"])
    payload = {
        "project_id": paths.project_id,
        "title_id": paths.title_id,
        "series_id": effective_series_id(paths),
        "branch": branch,
        "workfile_sha256": sha256_file(workfile_path),
        "source_manifest_sha256": sha256_file(paths.manifest),
        "title_config_sha256": sha256_file(paths.title_config),
        "research_mode": mode,
        "effective_semantic_sha256": research_sha,
    }
    return _canonical_sha(payload)


def build_semantic_packet(paths: TitlePaths, branch: str) -> dict[str, Any]:
    """Build the stable adapter input for one semantic editing pass.

    The packet is read-only production context. It does not mutate workfiles, create review
    candidates, or bypass Human Review. Adapters return only proposed changes through the
    existing proposal importer.
    """
    require_research_ready_for_edit(paths)
    state = state_summary(paths)
    stages = state.get("stages", {})
    if stages.get("alignment_and_seed", {}).get("status") != "passed":
        raise GateError("Semantic packet requires current prepare/alignment evidence")

    work = load_workfile(paths, branch)
    config = read_json(paths.title_config)
    editorial = editorial_context(config, branch=branch).to_dict()
    if editorial.get("assessment_required"):
        raise GateError(
            f"Editorial policy for {branch} is auto but Translation Quality Assessment is missing"
        )

    units = [_unit_payload(unit) for unit in work.units]
    priority_counts = Counter(str(item["priority"]) for item in units)
    research = _research_payload(paths, branch)
    packet_input_sha256 = semantic_packet_fingerprint(paths, branch)
    packet = {
        "schema_version": 1,
        "kind": "subtitleflow-semantic-packet",
        "project_id": paths.project_id,
        "title_id": paths.title_id,
        "series_id": effective_series_id(paths),
        "branch": branch,
        "packet_input_sha256": packet_input_sha256,
        "intent": {
            "timing_role": work.timing_role,
            "translation_seed_role": work.language_source_role,
            "source_language_role": work.source_language_role,
            "semantic_scan_scope": "all-units",
            "minimal_editorial_intervention": bool(
                work.metadata.get("minimal_editorial_intervention", True)
            ),
        },
        "editorial": editorial,
        "sources": {
            "manifest_sha256": sha256_file(paths.manifest),
            "roles": _source_manifest_summary(paths),
        },
        "research": research,
        "workfile": {
            "sha256": sha256_file(paths.work / f"{branch}.json"),
            "unit_count": len(units),
            "priority_counts": dict(sorted(priority_counts.items())),
            "metadata": dict(work.metadata),
        },
        "units": units,
        "proposal_contract": {
            "behavior": "return-only-material-changes",
            "human_review_required": True,
            "required_fields": [
                "branch",
                "unit_id",
                "original_text",
                "proposed_text",
                "change_type",
                "reason",
                "confidence",
            ],
            "recommended_evidence_fields": [
                "primary_evidence",
                "secondary_evidence",
                "authority_domain",
                "evidence_grade",
                "source_conflicts",
            ],
            "original_text_field": "current_text",
        },
    }
    packet["packet_sha256"] = _canonical_sha(packet)
    return packet


def export_semantic_packet(paths: TitlePaths, branch: str, output: Path | None = None) -> Path:
    packet = build_semantic_packet(paths, branch)
    destination = output or (paths.work / f"semantic-packet-{branch}.json")
    destination = destination.expanduser().resolve()
    write_json(destination, packet)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a SubtitleFlow semantic editing packet")
    parser.add_argument("project")
    parser.add_argument("title")
    parser.add_argument("branch")
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    repo = args.repo.resolve() if args.repo else find_repo_root()
    paths = title_paths(repo, args.project, args.title)
    destination = export_semantic_packet(paths, args.branch, args.output)
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

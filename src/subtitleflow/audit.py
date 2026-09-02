from __future__ import annotations

import csv
from collections import Counter
from typing import Any

from .editorial import editorial_context
from .io import read_json, write_json
from .review import list_candidates
from .workfile import load_workfile
from .workflow import active_branches
from .workspace import TitlePaths


def _change_kind(kind: str) -> str:
    value = kind.casefold()
    if "alignment" in value:
        return "alignment correction"
    if "termin" in value or "glossary" in value or "canon" in value:
        return "terminology/canon"
    if "number" in value or "unit" in value:
        return "number/unit"
    if "omission" in value:
        return "omission recovery"
    if "addition" in value:
        return "unsupported addition removal"
    if "register" in value:
        return "register"
    if "segment" in value:
        return "segmentation"
    if "layout" in value or "style" in value:
        return "layout-only"
    return "semantic correction"


def _change_rows(paths: TitlePaths) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for branch in active_branches(paths):
        work_path = paths.work / f"{branch}.json"
        if not work_path.is_file():
            continue
        work = load_workfile(paths, branch)
        for unit in work.units:
            for change in unit.changes:
                substantive = change.before != change.after
                if not substantive:
                    continue
                rows.append(
                    {
                        "branch": branch,
                        "unit_id": unit.id,
                        "start_ms": unit.start_ms,
                        "end_ms": unit.end_ms,
                        "before": change.before,
                        "after": change.after,
                        "change_type": _change_kind(change.kind),
                        "raw_change_kind": change.kind,
                        "reason": change.reason or change.note,
                        "primary_evidence": change.primary_evidence,
                        "secondary_evidence": change.secondary_evidence,
                        "authority_domain": change.authority_domain,
                        "evidence_grade": change.evidence_grade,
                        "source_conflicts": change.source_conflicts,
                        "confidence": change.confidence,
                        "proposal_source": change.proposal_source,
                        "review_status": change.review_status,
                        "final_decision": change.final_decision,
                        "source_cue_ids": unit.source_cue_ids,
                        "source_text_cue_ids": unit.source_text_cue_ids,
                        "source_operation": unit.source_operation,
                    }
                )
    return rows


def _markdown(rows: list[dict[str, Any]]) -> str:
    counts = Counter(row["change_type"] for row in rows)
    lines = [
        "# SubtitleFlow Evidence Change Log",
        "",
        f"Semantic/meaningful changes: **{len(rows)}**",
        "",
    ]
    if counts:
        lines.append("## Summary")
        lines.append("")
        for key, value in sorted(counts.items()):
            lines.append(f"- {key}: {value}")
        lines.append("")
    lines.append("## Changes")
    lines.append("")
    if not rows:
        lines.append("No substantive changes were recorded.")
    for row in rows:
        lines.extend(
            [
                f"### {row['branch']}/{row['unit_id']} · {row['change_type']}",
                "",
                f"- Before: {row['before']}",
                f"- After: {row['after']}",
                f"- Why: {row['reason'] or 'not recorded'}",
                f"- Evidence grade: {row['evidence_grade'] or 'not graded'}",
                f"- Primary evidence: {row['primary_evidence'] or 'not recorded'}",
                f"- Secondary evidence: {row['secondary_evidence'] or 'none'}",
                f"- Source conflicts: {row['source_conflicts'] or 'none'}",
                f"- Review: {row['review_status'] or 'automatic/non-semantic'} / {row['final_decision'] or 'n/a'}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_release_audit(paths: TitlePaths) -> dict[str, Any]:
    rows = _change_rows(paths)
    config = read_json(paths.title_config)
    manifest = read_json(paths.manifest)
    provenance = {
        "schema_version": 1,
        "raw_sources_immutable": True,
        "sources": manifest.get("sources", {}),
        "source_history": manifest.get("history", []),
        "editorial": {
            branch: editorial_context(config, branch=branch).to_dict()
            for branch in active_branches(paths)
        },
    }
    write_json(paths.release / "source-provenance.json", provenance)

    audit = {
        "schema_version": 1,
        "changes": rows,
        "summary": dict(Counter(row["change_type"] for row in rows)),
    }
    write_json(paths.release / "change-audit.json", audit)
    with (paths.release / "change-audit.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fieldnames = [
            "branch",
            "unit_id",
            "start_ms",
            "end_ms",
            "before",
            "after",
            "change_type",
            "reason",
            "evidence_grade",
            "authority_domain",
            "confidence",
            "review_status",
            "final_decision",
            "source_conflicts",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})
    (paths.release / "CHANGELOG_EVIDENCE.md").write_text(_markdown(rows), encoding="utf-8")

    alignment_files = sorted(paths.work.glob("alignment-*.json"))
    alignment = {
        "schema_version": 1,
        "reports": {path.name: read_json(path) for path in alignment_files},
    }
    rec_path = paths.work / "bilingual-reconciliation.json"
    if rec_path.is_file():
        alignment["reconciliation"] = read_json(rec_path)
    write_json(paths.release / "alignment-report.json", alignment)

    coverage_path = paths.work / "bilingual-coverage.json"
    coverage = (
        read_json(coverage_path)
        if coverage_path.is_file()
        else {"schema_version": 1, "fabricated": 0}
    )
    write_json(paths.release / "bilingual-coverage.json", coverage)

    pending = [item.to_dict() for item in list_candidates(paths, status="pending")]
    rec_risks = (
        alignment.get("reconciliation", {}).get("semantic_risks", [])
        if isinstance(alignment.get("reconciliation"), dict)
        else []
    )
    unresolved = {
        "schema_version": 1,
        "pending_review": pending,
        "reconciliation_risks": rec_risks,
        "source_gaps": [
            item
            for item in alignment.get("reconciliation", {}).get("pairs", [])
            if item.get("operation") == "source-gap"
        ]
        if isinstance(alignment.get("reconciliation"), dict)
        else [],
    }
    write_json(paths.release / "unresolved.json", unresolved)

    copies = {
        "qa-report.json": paths.qa / "summary.json",
        "layout-report.json": paths.qa / "layout.json",
        "render-summary.json": paths.qa / "render-summary.json",
    }
    for name, source in copies.items():
        if source.is_file():
            write_json(paths.release / name, read_json(source))

    files = [
        "change-audit.json",
        "change-audit.csv",
        "CHANGELOG_EVIDENCE.md",
        "source-provenance.json",
        "alignment-report.json",
        "bilingual-coverage.json",
        "unresolved.json",
        *[name for name, source in copies.items() if source.is_file()],
    ]
    return {
        "schema_version": 1,
        "files": files,
        "change_count": len(rows),
        "summary": audit["summary"],
    }

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .errors import GateError, ValidationError
from .io import read_json, write_json
from .models import ChangeRecord, ReviewCandidate
from .state import invalidate_after_review_change, update_stage
from .util import utc_now
from .workfile import load_workfile, save_workfile
from .workspace import TitlePaths


def _candidate_store(paths: TitlePaths) -> dict[str, Any]:
    path = paths.review / "candidates.json"
    if not path.exists():
        return {"schema_version": 1, "candidates": []}
    data = read_json(path)
    if not isinstance(data.get("candidates", []), list):
        raise ValidationError("review/candidates.json must contain a candidates array")
    return data


def _find_unit(paths: TitlePaths, branch: str, unit_id: str):
    work = load_workfile(paths, branch)
    for unit in work.units:
        if unit.id == unit_id:
            return work, unit
    raise ValidationError(f"Unknown {branch} unit: {unit_id}")


def import_proposals(paths: TitlePaths, proposal_path: Path) -> list[ReviewCandidate]:
    raw = read_json(proposal_path)
    if isinstance(raw, dict) and "candidates" in raw:
        items = raw["candidates"]
    elif isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = [raw]
    else:
        raise ValidationError("Proposal file must be an object, array, or {candidates: [...]} object")
    if not isinstance(items, list):
        raise ValidationError("candidates must be a list")

    store = _candidate_store(paths)
    existing_ids = {item.get("candidate_id") for item in store["candidates"]}
    imported: list[ReviewCandidate] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValidationError("Each proposal must be an object")
        branch = str(item.get("branch", ""))
        unit_id = str(item.get("unit_id", ""))
        work, unit = _find_unit(paths, branch, unit_id)
        original = str(item.get("original_text", unit.final_text))
        if original != unit.final_text:
            raise GateError(
                f"Stale proposal for {unit_id}: original_text no longer matches current final_text"
            )
        candidate_id = str(item.get("candidate_id") or f"rev-{uuid.uuid4().hex[:12]}")
        if candidate_id in existing_ids:
            raise ValidationError(f"Duplicate candidate_id: {candidate_id}")
        candidate = ReviewCandidate(
            schema_version=1,
            candidate_id=candidate_id,
            project_id=paths.project_id,
            title_id=paths.title_id,
            branch=branch,  # type: ignore[arg-type]
            unit_id=unit_id,
            change_type=str(item.get("change_type", "semantic")),
            original_text=original,
            proposed_text=str(item.get("proposed_text", "")),
            reason=str(item.get("reason", "")),
            confidence=float(item.get("confidence", 0.5)),
            severity=str(item.get("severity", "medium")),
            evidence={str(k): str(v) for k, v in dict(item.get("evidence", {})).items()},
            requires_human=True,
            status="pending",
            created_at=utc_now(),
        )
        candidate.validate()
        store["candidates"].append(candidate.to_dict())
        existing_ids.add(candidate_id)
        imported.append(candidate)
    write_json(paths.review / "candidates.json", store)
    if imported:
        invalidate_after_review_change(paths, reason="semantic proposals imported")
    update_stage(paths, "human_review", "blocked" if imported else "passed", pending=pending_count(paths))
    return imported


def list_candidates(paths: TitlePaths, *, status: str | None = None) -> list[ReviewCandidate]:
    store = _candidate_store(paths)
    candidates = [ReviewCandidate.from_dict(item) for item in store["candidates"]]
    if status:
        candidates = [candidate for candidate in candidates if candidate.status == status]
    return candidates


def pending_count(paths: TitlePaths) -> int:
    return len(list_candidates(paths, status="pending"))


def decide_candidate(
    paths: TitlePaths,
    candidate_id: str,
    decision: str,
    *,
    note: str | None = None,
    custom_text: str | None = None,
) -> ReviewCandidate:
    decision = decision.lower()
    if decision not in {"approve", "reject", "custom"}:
        raise ValidationError("Decision must be approve, reject, or custom")
    store = _candidate_store(paths)
    index = next(
        (i for i, item in enumerate(store["candidates"]) if item.get("candidate_id") == candidate_id),
        None,
    )
    if index is None:
        raise ValidationError(f"Unknown candidate_id: {candidate_id}")
    candidate = ReviewCandidate.from_dict(store["candidates"][index])
    if candidate.status != "pending":
        raise GateError(f"Candidate {candidate_id} already decided: {candidate.status}")

    if decision in {"approve", "custom"}:
        work, unit = _find_unit(paths, candidate.branch, candidate.unit_id)
        if unit.final_text != candidate.original_text:
            raise GateError(
                f"Candidate {candidate_id} is stale: workfile text changed after proposal creation"
            )
        replacement = candidate.proposed_text if decision == "approve" else (custom_text or "")
        if not replacement.strip():
            raise ValidationError("Custom approved text cannot be empty")
        before = unit.final_text
        unit.final_text = replacement
        unit.changes.append(
            ChangeRecord(
                kind="human-approved-semantic" if decision == "approve" else "human-custom",
                before=before,
                after=replacement,
                rule_id=candidate.candidate_id,
                note=note or candidate.reason,
            )
        )
        save_workfile(paths, work)
        candidate.status = "approved"
        if decision == "custom":
            candidate.proposed_text = replacement
    else:
        candidate.status = "rejected"
    candidate.decision_note = note
    candidate.decided_at = utc_now()
    store["candidates"][index] = candidate.to_dict()
    write_json(paths.review / "candidates.json", store)
    invalidate_after_review_change(paths, reason=f"review candidate {candidate_id} decided")
    remaining = pending_count(paths)
    update_stage(
        paths,
        "human_review",
        "passed" if remaining == 0 else "blocked",
        pending=remaining,
    )
    return candidate


def render_review_markdown(candidates: list[ReviewCandidate]) -> str:
    if not candidates:
        return "No review candidates.\n"
    parts: list[str] = []
    for candidate in candidates:
        evidence = "\n".join(f"- **{key}**: {value}" for key, value in candidate.evidence.items())
        parts.append(
            f"## {candidate.candidate_id} · {candidate.branch}/{candidate.unit_id}\n\n"
            f"- Status: **{candidate.status}**\n"
            f"- Severity: **{candidate.severity}**\n"
            f"- Confidence: **{candidate.confidence:.2f}**\n"
            f"- Type: `{candidate.change_type}`\n\n"
            f"**Original**\n\n> {candidate.original_text.replace(chr(10), chr(10)+'> ')}\n\n"
            f"**Proposed**\n\n> {candidate.proposed_text.replace(chr(10), chr(10)+'> ')}\n\n"
            f"**Reason**\n\n{candidate.reason}\n\n"
            + (f"**Evidence**\n\n{evidence}\n" if evidence else "")
        )
    return "\n\n".join(parts).rstrip() + "\n"

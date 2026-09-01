from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from .errors import GateError, ValidationError
from .io import read_json, write_json
from .models import ChangeRecord, ReviewCandidate
from .state import invalidate_after_review_change, update_stage
from .util import sha256_file, utc_now
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




def unimported_proposal_files(paths: TitlePaths) -> list[Path]:
    root = paths.review_proposals
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.rglob("*.json")
        if path.is_file() and "_imported" not in path.relative_to(root).parts
    )


def _archive_proposal_path(paths: TitlePaths, proposal_path: Path) -> Path | None:
    resolved = proposal_path.resolve()
    root = paths.review_proposals.resolve()
    if not resolved.is_relative_to(root):
        return None
    archive = root / "_imported"
    archive.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().replace(":", "-")
    return archive / f"{stamp}-{uuid.uuid4().hex[:8]}-{resolved.name}"


def _unit_fingerprint(unit: Any) -> str:
    """Fingerprint the evidence/timing context a semantic proposal was made against.

    final_text is intentionally checked separately through original_text. This fingerprint
    protects against the more subtle stale case where timing or source evidence changes
    while the editable text happens to remain byte-for-byte identical.
    """
    payload = {
        "id": unit.id,
        "start_ms": unit.start_ms,
        "end_ms": unit.end_ms,
        "timing_cue_ids": list(unit.timing_cue_ids),
        "source_cue_ids": list(unit.source_cue_ids),
        "raw_text": unit.raw_text,
        "normalized_text": unit.normalized_text,
        "source_text": unit.source_text,
        "source_text_cue_ids": list(unit.source_text_cue_ids),
        "alignment_confidence": unit.alignment_confidence,
        "flags": list(unit.flags),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _semantic_context_fingerprint(paths: TitlePaths, unit: Any) -> str:
    """Bind a proposal to the repository evidence that informed semantic judgment."""
    canon_files = [
        *sorted(paths.project_canon.glob("*.json")),
        *sorted(paths.title_canon.glob("*.json")),
    ]
    research_files = [paths.research / "context.md", paths.research / "sources.md"]
    payload = {
        "unit": _unit_fingerprint(unit),
        "source_manifest_sha256": sha256_file(paths.manifest),
        "canon": {
            str(path.relative_to(paths.repo)).replace("\\", "/"): sha256_file(path)
            for path in canon_files
            if path.is_file()
        },
        "research": {
            str(path.relative_to(paths.title)).replace("\\", "/"): sha256_file(path)
            for path in research_files
            if path.is_file()
        },
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def approved_review_errors(paths: TitlePaths) -> list[dict[str, str]]:
    """Return safety violations for approvals no longer materialized in current workfiles."""
    errors: list[dict[str, str]] = []
    for candidate in list_candidates(paths, status="approved"):
        try:
            _work, unit = _find_unit(paths, candidate.branch, candidate.unit_id)
        except ValidationError:
            errors.append(
                {
                    "kind": "approved-review-unit-missing",
                    "candidate_id": candidate.candidate_id,
                    "branch": candidate.branch,
                    "unit_id": candidate.unit_id,
                }
            )
            continue
        if candidate.unit_fingerprint and _unit_fingerprint(unit) != candidate.unit_fingerprint:
            errors.append(
                {
                    "kind": "approved-review-evidence-stale",
                    "candidate_id": candidate.candidate_id,
                    "branch": candidate.branch,
                    "unit_id": candidate.unit_id,
                }
            )
            continue
        if (
            candidate.context_fingerprint
            and _semantic_context_fingerprint(paths, unit) != candidate.context_fingerprint
        ):
            errors.append(
                {
                    "kind": "approved-review-context-stale",
                    "candidate_id": candidate.candidate_id,
                    "branch": candidate.branch,
                    "unit_id": candidate.unit_id,
                }
            )
            continue
        materialized = any(
            change.rule_id == candidate.candidate_id
            and change.kind in {"human-approved-semantic", "human-custom"}
            and change.after == candidate.proposed_text
            for change in unit.changes
        )
        if not materialized:
            errors.append(
                {
                    "kind": "approved-review-not-materialized",
                    "candidate_id": candidate.candidate_id,
                    "branch": candidate.branch,
                    "unit_id": candidate.unit_id,
                }
            )
    return errors


def import_proposals(paths: TitlePaths, proposal_path: Path) -> list[ReviewCandidate]:
    proposal_path = proposal_path.resolve()
    proposal_sha = sha256_file(proposal_path)
    archive_path = _archive_proposal_path(paths, proposal_path)
    if archive_path is not None:
        proposal_source = str(archive_path.relative_to(paths.title)).replace("\\", "/")
    else:
        proposal_source = proposal_path.name
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
            unit_fingerprint=_unit_fingerprint(unit),
            context_fingerprint=_semantic_context_fingerprint(paths, unit),
            proposal_source=proposal_source,
            proposal_sha256=proposal_sha,
            requires_human=True,
            status="pending",
            created_at=utc_now(),
        )
        candidate.validate()
        store["candidates"].append(candidate.to_dict())
        existing_ids.add(candidate_id)
        imported.append(candidate)
    write_json(paths.review / "candidates.json", store)
    if imported and archive_path is not None:
        shutil.move(str(proposal_path), str(archive_path))
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
        if candidate.unit_fingerprint and _unit_fingerprint(unit) != candidate.unit_fingerprint:
            raise GateError(
                f"Candidate {candidate_id} is stale: timing or source evidence changed after proposal creation"
            )
        if (
            candidate.context_fingerprint
            and _semantic_context_fingerprint(paths, unit) != candidate.context_fingerprint
        ):
            raise GateError(
                f"Candidate {candidate_id} is stale: canon, research, or source manifest changed after proposal creation"
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

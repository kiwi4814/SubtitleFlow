from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..io import read_json
from ..workspace import TitlePaths
from .resolver import build_effective


def _semantic_record(item: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(item)
    for key in ("pack_refs", "record_id", "scope_rank", "evidence_ids"):
        value.pop(key, None)
    return value


def _record_id(kind: str, item: dict[str, Any]) -> str:
    if kind in {"terms", "decisions"}:
        return str(item.get("key", ""))
    return str(item.get("id", ""))


def _branch_changes(
    branch: str,
    kind: str,
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    old = {_record_id(kind, item): _semantic_record(item) for item in before}
    new = {_record_id(kind, item): _semantic_record(item) for item in after}
    changes: list[dict[str, Any]] = []
    for record_id in sorted(set(old) | set(new)):
        if old.get(record_id) == new.get(record_id):
            continue
        changes.append(
            {
                "branch": branch,
                "kind": kind[:-1] if kind.endswith("s") else kind,
                "key" if kind in {"terms", "decisions"} else "id": record_id,
                "before": old.get(record_id),
                "after": new.get(record_id),
            }
        )
    return changes


def diff_research(paths: TitlePaths) -> dict[str, Any]:
    current = read_json(paths.research_effective) if paths.research_effective.exists() else None
    old_snapshot = read_json(paths.research_snapshot) if paths.research_snapshot.exists() else None
    prospective, snapshot = build_effective(paths)
    changes: list[dict[str, Any]] = []
    current_branches = current.get("branches", {}) if isinstance(current, dict) else {}

    all_branches = sorted(set(current_branches) | set(prospective.get("branches", {})))
    for branch in all_branches:
        before = current_branches.get(branch, {})
        after = prospective.get("branches", {}).get(branch, {})
        if before.get("srp_branch_id") != after.get("srp_branch_id"):
            changes.append(
                {
                    "branch": branch,
                    "kind": "branch_mapping",
                    "before": before.get("srp_branch_id"),
                    "after": after.get("srp_branch_id"),
                }
            )
        for kind in ("terms", "decisions", "entities", "facts", "unresolved"):
            changes.extend(
                _branch_changes(
                    branch,
                    kind,
                    list(before.get(kind, [])),
                    list(after.get(kind, [])),
                )
            )

    return {
        "changes": changes,
        "semantic_changed": (
            old_snapshot is None
            or old_snapshot.get("effective_semantic_sha256")
            != snapshot.get("effective_semantic_sha256")
        ),
        "provenance_changed": (
            old_snapshot is None
            or old_snapshot.get("provenance_sha256") != snapshot.get("provenance_sha256")
        ),
        "prospective_snapshot": snapshot,
        "blocking_conflicts": prospective.get("blocking_conflicts", 0),
        "blocking_unresolved": prospective.get("blocking_unresolved", 0),
    }

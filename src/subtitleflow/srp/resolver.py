from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from ..errors import GateError, ValidationError
from ..io import read_json, write_json
from ..state import invalidate_stages, update_stage
from ..util import sha256_file, utc_now
from ..workflow import active_branches
from ..workspace import TitlePaths, effective_series_id
from . import RESOLVER_VERSION
from .archive import compute_pack_digest
from .context import render_context
from .registry import (
    bindings_digest,
    bound_registry_entries,
    branch_map,
    load_bindings,
    research_mode,
)
from .validate import validate_pack_dir

_SCOPE_RANK = {"series": 10, "title": 20, "series_branch": 30, "branch": 40}
_ENFORCEMENT_RANK = {"informational": 0, "preferred": 1, "locked": 2}
_INTERNAL_BRANCHES = ("clean", "tw", "jp")


def _canonical_sha(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _target_language(paths: TitlePaths) -> str:
    project = read_json(paths.project_config)
    return str(project.get("defaults", {}).get("target_locale", "zh-CN"))


def _scope_rank(
    scope: dict[str, Any],
    *,
    series_id: str,
    title_id: str,
    branch_id: str | None,
) -> int | None:
    if scope.get("series_id") != series_id:
        return None
    level = scope.get("level")
    if level == "series":
        return _SCOPE_RANK[level]
    if level == "title":
        return _SCOPE_RANK[level] if scope.get("title_id") == title_id else None
    if level == "series_branch":
        return (
            _SCOPE_RANK[level]
            if branch_id is not None and scope.get("branch_id") == branch_id
            else None
        )
    if level == "branch":
        return (
            _SCOPE_RANK[level]
            if branch_id is not None
            and scope.get("title_id") == title_id
            and scope.get("branch_id") == branch_id
            else None
        )
    return None


def _local_scope(
    *,
    origin: str,
    branches: list[str],
    current_branch: str,
    series_id: str,
    title_id: str,
) -> tuple[int, dict[str, str]] | None:
    if current_branch not in branches:
        return None
    branch_specific = set(branches) != set(_INTERNAL_BRANCHES)
    if origin == "local-project":
        if branch_specific:
            return _SCOPE_RANK["series_branch"], {
                "level": "series_branch",
                "series_id": series_id,
                "branch_id": current_branch,
            }
        return _SCOPE_RANK["series"], {"level": "series", "series_id": series_id}
    if branch_specific:
        return _SCOPE_RANK["branch"], {
            "level": "branch",
            "series_id": series_id,
            "title_id": title_id,
            "branch_id": current_branch,
        }
    return _SCOPE_RANK["title"], {
        "level": "title",
        "series_id": series_id,
        "title_id": title_id,
    }


def _load_local_terms(paths: TitlePaths, branch: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for origin, file_path in (
        ("local-project", paths.project_canon / "glossary.json"),
        ("local-title", paths.title_canon / "glossary.json"),
    ):
        if not file_path.exists():
            continue
        data = read_json(file_path)
        for record in data.get("terms", []):
            term_id = str(record.get("id", "")).strip()
            canonical = str(record.get("canonical", "")).strip()
            if not term_id or not canonical:
                continue
            branches = [str(item) for item in record.get("branches", list(_INTERNAL_BRANCHES))]
            scoped = _local_scope(
                origin=origin,
                branches=branches,
                current_branch=branch,
                series_id=effective_series_id(paths),
                title_id=paths.title_id,
            )
            if scoped is None:
                continue
            rank, scope = scoped
            aliases = [str(item) for item in record.get("aliases", []) if str(item)]
            forbidden = [
                str(item)
                for item in record.get("forbidden_aliases", aliases)
                if str(item)
            ]
            accepted = [
                str(item) for item in record.get("accepted_aliases", []) if str(item)
            ]
            deprecated = [
                str(item) for item in record.get("deprecated_aliases", []) if str(item)
            ]
            result.append(
                {
                    "key": str(record.get("key") or term_id),
                    "canonical": canonical,
                    "source_forms": [],
                    "target_language": _target_language(paths),
                    "accepted_aliases": accepted,
                    "deprecated_aliases": deprecated,
                    "forbidden_aliases": forbidden,
                    "known_aliases": aliases,
                    "enforcement": str(record.get("enforcement", "locked")),
                    "origin": origin,
                    "scope": scope,
                    "scope_rank": rank,
                    "record_id": term_id,
                    "pack_refs": [],
                    "notes": record.get("notes"),
                    "auto_replace": bool(record.get("auto_replace", False)),
                    "context_sensitive": bool(record.get("context_sensitive", False)),
                }
            )
    return result


def _pack_ref(entry: dict[str, Any]) -> dict[str, str]:
    return {
        "pack_id": str(entry["pack_id"]),
        "pack_version": str(entry["pack_version"]),
        "pack_digest": str(entry["pack_digest"]),
    }


def _load_bound_packs(paths: TitlePaths) -> list[dict[str, Any]]:
    packs: list[dict[str, Any]] = []
    for entry in bound_registry_entries(paths):
        pack_root = paths.project / str(entry["path"])
        expected_digest = str(entry["pack_digest"])
        current_digest = compute_pack_digest(pack_root)
        if current_digest != expected_digest:
            raise ValidationError(
                f"Imported SRP snapshot was modified: {entry['pack_id']}@{entry['pack_version']}"
            )
        validated = validate_pack_dir(pack_root)
        packs.append(
            {
                "entry": entry,
                "manifest": validated.manifest,
                "records": validated.records,
            }
        )
    return packs


def _applicable_records(
    packs: list[dict[str, Any]],
    filename: str,
    *,
    paths: TitlePaths,
    branch_id: str | None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for pack in packs:
        ref = _pack_ref(pack["entry"])
        for record in pack["records"].get(filename, []):
            scope = record.get("scope")
            if not isinstance(scope, dict):
                continue
            rank = _scope_rank(
                scope,
                series_id=effective_series_id(paths),
                title_id=paths.title_id,
                branch_id=branch_id,
            )
            if rank is None:
                continue
            item = deepcopy(record)
            item["_scope_rank"] = rank
            item["_pack_ref"] = ref
            result.append(item)
    return result


def _merge_equal_srp_terms(
    items: list[dict[str, Any]],
    *,
    branch: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    first = items[0]
    target = first.get("target", {})
    canonical = str(target["value"])
    source_forms: set[str] = set()
    accepted: set[str] = set()
    deprecated: set[str] = set()
    forbidden: set[str] = set()
    rationales: list[str] = []

    for item in items:
        source_forms.update(str(value) for value in item.get("source", {}).get("forms", []))
        item_target = item.get("target", {})
        accepted.update(str(value) for value in item_target.get("accepted_aliases", []))
        deprecated.update(str(value) for value in item_target.get("deprecated", []))
        forbidden.update(str(value) for value in item_target.get("forbidden", []))
        rationale = item.get("rationale")
        if isinstance(rationale, str) and rationale and rationale not in rationales:
            rationales.append(rationale)

    category_overlaps = {
        "accepted/deprecated": sorted(accepted & deprecated),
        "accepted/forbidden": sorted(accepted & forbidden),
        "deprecated/forbidden": sorted(deprecated & forbidden),
    }
    category_overlaps = {key: value for key, value in category_overlaps.items() if value}
    canonical_conflicts = {
        name: canonical in values
        for name, values in {
            "accepted": accepted,
            "deprecated": deprecated,
            "forbidden": forbidden,
        }.items()
        if canonical in values
    }
    if category_overlaps or canonical_conflicts:
        return None, {
            "kind": "srp-term-policy-conflict",
            "key": first["key"],
            "branch": branch,
            "message": "Bound SRP packs agree on the canonical value but disagree on alias policy",
            "canonical": canonical,
            "alias_overlaps": category_overlaps,
            "canonical_category_conflicts": sorted(canonical_conflicts),
            "blocking": True,
            "pack_refs": [item["_pack_ref"] for item in items],
        }

    enforcement = max(
        (str(item.get("enforcement", "informational")) for item in items),
        key=lambda value: _ENFORCEMENT_RANK.get(value, 0),
    )
    return {
        "key": first["key"],
        "canonical": canonical,
        "source_forms": sorted(source_forms),
        "target_language": target["language"],
        "accepted_aliases": sorted(accepted),
        "deprecated_aliases": sorted(deprecated),
        "forbidden_aliases": sorted(forbidden),
        "known_aliases": sorted(deprecated | forbidden),
        "enforcement": enforcement,
        "origin": "srp",
        "scope": deepcopy(first["scope"]),
        "scope_rank": int(first["_scope_rank"]),
        "record_id": first["id"],
        "pack_refs": [item["_pack_ref"] for item in items],
        "notes": " | ".join(rationales) if rationales else None,
        "auto_replace": False,
        "context_sensitive": True,
    }, None


def _resolve_terms(
    paths: TitlePaths,
    packs: list[dict[str, Any]],
    *,
    branch: str,
    branch_id: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    target_language = _target_language(paths)
    candidates: list[dict[str, Any]] = []
    for item in _applicable_records(
        packs, "terms.jsonl", paths=paths, branch_id=branch_id
    ):
        if item.get("status") != "accepted":
            continue
        if item.get("target", {}).get("language") != target_language:
            continue
        candidates.append(item)
    local = _load_local_terms(paths, branch)
    keys = {str(item.get("key")) for item in candidates} | {item["key"] for item in local}
    resolved: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    for key in sorted(keys):
        srp_for_key = [item for item in candidates if item.get("key") == key]
        local_for_key = [item for item in local if item["key"] == key]
        max_rank = max(
            [int(item["_scope_rank"]) for item in srp_for_key]
            + [int(item["scope_rank"]) for item in local_for_key],
            default=-1,
        )
        srp_top = [item for item in srp_for_key if int(item["_scope_rank"]) == max_rank]
        local_top = [item for item in local_for_key if int(item["scope_rank"]) == max_rank]

        if local_top:
            values = {item["canonical"] for item in local_top}
            if len(values) > 1:
                conflicts.append(
                    {
                        "kind": "local-term-conflict",
                        "key": key,
                        "branch": branch,
                        "message": "Multiple local canon values exist at the same effective scope",
                        "values": sorted(values),
                        "blocking": True,
                    }
                )
                continue
            winner = deepcopy(local_top[0])
            if srp_top:
                srp_values = {str(item.get("target", {}).get("value")) for item in srp_top}
                if srp_values != values:
                    conflicts.append(
                        {
                            "kind": "srp-term-conflict",
                            "key": key,
                            "branch": branch,
                            "message": "SRP conflict is explicitly resolved by same-scope local canon",
                            "values": sorted(srp_values | values),
                            "blocking": False,
                            "resolved_by_local": True,
                        }
                    )
            resolved.append(winner)
            continue

        if not srp_top:
            continue
        values = {str(item.get("target", {}).get("value")) for item in srp_top}
        if len(values) > 1:
            conflicts.append(
                {
                    "kind": "srp-term-conflict",
                    "key": key,
                    "branch": branch,
                    "message": "Bound SRP packs disagree at the same effective scope",
                    "values": sorted(values),
                    "blocking": True,
                    "pack_refs": [item["_pack_ref"] for item in srp_top],
                }
            )
            continue
        merged, policy_conflict = _merge_equal_srp_terms(srp_top, branch=branch)
        if policy_conflict is not None:
            conflicts.append(policy_conflict)
            continue
        if merged is not None:
            resolved.append(merged)

    return sorted(resolved, key=lambda item: item["key"]), conflicts


def _resolve_decisions(
    paths: TitlePaths,
    packs: list[dict[str, Any]],
    *,
    branch: str,
    branch_id: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = [
        item
        for item in _applicable_records(
            packs, "decisions.jsonl", paths=paths, branch_id=branch_id
        )
        if item.get("status") == "accepted"
    ]
    candidates = [
        item
        for item in candidates
        if not item.get("applies_to", {}).get("branch_ids")
        or (
            branch_id is not None
            and branch_id in item.get("applies_to", {}).get("branch_ids", [])
        )
    ]
    keys = {str(item.get("key")) for item in candidates}
    resolved: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for key in sorted(keys):
        for_key = [item for item in candidates if item.get("key") == key]
        max_rank = max(int(item["_scope_rank"]) for item in for_key)
        top = [item for item in for_key if int(item["_scope_rank"]) == max_rank]
        directives = {str(item.get("directive")) for item in top}
        if len(directives) > 1:
            conflicts.append(
                {
                    "kind": "srp-decision-conflict",
                    "key": key,
                    "branch": branch,
                    "message": "Bound SRP packs disagree on an effective decision",
                    "directives": sorted(directives),
                    "blocking": True,
                    "pack_refs": [item["_pack_ref"] for item in top],
                }
            )
            continue
        first = top[0]
        resolved.append(
            {
                "key": key,
                "directive": first["directive"],
                "kind": first.get("kind"),
                "enforcement": max(
                    (str(item.get("enforcement", "informational")) for item in top),
                    key=lambda value: _ENFORCEMENT_RANK.get(value, 0),
                ),
                "scope": deepcopy(first["scope"]),
                "record_id": first["id"],
                "pack_refs": [item["_pack_ref"] for item in top],
                "rationale": first.get("rationale"),
            }
        )
    return resolved, conflicts


def _dedupe_context_records(
    records: list[dict[str, Any]],
    *,
    branch: str,
    kind: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id: dict[str, list[dict[str, Any]]] = {}
    for item in records:
        by_id.setdefault(str(item.get("id")), []).append(item)
    result: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for record_id, items in sorted(by_id.items()):
        normalized = []
        for item in items:
            copy = deepcopy(item)
            copy.pop("_pack_ref", None)
            copy.pop("_scope_rank", None)
            normalized.append(copy)
        fingerprints = {_canonical_sha(item) for item in normalized}
        if len(fingerprints) > 1:
            conflicts.append(
                {
                    "kind": f"srp-{kind}-id-conflict",
                    "id": record_id,
                    "branch": branch,
                    "message": "Bound SRP packs reuse an id with different content",
                    "blocking": True,
                }
            )
            continue
        record = normalized[0]
        record["pack_refs"] = [item["_pack_ref"] for item in items]
        result.append(record)
    return result, conflicts


def _semantic_copy(effective: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "resolver_version": effective["resolver_version"],
        "mode": effective["mode"],
        "series_id": effective.get("series_id"),
        "branch_map": effective["branch_map"],
        "branches": {},
        "blocking_conflicts": effective["blocking_conflicts"],
        "blocking_unresolved": effective["blocking_unresolved"],
    }
    for branch, data in effective.get("branches", {}).items():
        branch_payload: dict[str, Any] = {"srp_branch_id": data.get("srp_branch_id")}
        for name in ("terms", "decisions", "entities", "facts", "unresolved"):
            values = []
            for item in data.get(name, []):
                cleaned = deepcopy(item)
                cleaned.pop("pack_refs", None)
                cleaned.pop("record_id", None)
                cleaned.pop("evidence_ids", None)
                values.append(cleaned)
            branch_payload[name] = values
        payload["branches"][branch] = branch_payload
    return payload


def _provenance_payload(packs: list[dict[str, Any]], bindings: list[dict[str, Any]]) -> dict[str, Any]:
    data: dict[str, Any] = {"bindings": bindings, "packs": []}
    for pack in packs:
        data["packs"].append(
            {
                "manifest": pack["manifest"],
                "pack_ref": _pack_ref(pack["entry"]),
                "sources": pack["records"].get("sources.jsonl", []),
                "evidence": pack["records"].get("evidence.jsonl", []),
            }
        )
    return data


def research_input_digest(paths: TitlePaths) -> str:
    mode = research_mode(paths)
    config = read_json(paths.title_config)
    research = config.get("research") if isinstance(config.get("research"), dict) else None
    payload: dict[str, Any] = {
        "mode": mode,
        "series_id": effective_series_id(paths),
        "research": research,
        "bindings": load_bindings(paths).get("bindings", []),
        "canon": {},
        "packs": [],
    }
    for path in sorted(paths.project_canon.glob("*.json")) + sorted(paths.title_canon.glob("*.json")):
        if path.is_file():
            payload["canon"][str(path.relative_to(paths.project))] = sha256_file(path)
    if mode not in {"off", "legacy"}:
        for entry in bound_registry_entries(paths):
            root = paths.project / str(entry["path"])
            payload["packs"].append(
                {
                    "pack_digest_expected": entry["pack_digest"],
                    "pack_digest_current": compute_pack_digest(root),
                }
            )
    return _canonical_sha(payload)


def build_effective(paths: TitlePaths) -> tuple[dict[str, Any], dict[str, Any]]:
    mode = research_mode(paths)
    if mode == "legacy":
        raise ValidationError("Legacy v0.3 research does not use SRP resolution")
    mapping = branch_map(paths)
    series_id = effective_series_id(paths)
    bindings = load_bindings(paths).get("bindings", [])
    packs = [] if mode == "off" else _load_bound_packs(paths)
    conflicts: list[dict[str, Any]] = []
    branches: dict[str, Any] = {}
    blocking_unresolved = 0

    for branch in active_branches(paths):
        srp_branch_id = mapping.get(branch)
        terms, term_conflicts = _resolve_terms(
            paths, packs, branch=branch, branch_id=srp_branch_id
        )
        decisions, decision_conflicts = _resolve_decisions(
            paths, packs, branch=branch, branch_id=srp_branch_id
        )
        entities, entity_conflicts = _dedupe_context_records(
            _applicable_records(packs, "entities.jsonl", paths=paths, branch_id=srp_branch_id),
            branch=branch,
            kind="entity",
        )
        fact_candidates = [
            item
            for item in _applicable_records(
                packs, "facts.jsonl", paths=paths, branch_id=srp_branch_id
            )
            if item.get("status") != "deprecated"
        ]
        facts, fact_conflicts = _dedupe_context_records(
            fact_candidates,
            branch=branch,
            kind="fact",
        )
        unresolved, unresolved_conflicts = _dedupe_context_records(
            _applicable_records(packs, "unresolved.jsonl", paths=paths, branch_id=srp_branch_id),
            branch=branch,
            kind="unresolved",
        )
        unresolved = [item for item in unresolved if item.get("severity")]
        blocking_unresolved += sum(item.get("severity") == "blocking" for item in unresolved)
        conflicts.extend(
            term_conflicts
            + decision_conflicts
            + entity_conflicts
            + fact_conflicts
            + unresolved_conflicts
        )
        branches[branch] = {
            "srp_branch_id": srp_branch_id,
            "terms": terms,
            "decisions": decisions,
            "entities": entities,
            "facts": facts,
            "unresolved": unresolved,
        }

    unique_conflicts = {
        _canonical_sha(
            {
                key: value
                for key, value in item.items()
                if key not in {"branch", "pack_refs"}
            }
        )
        for item in conflicts
        if item.get("blocking")
    }
    unique_unresolved = {
        str(item.get("id"))
        for data in branches.values()
        for item in data.get("unresolved", [])
        if item.get("severity") == "blocking"
    }
    blocking_conflicts = len(unique_conflicts)
    blocking_unresolved = len(unique_unresolved)
    effective = {
        "schema_version": 1,
        "resolver_version": RESOLVER_VERSION,
        "project_id": paths.project_id,
        "title_id": paths.title_id,
        "series_id": series_id,
        "mode": mode,
        "branch_map": mapping,
        "bindings": bindings,
        "branches": branches,
        "conflicts": conflicts,
        "blocking_conflicts": blocking_conflicts,
        "blocking_unresolved": blocking_unresolved,
        "generated_at": utc_now(),
    }
    semantic_sha = _canonical_sha(_semantic_copy(effective))
    provenance_sha = _canonical_sha(_provenance_payload(packs, bindings))
    snapshot = {
        "schema_version": 1,
        "resolver_version": RESOLVER_VERSION,
        "project_id": paths.project_id,
        "title_id": paths.title_id,
        "series_id": series_id,
        "mode": mode,
        "bindings_sha256": bindings_digest(paths),
        "pack_digests": sorted(
            str(item["pack_digest"]) for item in bound_registry_entries(paths)
        )
        if mode != "off"
        else [],
        "effective_semantic_sha256": semantic_sha,
        "provenance_sha256": provenance_sha,
        "input_sha256": research_input_digest(paths),
        "blocking_unresolved": blocking_unresolved,
        "blocking_conflicts": blocking_conflicts,
        "resolved_at": utc_now(),
    }
    return effective, snapshot


def resolve_research(paths: TitlePaths) -> dict[str, Any]:
    old_snapshot = read_json(paths.research_snapshot) if paths.research_snapshot.exists() else None
    effective, snapshot = build_effective(paths)
    write_json(paths.research_effective, effective)
    write_json(paths.research_snapshot, snapshot)
    render_context(paths, effective)

    semantic_changed = (
        old_snapshot is not None
        and old_snapshot.get("effective_semantic_sha256")
        != snapshot["effective_semantic_sha256"]
    )
    provenance_changed = (
        old_snapshot is not None
        and old_snapshot.get("provenance_sha256") != snapshot["provenance_sha256"]
    )
    if semantic_changed:
        invalidate_stages(
            paths,
            ("research", "qa", "semantic_qa", "release", "remux"),
            reason="effective research semantics changed",
        )
    elif provenance_changed:
        invalidate_stages(
            paths,
            ("research", "release", "remux"),
            reason="research provenance changed",
        )
    update_stage(
        paths,
        "research_resolve",
        "passed",
        evidence={
            "effective_semantic_sha256": snapshot["effective_semantic_sha256"],
            "provenance_sha256": snapshot["provenance_sha256"],
            "input_sha256": snapshot["input_sha256"],
        },
    )
    return snapshot


def validate_resolved_snapshot(paths: TitlePaths) -> dict[str, Any]:
    if not paths.research_snapshot.is_file() or not paths.research_effective.is_file():
        raise GateError("research is not resolved; run subflow research resolve")
    snapshot = read_json(paths.research_snapshot)
    state = read_json(paths.state)
    current_series_id = effective_series_id(paths)
    if snapshot.get("series_id", current_series_id) != current_series_id:
        raise GateError("research resolution is stale; title series identity changed")
    effective = read_json(paths.research_effective)
    if effective.get("series_id", current_series_id) != current_series_id:
        raise GateError("research resolution is stale; title series identity changed")
    if state.get("stages", {}).get("research_resolve", {}).get("status") != "passed":
        raise GateError("research resolve stage is not passed")
    current_input = research_input_digest(paths)
    if snapshot.get("input_sha256") != current_input:
        raise GateError("research resolution is stale; inputs changed after resolve")
    return snapshot


def approve_research(paths: TitlePaths, *, note: str | None = None) -> dict[str, Any]:
    mode = research_mode(paths)
    if mode == "legacy":
        raise GateError("legacy research approval must use the v0.3 evidence files")
    if mode == "off":
        raise GateError("research.mode=off has no Research Gate to approve")
    snapshot = validate_resolved_snapshot(paths)
    if mode == "enforce" and not snapshot.get("pack_digests"):
        raise GateError("enforce mode requires at least one bound SRP pack")
    if mode == "enforce" and snapshot.get("blocking_conflicts", 0):
        raise GateError("Research Gate blocked by unresolved SRP conflicts")
    if mode == "enforce" and snapshot.get("blocking_unresolved", 0):
        raise GateError("Research Gate blocked by unresolved items with severity=blocking")
    evidence = {
        key: snapshot[key]
        for key in (
            "resolver_version",
            "mode",
            "bindings_sha256",
            "pack_digests",
            "effective_semantic_sha256",
            "provenance_sha256",
            "input_sha256",
            "blocking_unresolved",
            "blocking_conflicts",
        )
    }
    invalidate_stages(paths, ("release", "remux"), reason="research approval refreshed")
    update_stage(paths, "research", "passed", note=note, evidence=evidence)
    return evidence


def validate_native_research_evidence(paths: TitlePaths) -> dict[str, Any]:
    mode = research_mode(paths)
    if mode == "off":
        return {"mode": "off"}
    if mode == "legacy":
        raise GateError("legacy research must use legacy evidence validation")
    snapshot = validate_resolved_snapshot(paths)
    state = read_json(paths.state)
    stage = state.get("stages", {}).get("research", {})
    if stage.get("status") != "passed":
        raise GateError("research gate is not passed")
    current = {
        key: snapshot[key]
        for key in (
            "resolver_version",
            "mode",
            "bindings_sha256",
            "pack_digests",
            "effective_semantic_sha256",
            "provenance_sha256",
            "input_sha256",
            "blocking_unresolved",
            "blocking_conflicts",
        )
    }
    if stage.get("evidence") != current:
        raise GateError("research gate is stale: resolved SRP evidence changed after approval")
    return current


def effective_semantic_digest(paths: TitlePaths) -> str | None:
    mode = research_mode(paths)
    if mode in {"off", "legacy"}:
        return None
    snapshot = validate_resolved_snapshot(paths)
    return str(snapshot["effective_semantic_sha256"])


def ensure_resolved(paths: TitlePaths) -> dict[str, Any] | None:
    mode = research_mode(paths)
    if mode in {"off", "legacy"}:
        return None
    try:
        return validate_resolved_snapshot(paths)
    except GateError:
        return resolve_research(paths)


def require_research_ready_for_edit(paths: TitlePaths) -> None:
    mode = research_mode(paths)
    if mode != "enforce":
        if mode == "advisory":
            ensure_resolved(paths)
        return
    ensure_resolved(paths)
    validate_native_research_evidence(paths)

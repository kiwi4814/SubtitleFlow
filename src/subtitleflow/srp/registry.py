from __future__ import annotations

import hashlib
import json
from typing import Any

from ..errors import ValidationError
from ..io import read_json, write_json
from ..state import invalidate_after_research_semantic_change, invalidate_stages
from ..workspace import TitlePaths, effective_series_id

VALID_RESEARCH_MODES = {"off", "advisory", "enforce"}
VALID_INTERNAL_BRANCHES = {"clean", "tw", "jp"}


def research_config(paths: TitlePaths) -> dict[str, Any] | None:
    config = read_json(paths.title_config)
    value = config.get("research")
    return dict(value) if isinstance(value, dict) else None


def research_mode(paths: TitlePaths) -> str:
    config = research_config(paths)
    if config is None:
        return "legacy"
    mode = str(config.get("mode", "off"))
    if mode not in VALID_RESEARCH_MODES:
        raise ValidationError(f"Invalid research.mode {mode!r}")
    return mode


def branch_map(paths: TitlePaths) -> dict[str, str]:
    config = research_config(paths) or {}
    raw = config.get("branch_map", {})
    if not isinstance(raw, dict):
        raise ValidationError("research.branch_map must be an object")
    result: dict[str, str] = {}
    for key, value in raw.items():
        if key not in VALID_INTERNAL_BRANCHES:
            raise ValidationError(f"Invalid SubtitleFlow branch in research.branch_map: {key}")
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"Invalid SRP branch id for {key}")
        result[key] = value.strip()
    return result


def set_mode(paths: TitlePaths, mode: str) -> dict[str, Any]:
    mode = mode.strip().lower()
    if mode not in VALID_RESEARCH_MODES:
        raise ValidationError(
            f"research mode must be one of {', '.join(sorted(VALID_RESEARCH_MODES))}"
        )
    previous_mode = research_mode(paths)
    config = read_json(paths.title_config)
    research = config.setdefault("research", {})
    research["mode"] = mode
    research.setdefault("branch_map", {})
    write_json(paths.title_config, config)
    if previous_mode != mode:
        reason = f"research mode changed: {previous_mode} -> {mode}"
        invalidate_stages(paths, ("research_resolve",), reason=reason)
        invalidate_after_research_semantic_change(paths, reason=reason)
    return dict(research)


def map_branch(paths: TitlePaths, branch: str, srp_branch_id: str | None) -> dict[str, str]:
    if branch not in VALID_INTERNAL_BRANCHES:
        raise ValidationError("branch must be clean, tw, or jp")
    config = read_json(paths.title_config)
    research = config.setdefault("research", {"mode": "off", "branch_map": {}})
    mapping = research.setdefault("branch_map", {})
    if not isinstance(mapping, dict):
        raise ValidationError("research.branch_map must be an object")
    previous = mapping.get(branch)
    if srp_branch_id is None:
        if branch not in mapping:
            return dict(mapping)
        mapping.pop(branch)
    else:
        value = srp_branch_id.strip()
        if not value:
            raise ValidationError("SRP branch id cannot be empty")
        if previous == value:
            return dict(mapping)
        mapping[branch] = value
    write_json(paths.title_config, config)
    reason = f"research branch mapping changed for {branch}"
    invalidate_stages(paths, ("research_resolve",), reason=reason)
    invalidate_after_research_semantic_change(paths, reason=reason)
    return dict(mapping)


def load_registry(paths: TitlePaths) -> dict[str, Any]:
    if not paths.project_research_registry.exists():
        return {"schema_version": 1, "packs": []}
    data = read_json(paths.project_research_registry)
    if not isinstance(data.get("packs", []), list):
        raise ValidationError("research registry packs must be an array")
    return data


def list_packs(paths: TitlePaths) -> list[dict[str, Any]]:
    return list(load_registry(paths).get("packs", []))


def _parse_pack_ref(pack_ref: str) -> tuple[str, str, str | None]:
    base, marker, digest = pack_ref.partition("#")
    if "@" not in base:
        raise ValidationError("PACK_REF must be pack_id@pack_version")
    pack_id, version = base.rsplit("@", 1)
    if not pack_id or not version:
        raise ValidationError("PACK_REF must be pack_id@pack_version")
    expected = digest if marker else None
    if expected and not expected.startswith("sha256:"):
        expected = "sha256:" + expected
    return pack_id, version, expected


def resolve_pack_ref(paths: TitlePaths, pack_ref: str) -> dict[str, Any]:
    pack_id, version, digest = _parse_pack_ref(pack_ref)
    candidates = [
        item
        for item in list_packs(paths)
        if item.get("pack_id") == pack_id and item.get("pack_version") == version
    ]
    if digest:
        candidates = [item for item in candidates if item.get("pack_digest") == digest]
    if not candidates:
        raise ValidationError(f"No imported SRP matches {pack_ref}")
    if len(candidates) > 1:
        choices = ", ".join(str(item.get("pack_digest")) for item in candidates)
        raise ValidationError(
            f"PACK_REF {pack_ref} is ambiguous; append #sha256:<digest>. Candidates: {choices}"
        )
    return dict(candidates[0])


def load_bindings(paths: TitlePaths) -> dict[str, Any]:
    if not paths.research_bindings.exists():
        return {"schema_version": 1, "bindings": []}
    data = read_json(paths.research_bindings)
    if not isinstance(data.get("bindings", []), list):
        raise ValidationError("research bindings must be an array")
    return data


def bindings_digest(paths: TitlePaths) -> str:
    data = load_bindings(paths)
    enabled = [item for item in data.get("bindings", []) if item.get("enabled", True)]
    payload = json.dumps(enabled, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def bind_pack(paths: TitlePaths, pack_ref: str) -> dict[str, Any]:
    entry = resolve_pack_ref(paths, pack_ref)
    scope = entry.get("scope")
    pack_series_id = scope.get("series_id") if isinstance(scope, dict) else None
    if not isinstance(pack_series_id, str) or not pack_series_id.strip():
        raise ValidationError("Imported SRP registry entry is missing scope.series_id")
    title_series_id = effective_series_id(paths)
    if pack_series_id != title_series_id:
        raise ValidationError(
            "SRP series_id is incompatible with the title: "
            f"title {paths.project_id}/{paths.title_id} uses {title_series_id}, "
            f"but {entry['pack_id']}@{entry['pack_version']} uses {pack_series_id}"
        )
    bindings = load_bindings(paths)
    items = bindings.setdefault("bindings", [])
    existing = next(
        (item for item in items if item.get("pack_digest") == entry["pack_digest"]),
        None,
    )
    if existing is not None:
        existing_series_id = existing.get("series_id")
        if existing_series_id is not None and existing_series_id != pack_series_id:
            raise ValidationError(
                "Existing SRP binding series_id does not match the imported pack: "
                f"{existing_series_id} != {pack_series_id}"
            )
        return dict(existing)

    binding = {
        "pack_id": entry["pack_id"],
        "pack_version": entry["pack_version"],
        "pack_digest": entry["pack_digest"],
        "series_id": pack_series_id,
        "enabled": True,
    }
    items.append(binding)
    write_json(paths.research_bindings, bindings)
    invalidate_stages(
        paths,
        ("research_resolve", "research", "release", "remux"),
        reason="SRP binding changed; resolve to determine semantic impact",
    )
    return binding


def unbind_pack(paths: TitlePaths, pack_ref: str) -> dict[str, Any]:
    entry = resolve_pack_ref(paths, pack_ref)
    bindings = load_bindings(paths)
    before = list(bindings.get("bindings", []))
    after = [item for item in before if item.get("pack_digest") != entry["pack_digest"]]
    if len(after) == len(before):
        raise ValidationError(f"SRP is not bound to this title: {pack_ref}")
    bindings["bindings"] = after
    write_json(paths.research_bindings, bindings)
    invalidate_stages(
        paths,
        ("research_resolve", "research", "release", "remux"),
        reason="SRP binding changed; resolve to determine semantic impact",
    )
    return {"removed": entry["pack_digest"], "bindings": after}


def bound_registry_entries(paths: TitlePaths) -> list[dict[str, Any]]:
    registry_by_digest = {str(item.get("pack_digest")): item for item in list_packs(paths)}
    title_series_id = effective_series_id(paths)
    result: list[dict[str, Any]] = []
    for binding in load_bindings(paths).get("bindings", []):
        if not binding.get("enabled", True):
            continue
        digest = str(binding.get("pack_digest", ""))
        entry = registry_by_digest.get(digest)
        if entry is None:
            raise ValidationError(f"Bound SRP digest is missing from registry: {digest}")
        if (
            binding.get("pack_id") != entry.get("pack_id")
            or binding.get("pack_version") != entry.get("pack_version")
        ):
            raise ValidationError(f"Bound SRP identity does not match registry: {digest}")
        scope = entry.get("scope")
        pack_series_id = scope.get("series_id") if isinstance(scope, dict) else None
        if not isinstance(pack_series_id, str) or not pack_series_id.strip():
            raise ValidationError(f"Imported SRP registry entry is missing scope.series_id: {digest}")
        binding_series_id = binding.get("series_id")
        if binding_series_id is not None and binding_series_id != pack_series_id:
            raise ValidationError(
                "Bound SRP series_id does not match registry: "
                f"{binding_series_id} != {pack_series_id} ({digest})"
            )
        if pack_series_id != title_series_id:
            raise ValidationError(
                "Bound SRP series_id is incompatible with the title: "
                f"title {paths.project_id}/{paths.title_id} uses {title_series_id}, "
                f"but bound pack {entry['pack_id']}@{entry['pack_version']} uses {pack_series_id}"
            )
        result.append(dict(entry))
    return result


def research_status(paths: TitlePaths) -> dict[str, Any]:
    state = read_json(paths.state)
    snapshot = read_json(paths.research_snapshot) if paths.research_snapshot.exists() else None
    return {
        "series_id": effective_series_id(paths),
        "mode": research_mode(paths),
        "branch_map": branch_map(paths) if research_mode(paths) != "legacy" else {},
        "bindings": load_bindings(paths).get("bindings", []),
        "resolve_stage": state.get("stages", {}).get("research_resolve"),
        "approval_stage": state.get("stages", {}).get("research"),
        "snapshot": snapshot,
    }

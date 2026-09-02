from __future__ import annotations

from typing import Any

from .io import read_json
from .workspace import TitlePaths

BRANCH_REQUIREMENTS: dict[str, set[str]] = {
    "clean": {"S"},
    "tw": {"A", "D"},
    "jp": {"A", "B", "C"},
}

PROFILE_BRANCHES: dict[str, tuple[str, ...]] = {
    "full": ("tw", "jp"),
    "single": ("clean",),
    "source-assisted": ("clean",),
    "dub": ("tw",),
    "bilingual": ("jp",),
}

PROFILE_REQUIREMENTS: dict[str, dict[str, set[str]]] = {
    "source-assisted": {"clean": {"S", "C"}},
}


def available_roles(paths: TitlePaths) -> set[str]:
    manifest = read_json(paths.manifest)
    return {str(role) for role in manifest.get("sources", {})}


def active_branches(paths: TitlePaths) -> list[str]:
    config = read_json(paths.title_config)
    roles = available_roles(paths)
    profile = str(config.get("workflow", {}).get("profile", "auto")).lower()
    if profile == "auto":
        candidates = [
            branch for branch, required in BRANCH_REQUIREMENTS.items() if required.issubset(roles)
        ]
    else:
        candidates = list(PROFILE_BRANCHES.get(profile, ()))
    result: list[str] = []
    for branch in candidates:
        branch_cfg = config.get(f"{branch}_branch", {})
        if branch_cfg.get("enabled", True) is False:
            continue
        result.append(branch)
    return result


def missing_roles_for_profile(paths: TitlePaths) -> dict[str, list[str]]:
    config = read_json(paths.title_config)
    roles = available_roles(paths)
    profile = str(config.get("workflow", {}).get("profile", "auto")).lower()
    branches = list(PROFILE_BRANCHES.get(profile, ())) if profile != "auto" else []
    result: dict[str, list[str]] = {}
    for branch in branches:
        required = PROFILE_REQUIREMENTS.get(profile, {}).get(branch, BRANCH_REQUIREMENTS[branch])
        missing = required - roles
        if missing:
            result[branch] = sorted(missing)
    return result


def branch_release_filename(title_id: str, branch: str) -> str:
    if branch == "clean":
        return f"{title_id}.zh-CN.ass"
    if branch == "tw":
        return f"{title_id}.zh-CN.tw.ass"
    if branch == "jp":
        return f"{title_id}.zh-CN-ja.ass"
    raise ValueError(f"Unknown branch: {branch}")


def branch_config(config: dict[str, Any], branch: str) -> dict[str, Any]:
    value = config.get(f"{branch}_branch", {})
    return dict(value) if isinstance(value, dict) else {}

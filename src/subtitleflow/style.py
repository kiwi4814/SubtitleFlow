from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .io import read_json
from .workspace import TitlePaths

DEFAULT_STYLE_PROFILE = "kiwi-collector-v1"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def style_profile_path(paths: TitlePaths, profile: str) -> Path:
    candidate = Path(profile)
    if candidate.suffix.lower() == ".json" or "/" in profile or "\\" in profile:
        if not candidate.is_absolute():
            candidate = paths.repo / candidate
        return candidate.resolve()
    repo_profile = (paths.repo / "styles" / f"{profile}.json").resolve()
    if repo_profile.is_file():
        return repo_profile
    return (Path(__file__).resolve().parent / "styles" / f"{profile}.json").resolve()


def load_style_profile(paths: TitlePaths, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = read_json(paths.title_config) if config is None else config
    style_cfg = config.get("style", {})
    profile_name = str(style_cfg.get("profile", DEFAULT_STYLE_PROFILE))
    profile_path = style_profile_path(paths, profile_name)
    if not profile_path.is_file():
        raise ValidationError(f"ASS style profile not found: {profile_path}")
    profile = read_json(profile_path)
    if not isinstance(profile.get("styles"), dict):
        raise ValidationError(f"Style profile has no styles object: {profile_path}")
    overrides = style_cfg.get("overrides", {})
    if overrides:
        if not isinstance(overrides, dict):
            raise ValidationError("style.overrides must be an object")
        profile = _deep_merge(profile, overrides)
    profile["_profile_path"] = str(profile_path)
    return profile


def ass_style_values(paths: TitlePaths, style_name: str) -> dict[str, str]:
    profile = load_style_profile(paths)
    raw = profile.get("styles", {}).get(style_name)
    if not isinstance(raw, dict):
        raise ValidationError(f"Style profile does not define {style_name}")
    values = {str(key): str(value) for key, value in raw.items()}
    values["Name"] = style_name
    return values


def layout_settings(paths: TitlePaths) -> dict[str, Any]:
    profile = load_style_profile(paths)
    layout = profile.get("layout", {})
    return dict(layout) if isinstance(layout, dict) else {}


def font_policy(paths: TitlePaths) -> dict[str, Any]:
    profile = load_style_profile(paths)
    policy = profile.get("font_policy", {})
    return dict(policy) if isinstance(policy, dict) else {}


def event_override_tag(paths: TitlePaths, style_name: str) -> str | None:
    profile = load_style_profile(paths)
    overrides = profile.get("event_overrides", {})
    if not isinstance(overrides, dict):
        return None
    raw = overrides.get(style_name)
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def source_preservation(paths: TitlePaths) -> dict[str, Any]:
    profile = load_style_profile(paths)
    raw = profile.get("source_preservation", {})
    return dict(raw) if isinstance(raw, dict) else {}


def is_special_source_style(paths: TitlePaths, style_name: str) -> bool:
    """Return True for source styles that should be preserved in hybrid mode.

    The default policy is deliberately conservative: named note/title/song/screen/OP/ED
    styles are treated as authored typesetting even when a particular event has no complex
    override tags. Projects can replace the name/prefix lists through style.overrides.
    """
    policy = source_preservation(paths)
    if not policy.get("preserve_special_styles", True):
        return False
    value = " ".join(style_name.strip().casefold().split())
    if not value:
        return False
    exact = {" ".join(str(item).strip().casefold().split()) for item in policy.get("special_style_names", [])}
    if value in exact:
        return True
    for raw_prefix in policy.get("special_style_prefixes", []):
        prefix = " ".join(str(raw_prefix).strip().casefold().split())
        if not prefix:
            continue
        if value == prefix:
            return True
        if value.startswith(prefix + " ") or value.startswith(prefix + "-") or value.startswith(prefix + "_"):
            return True
    return False

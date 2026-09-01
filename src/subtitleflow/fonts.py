from __future__ import annotations

import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .errors import GateError, ValidationError
from .formats.ass import parse_ass
from .io import read_json, write_json
from .state import update_stage
from .style import font_policy
from .util import sha256_file
from .workspace import TitlePaths

_FONT_EXTENSIONS = {".ttf", ".otf", ".ttc", ".otc"}
_INLINE_FONT_RE = re.compile(r"\\fn([^\\}]+)", flags=re.IGNORECASE)


def display_family(name: str) -> str:
    value = name.strip()
    if value.startswith("@"):
        value = value[1:]
    return " ".join(value.split())


def normalize_family(name: str) -> str:
    return display_family(name).casefold()


def font_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".ttf":
        return "font/ttf"
    if suffix == ".otf":
        return "font/otf"
    if suffix in {".ttc", ".otc"}:
        return "font/collection"
    raise ValidationError(f"Unsupported font attachment type: {path}")


def _style_font_map(path: Path) -> tuple[dict[str, str], set[str]]:
    doc = parse_ass(path)
    used_styles = {
        event.fields.get("Style", "").strip()
        for event in doc.events
        if event.fields.get("Style", "").strip()
    }
    style_map: dict[str, str] = {}
    bounds = doc.section_bounds.get("[v4+ styles]") or doc.section_bounds.get("[v4 styles]")
    if not bounds:
        return style_map, used_styles
    style_format = doc.style_format
    if not style_format:
        return style_map, used_styles
    for line in doc.lines[bounds[0] + 1 : bounds[1]]:
        if not line.lstrip().lower().startswith("style:"):
            continue
        payload = line.partition(":")[2].lstrip()
        parts = payload.split(",", maxsplit=len(style_format) - 1)
        if len(parts) != len(style_format):
            continue
        fields = {name: value for name, value in zip(style_format, parts, strict=True)}
        name = fields.get("Name", "").strip()
        font = fields.get("Fontname", "").strip()
        if name and font:
            style_map[name] = font
    return style_map, used_styles


def referenced_font_families(path: Path) -> dict[str, list[str]]:
    doc = parse_ass(path)
    style_map, used_styles = _style_font_map(path)
    reasons: dict[str, set[str]] = defaultdict(set)
    for style in sorted(used_styles):
        font = style_map.get(style)
        if font:
            reasons[display_family(font)].add(f"style:{style}")
    for event in doc.events:
        text = event.fields.get("Text", "")
        for match in _INLINE_FONT_RE.finditer(text):
            family = match.group(1).strip()
            if family:
                reasons[display_family(family)].add("inline-fn")
    return {family: sorted(items) for family, items in sorted(reasons.items())}


def required_fonts(paths: TitlePaths) -> dict[str, list[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for ass in sorted(
        path
        for path in paths.release.glob("*.ass")
        if not path.name.endswith(".preview.ass")
    ):
        for family, reasons in referenced_font_families(ass).items():
            for reason in reasons:
                merged[family].add(f"{ass.name}:{reason}")
    if not merged:
        policy = font_policy(paths)
        for item in policy.get("required_families", []):
            if isinstance(item, dict) and item.get("required"):
                family = str(item.get("family", "")).strip()
                if family:
                    merged[family].add("style-profile:required")
    return {family: sorted(reasons) for family, reasons in sorted(merged.items())}


def _expand_path(value: str, *, base: Path) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(value))
    path = Path(expanded)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _load_font_map(paths: TitlePaths, override: Path | None) -> dict[str, list[Path]]:
    config = read_json(paths.title_config)
    fonts_cfg = config.get("fonts", {})
    raw_map = override
    if raw_map is None:
        value = fonts_cfg.get("map_file", "fonts/font-map.json")
        raw_map = _expand_path(str(value), base=paths.repo)
    if not raw_map.is_file():
        return {}
    data = read_json(raw_map)
    families = data.get("families", {})
    if not isinstance(families, dict):
        raise ValidationError(f"Font map must contain a families object: {raw_map}")
    result: dict[str, list[Path]] = {}
    for family, values in families.items():
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            raise ValidationError(f"Font map entry must be a string or list: {family}")
        files = [_expand_path(str(value), base=raw_map.parent) for value in values]
        result[str(family)] = files
    return result



def fonttools_available() -> bool:
    try:
        import fontTools  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return False
    return True

def _fonttools_names(path: Path) -> set[str]:
    try:
        from fontTools.ttLib import TTCollection, TTFont  # type: ignore[import-not-found]
    except ImportError:
        return set()

    def names_from_font(font: Any) -> set[str]:
        values: set[str] = set()
        if "name" not in font:
            return values
        for record in font["name"].names:
            if record.nameID not in {1, 4, 6, 16, 17}:
                continue
            try:
                text = record.toUnicode().strip()
            except Exception:
                continue
            if text:
                values.add(text)
        return values

    try:
        if path.suffix.lower() in {".ttc", ".otc"}:
            collection = TTCollection(str(path), lazy=True)
            try:
                names: set[str] = set()
                for font in collection.fonts:
                    names.update(names_from_font(font))
                return names
            finally:
                collection.close()
        font = TTFont(str(path), lazy=True)
        try:
            return names_from_font(font)
        finally:
            font.close()
    except Exception:
        return set()


def _candidate_font_files(paths: TitlePaths, extra_dirs: Iterable[Path]) -> list[Path]:
    config = read_json(paths.title_config)
    fonts_cfg = config.get("fonts", {})
    raw_dirs = list(fonts_cfg.get("directories", ["fonts/local"]))
    directories = [_expand_path(str(value), base=paths.repo) for value in raw_dirs]
    directories.extend(path.resolve() for path in extra_dirs)
    found: set[Path] = set()
    for directory in directories:
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in _FONT_EXTENSIONS:
                found.add(path.resolve())
    return sorted(found)


def _family_aliases(paths: TitlePaths, family: str) -> set[str]:
    config = read_json(paths.title_config)
    aliases_cfg = config.get("fonts", {}).get("aliases", {})
    aliases = {family}
    if isinstance(aliases_cfg, dict):
        raw = aliases_cfg.get(family, [])
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            aliases.update(str(item) for item in raw)
    return {normalize_family(item) for item in aliases if str(item).strip()}


def _resolved_record(family: str, path: Path, reasons: list[str]) -> dict[str, Any]:
    return {
        "family": family,
        "path": str(path),
        "attachment_name": path.name,
        "mime_type": font_mime_type(path),
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
        "reasons": reasons,
    }


def audit_fonts(
    paths: TitlePaths,
    *,
    extra_dirs: Iterable[Path] = (),
    map_file: Path | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    required = required_fonts(paths)
    explicit = _load_font_map(paths, map_file)
    candidates = _candidate_font_files(paths, extra_dirs)
    candidate_names = {path: _fonttools_names(path) for path in candidates}
    resolved: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for family, reasons in required.items():
        matches: list[Path] = []
        explicit_values: list[Path] = []
        wanted_key = normalize_family(family)
        for mapped_family, mapped_paths in explicit.items():
            if normalize_family(mapped_family) == wanted_key:
                explicit_values.extend(mapped_paths)
        for path in explicit_values:
            if not path.is_file() or path.suffix.lower() not in _FONT_EXTENSIONS:
                continue
            if fonttools_available() and not _fonttools_names(path):
                continue
            matches.append(path.resolve())
        if not matches:
            desired = _family_aliases(paths, family)
            for path, names in candidate_names.items():
                normalized_names = {normalize_family(name) for name in names}
                if desired & normalized_names:
                    matches.append(path)
        if not matches:
            # Filename matching is a last-resort convenience, never the only production proof if
            # FontTools metadata is available.
            desired = _family_aliases(paths, family)
            for path in candidates:
                if normalize_family(path.stem) in desired:
                    matches.append(path)
        if matches:
            for path in sorted(set(matches)):
                resolved.append(_resolved_record(family, path, reasons))
        else:
            missing.append({"family": family, "reasons": reasons})

    # De-duplicate attachments by exact local file path while retaining all family reasons.
    by_path: dict[str, dict[str, Any]] = {}
    for item in resolved:
        key = item["path"]
        if key not in by_path:
            by_path[key] = {**item, "families": [item["family"]]}
        else:
            by_path[key]["families"].append(item["family"])
            by_path[key]["reasons"] = sorted(set(by_path[key]["reasons"]) | set(item["reasons"]))
    attachments = []
    for item in by_path.values():
        item["families"] = sorted(set(item["families"]))
        item.pop("family", None)
        attachments.append(item)
    attachments.sort(key=lambda item: item["attachment_name"].casefold())

    config = read_json(paths.title_config)
    require_all = bool(config.get("fonts", {}).get("require_all_referenced", True))
    report = {
        "schema_version": 1,
        "ok": not missing or not require_all,
        "required_families": [
            {"family": family, "reasons": reasons} for family, reasons in required.items()
        ],
        "attachments": attachments,
        "missing": missing,
        "require_all_referenced": require_all,
        "fonttools_available": fonttools_available(),
    }
    if write_report:
        write_json(paths.qa / "fonts.json", report)
        update_stage(paths, "fonts", "passed" if report["ok"] else "failed", missing=len(missing))
    return report


def require_font_attachments(paths: TitlePaths) -> list[dict[str, Any]]:
    path = paths.qa / "fonts.json"
    if not path.is_file():
        raise GateError("Font audit is missing; run `subflow fonts audit PROJECT TITLE`")
    report = read_json(path)
    if not report.get("ok"):
        missing = ", ".join(str(item.get("family")) for item in report.get("missing", []))
        raise GateError(f"Required subtitle fonts are unresolved: {missing}")
    attachments = list(report.get("attachments", []))
    for item in attachments:
        font_path = Path(str(item.get("path", "")))
        if not font_path.is_file():
            raise GateError(f"Font attachment disappeared: {font_path}")
        if sha256_file(font_path) != item.get("sha256"):
            raise GateError(f"Font attachment changed after audit: {font_path}")
    return attachments

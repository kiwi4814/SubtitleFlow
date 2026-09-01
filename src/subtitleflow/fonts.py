from __future__ import annotations

import os
import re
import shutil
import zipfile
from collections import defaultdict
from hashlib import sha256
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
DEFAULT_FONT_REGISTRY = "fonts/font-registry.json"


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


def configured_font_map_path(paths: TitlePaths, override: Path | None = None) -> Path:
    if override is not None:
        return override.expanduser().resolve()
    config = read_json(paths.title_config)
    value = config.get("fonts", {}).get("map_file", "fonts/font-map.json")
    return _expand_path(str(value), base=paths.repo)


def configured_font_registry_path(paths: TitlePaths, override: Path | None = None) -> Path:
    if override is not None:
        return override.expanduser().resolve()
    config = read_json(paths.title_config)
    value = config.get("fonts", {}).get("registry_file", DEFAULT_FONT_REGISTRY)
    return _expand_path(str(value), base=paths.repo)


def font_registry_path(repo: Path, override: Path | None = None) -> Path:
    if override is not None:
        return override.expanduser().resolve()
    return (repo / DEFAULT_FONT_REGISTRY).resolve()


def load_font_registry(repo: Path, override: Path | None = None) -> dict[str, Any]:
    path = font_registry_path(repo, override)
    if not path.is_file():
        return {"schema_version": 1, "id": "none", "fonts": []}
    data = read_json(path)
    fonts = data.get("fonts", [])
    if not isinstance(fonts, list):
        raise ValidationError(f"Font registry must contain a fonts array: {path}")
    seen_ids: set[str] = set()
    seen_files: set[str] = set()
    for entry in fonts:
        if not isinstance(entry, dict):
            raise ValidationError(f"Font registry entries must be objects: {path}")
        font_id = str(entry.get("id", "")).strip()
        family = str(entry.get("family", "")).strip()
        canonical_file = str(entry.get("canonical_file", "")).strip()
        digest = str(entry.get("sha256", "")).strip().lower()
        if not font_id or not family or not canonical_file or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValidationError(
                "Font registry entries require id, family, canonical_file and a SHA-256 digest"
            )
        if Path(canonical_file).name != canonical_file:
            raise ValidationError(f"Font registry canonical_file must be a basename: {canonical_file}")
        if font_id in seen_ids:
            raise ValidationError(f"Duplicate font registry id: {font_id}")
        file_key = canonical_file.casefold()
        if file_key in seen_files:
            raise ValidationError(f"Duplicate font registry canonical_file: {canonical_file}")
        seen_ids.add(font_id)
        seen_files.add(file_key)
    data["_registry_path"] = str(path)
    return data


def _registry_match_names(entry: dict[str, Any]) -> set[str]:
    values = {str(entry.get("family", ""))}
    raw = entry.get("aliases", [])
    if isinstance(raw, str):
        raw = [raw]
    if isinstance(raw, list):
        values.update(str(item) for item in raw)
    return {normalize_family(value) for value in values if value.strip()}


def _registry_expected_names(entry: dict[str, Any]) -> set[str]:
    values = {str(entry.get("family", ""))}
    for key in ("aliases", "internal_names"):
        raw = entry.get(key, [])
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            values.update(str(item) for item in raw)
    postscript = str(entry.get("postscript", "")).strip()
    if postscript:
        values.add(postscript)
    return {normalize_family(value) for value in values if value.strip()}


def _registry_entry_for_family(registry: dict[str, Any], family: str) -> dict[str, Any] | None:
    wanted = normalize_family(family)
    for entry in registry.get("fonts", []):
        if isinstance(entry, dict) and wanted in _registry_match_names(entry):
            return entry
    return None


def _font_inventory(source: Path) -> dict[str, list[dict[str, str]]]:
    source = source.expanduser().resolve()
    if not source.exists():
        raise ValidationError(f"Font source does not exist: {source}")
    inventory: dict[str, list[dict[str, str]]] = defaultdict(list)
    if source.is_dir():
        for path in sorted(source.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in _FONT_EXTENSIONS:
                continue
            inventory[sha256_file(path)].append({"kind": "file", "value": str(path.resolve())})
        return dict(inventory)
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            for info in archive.infolist():
                if info.is_dir() or Path(info.filename).suffix.lower() not in _FONT_EXTENSIONS:
                    continue
                digest = sha256()
                with archive.open(info, "r") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                inventory[digest.hexdigest()].append(
                    {"kind": "zip", "value": info.filename, "archive": str(source)}
                )
        return dict(inventory)
    if source.is_file() and source.suffix.lower() in _FONT_EXTENSIONS:
        inventory[sha256_file(source)].append({"kind": "file", "value": str(source)})
        return dict(inventory)
    raise ValidationError("Font source must be a font file, directory, or ZIP archive")


def _copy_inventory_item(item: dict[str, str], destination: Path) -> None:
    if item["kind"] == "file":
        shutil.copy2(Path(item["value"]), destination)
        return
    archive_path = Path(item["archive"])
    with zipfile.ZipFile(archive_path) as archive, archive.open(item["value"], "r") as source:
        with destination.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)


def verify_registered_fonts(
    repo: Path,
    *,
    registry_file: Path | None = None,
    local_dir: Path | None = None,
) -> dict[str, Any]:
    repo = repo.resolve()
    registry = load_font_registry(repo, registry_file)
    registry_path = Path(str(registry.get("_registry_path", font_registry_path(repo, registry_file))))
    local = (local_dir or repo / "fonts" / "local").expanduser().resolve()
    installed: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for entry in registry.get("fonts", []):
        if not isinstance(entry, dict):
            continue
        path = local / str(entry["canonical_file"])
        if not path.is_file():
            errors.append(
                {"id": entry["id"], "file": str(path), "reason": "missing-font-file"}
            )
            continue
        actual_sha = sha256_file(path)
        if actual_sha != entry["sha256"]:
            errors.append(
                {
                    "id": entry["id"],
                    "file": str(path),
                    "reason": "sha256-mismatch",
                    "expected_sha256": entry["sha256"],
                    "actual_sha256": actual_sha,
                }
            )
            continue
        if int(entry.get("size", path.stat().st_size)) != path.stat().st_size:
            errors.append(
                {
                    "id": entry["id"],
                    "file": str(path),
                    "reason": "size-mismatch",
                    "expected_size": entry.get("size"),
                    "actual_size": path.stat().st_size,
                }
            )
            continue
        metadata = _fonttools_metadata(path) if fonttools_available() else {}
        if metadata:
            actual_names = {normalize_family(value) for value in metadata.get("names", [])}
            if not (_registry_expected_names(entry) & actual_names):
                errors.append(
                    {
                        "id": entry["id"],
                        "file": str(path),
                        "reason": "name-table-mismatch",
                        "actual_names": metadata.get("names", []),
                    }
                )
                continue
        installed.append(
            {
                "id": entry["id"],
                "family": entry["family"],
                "file": str(path),
                "sha256": actual_sha,
                "size": path.stat().st_size,
                "mime_type": font_mime_type(path),
                "metadata": metadata,
                "metadata_verified": bool(metadata),
            }
        )
    return {
        "schema_version": 1,
        "ok": not errors and len(installed) == len(registry.get("fonts", [])),
        "registry": {
            "id": registry.get("id"),
            "path": str(registry_path),
            "sha256": sha256_file(registry_path) if registry_path.is_file() else None,
        },
        "local_dir": str(local),
        "fonttools_available": fonttools_available(),
        "installed": installed,
        "errors": errors,
    }


def install_registered_fonts(
    repo: Path,
    source: Path,
    *,
    registry_file: Path | None = None,
    local_dir: Path | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    repo = repo.resolve()
    registry = load_font_registry(repo, registry_file)
    entries = [entry for entry in registry.get("fonts", []) if isinstance(entry, dict)]
    if not entries:
        raise ValidationError("Font registry is empty; nothing to install")
    inventory = _font_inventory(source)
    missing = [entry for entry in entries if str(entry["sha256"]) not in inventory]
    if missing:
        detail = ", ".join(f"{entry['id']} ({entry['canonical_file']})" for entry in missing)
        raise GateError("Font source does not contain every registered SHA-256: " + detail)

    local = (local_dir or repo / "fonts" / "local").expanduser().resolve()
    local.mkdir(parents=True, exist_ok=True)
    conflicts: list[str] = []
    for entry in entries:
        destination = local / str(entry["canonical_file"])
        if destination.is_file() and sha256_file(destination) != entry["sha256"] and not replace:
            conflicts.append(destination.name)
    if conflicts:
        raise GateError(
            "Registered font destination already exists with different bytes; use --replace explicitly: "
            + ", ".join(sorted(conflicts))
        )

    installed: list[dict[str, Any]] = []
    for entry in entries:
        destination = local / str(entry["canonical_file"])
        if destination.is_file() and sha256_file(destination) == entry["sha256"]:
            action = "reused"
        else:
            _copy_inventory_item(inventory[str(entry["sha256"])][0], destination)
            action = "installed"
        installed.append(
            {
                "id": entry["id"],
                "family": entry["family"],
                "file": str(destination),
                "sha256": sha256_file(destination),
                "action": action,
            }
        )

    verification = verify_registered_fonts(
        repo,
        registry_file=registry_file,
        local_dir=local,
    )
    if not verification["ok"]:
        raise GateError("Installed fonts failed registry verification")
    return {
        "schema_version": 1,
        "ok": True,
        "source": str(source.expanduser().resolve()),
        "registry": verification["registry"],
        "local_dir": str(local),
        "installed": installed,
        "verification": verification,
    }


def _load_font_map(paths: TitlePaths, override: Path | None) -> dict[str, list[Path]]:
    raw_map = configured_font_map_path(paths, override)
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


def _fonttools_metadata(path: Path) -> dict[str, Any]:
    try:
        from fontTools.ttLib import TTCollection, TTFont  # type: ignore[import-not-found]
    except ImportError:
        return {}

    def metadata_from_font(font: Any) -> dict[str, Any]:
        groups: dict[str, set[str]] = {
            "families": set(),
            "full_names": set(),
            "postscript_names": set(),
            "versions": set(),
            "typographic_families": set(),
            "typographic_subfamilies": set(),
        }
        if "name" not in font:
            return {key: [] for key in groups}
        name_map = {
            1: "families",
            4: "full_names",
            5: "versions",
            6: "postscript_names",
            16: "typographic_families",
            17: "typographic_subfamilies",
        }
        for record in font["name"].names:
            key = name_map.get(record.nameID)
            if key is None:
                continue
            try:
                text = record.toUnicode().strip()
            except Exception:
                continue
            if text:
                groups[key].add(text)
        metadata = {key: sorted(values) for key, values in groups.items()}
        if "OS/2" in font:
            metadata["weight_class"] = int(font["OS/2"].usWeightClass)
            metadata["fs_type"] = int(font["OS/2"].fsType)
        return metadata

    def merge_faces(faces: list[dict[str, Any]]) -> dict[str, Any]:
        merged: dict[str, Any] = {"faces": len(faces)}
        for key in (
            "families",
            "full_names",
            "postscript_names",
            "versions",
            "typographic_families",
            "typographic_subfamilies",
        ):
            merged[key] = sorted({value for face in faces for value in face.get(key, [])})
        merged["weight_classes"] = sorted(
            {int(face["weight_class"]) for face in faces if "weight_class" in face}
        )
        merged["fs_types"] = sorted({int(face["fs_type"]) for face in faces if "fs_type" in face})
        merged["names"] = sorted(
            {
                value
                for key in (
                    "families",
                    "full_names",
                    "postscript_names",
                )
                for value in merged[key]
            }
        )
        return merged

    try:
        if path.suffix.lower() in {".ttc", ".otc"}:
            collection = TTCollection(str(path), lazy=True)
            try:
                return merge_faces([metadata_from_font(font) for font in collection.fonts])
            finally:
                collection.close()
        font = TTFont(str(path), lazy=True)
        try:
            return merge_faces([metadata_from_font(font)])
        finally:
            font.close()
    except Exception:
        return {}


def _fonttools_names(path: Path) -> set[str]:
    return set(_fonttools_metadata(path).get("names", []))


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


def _family_aliases(
    paths: TitlePaths,
    family: str,
    *,
    registry_entry: dict[str, Any] | None = None,
) -> set[str]:
    config = read_json(paths.title_config)
    aliases_cfg = config.get("fonts", {}).get("aliases", {})
    aliases = {family}
    if isinstance(aliases_cfg, dict):
        raw = aliases_cfg.get(family, [])
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, list):
            aliases.update(str(item) for item in raw)
    if registry_entry is not None:
        aliases.add(str(registry_entry.get("family", "")))
        raw_aliases = registry_entry.get("aliases", [])
        if isinstance(raw_aliases, str):
            raw_aliases = [raw_aliases]
        if isinstance(raw_aliases, list):
            aliases.update(str(item) for item in raw_aliases)
        postscript = str(registry_entry.get("postscript", "")).strip()
        if postscript:
            aliases.add(postscript)
    return {normalize_family(item) for item in aliases if str(item).strip()}


def _resolved_record(
    family: str,
    path: Path,
    reasons: list[str],
    *,
    registry_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = _fonttools_metadata(path) if fonttools_available() else {}
    record: dict[str, Any] = {
        "family": family,
        "canonical_family": str(registry_entry.get("family")) if registry_entry else family,
        "path": str(path),
        "attachment_name": str(registry_entry.get("canonical_file")) if registry_entry else path.name,
        "mime_type": font_mime_type(path),
        "sha256": sha256_file(path),
        "size": path.stat().st_size,
        "reasons": reasons,
        "metadata_verified": bool(metadata),
    }
    if metadata:
        record["metadata"] = metadata
    if registry_entry is not None:
        record["registry"] = {
            "id": registry_entry.get("id"),
            "family": registry_entry.get("family"),
            "version": registry_entry.get("version"),
            "sha256": registry_entry.get("sha256"),
        }
    return record


def audit_fonts(
    paths: TitlePaths,
    *,
    extra_dirs: Iterable[Path] = (),
    map_file: Path | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    required = required_fonts(paths)
    explicit = _load_font_map(paths, map_file)
    registry_path = configured_font_registry_path(paths)
    registry = load_font_registry(paths.repo, registry_path)
    candidates = _candidate_font_files(paths, extra_dirs)
    candidate_names = {path: _fonttools_names(path) for path in candidates}
    resolved: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    invalid_mappings: list[dict[str, Any]] = []

    for family, reasons in required.items():
        matches: list[Path] = []
        explicit_values: list[Path] = []
        registry_entry = _registry_entry_for_family(registry, family)
        wanted_key = normalize_family(family)
        for mapped_family, mapped_paths in explicit.items():
            if normalize_family(mapped_family) == wanted_key:
                explicit_values.extend(mapped_paths)
        desired = _family_aliases(paths, family, registry_entry=registry_entry)
        for path in explicit_values:
            if not path.is_file() or path.suffix.lower() not in _FONT_EXTENSIONS:
                invalid_mappings.append(
                    {"family": family, "path": str(path), "reason": "missing-or-unsupported-file"}
                )
                continue
            if fonttools_available():
                names = _fonttools_names(path)
                normalized_names = {normalize_family(name) for name in names}
                if not names:
                    invalid_mappings.append(
                        {"family": family, "path": str(path), "reason": "unreadable-font-metadata"}
                    )
                    continue
                if not (desired & normalized_names):
                    invalid_mappings.append(
                        {
                            "family": family,
                            "path": str(path),
                            "reason": "family-metadata-mismatch",
                            "declared_names": sorted(names),
                        }
                    )
                    continue
            if registry_entry is not None and sha256_file(path) != registry_entry.get("sha256"):
                invalid_mappings.append(
                    {
                        "family": family,
                        "path": str(path),
                        "reason": "registry-sha256-mismatch",
                        "expected_sha256": registry_entry.get("sha256"),
                        "actual_sha256": sha256_file(path),
                    }
                )
                continue
            matches.append(path.resolve())
        if not matches and registry_entry is not None:
            # A registry SHA is an authoritative byte identity even without FontTools. Name Table
            # verification is an additional check when available, not a prerequisite for locating
            # an already registered font. This also makes minimal installations deterministic.
            exact_sha_matches = [
                path
                for path in candidates
                if sha256_file(path) == str(registry_entry.get("sha256"))
            ]
            if exact_sha_matches:
                matches.extend(exact_sha_matches)

        if not matches:
            metadata_matches: list[Path] = []
            for path, names in candidate_names.items():
                normalized_names = {normalize_family(name) for name in names}
                if desired & normalized_names:
                    metadata_matches.append(path)
            if registry_entry is not None:
                exact = [
                    path
                    for path in metadata_matches
                    if sha256_file(path) == registry_entry.get("sha256")
                ]
                if exact:
                    matches.extend(exact)
                elif metadata_matches:
                    for path in metadata_matches:
                        invalid_mappings.append(
                            {
                                "family": family,
                                "path": str(path),
                                "reason": "registry-sha256-mismatch",
                                "expected_sha256": registry_entry.get("sha256"),
                                "actual_sha256": sha256_file(path),
                            }
                        )
            else:
                matches.extend(metadata_matches)
        if not matches:
            # Filename matching is a last-resort convenience, never the only production proof if
            # FontTools metadata is available.
            desired = _family_aliases(paths, family, registry_entry=registry_entry)
            for path in candidates:
                if normalize_family(path.stem) not in desired:
                    continue
                if registry_entry is not None and sha256_file(path) != registry_entry.get("sha256"):
                    invalid_mappings.append(
                        {
                            "family": family,
                            "path": str(path),
                            "reason": "registry-sha256-mismatch",
                            "expected_sha256": registry_entry.get("sha256"),
                            "actual_sha256": sha256_file(path),
                        }
                    )
                    continue
                if not fonttools_available() or _fonttools_names(path):
                    matches.append(path)
        if matches:
            for path in sorted(set(matches)):
                resolved.append(
                    _resolved_record(
                        family,
                        path,
                        reasons,
                        registry_entry=registry_entry,
                    )
                )
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
    deduped_by_path = []
    for item in by_path.values():
        item["families"] = sorted(set(item["families"]))
        item.pop("family", None)
        deduped_by_path.append(item)

    # MKV attachment names are the user-visible identity inside the container. Never
    # freeze two same-name files with different bytes: players may select either one
    # and the result becomes non-deterministic. Same-name + same-SHA duplicates are
    # safe to collapse into one attachment while retaining all family/reason metadata.
    by_attachment_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in deduped_by_path:
        by_attachment_name[str(item["attachment_name"]).casefold()].append(item)
    attachments: list[dict[str, Any]] = []
    collisions: list[dict[str, Any]] = []
    for items in by_attachment_name.values():
        hashes = {str(item["sha256"]) for item in items}
        if len(hashes) > 1:
            collisions.append(
                {
                    "attachment_name": items[0]["attachment_name"],
                    "files": [
                        {"path": item["path"], "sha256": item["sha256"], "families": item["families"]}
                        for item in sorted(items, key=lambda value: str(value["path"]))
                    ],
                }
            )
            continue
        merged = dict(sorted(items, key=lambda value: str(value["path"]))[0])
        merged["families"] = sorted({family for item in items for family in item["families"]})
        merged["reasons"] = sorted({reason for item in items for reason in item["reasons"]})
        attachments.append(merged)
    attachments.sort(key=lambda item: item["attachment_name"].casefold())
    collisions.sort(key=lambda item: str(item["attachment_name"]).casefold())

    config = read_json(paths.title_config)
    require_all = bool(config.get("fonts", {}).get("require_all_referenced", True))
    report = {
        "schema_version": 2,
        "ok": (not missing or not require_all) and not collisions and not invalid_mappings,
        "required_families": [
            {"family": family, "reasons": reasons} for family, reasons in required.items()
        ],
        "attachments": attachments,
        "missing": missing,
        "collisions": collisions,
        "invalid_mappings": invalid_mappings,
        "require_all_referenced": require_all,
        "fonttools_available": fonttools_available(),
        "registry": {
            "id": registry.get("id"),
            "path": str(registry_path) if registry_path.is_file() else None,
            "sha256": sha256_file(registry_path) if registry_path.is_file() else None,
        },
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
        invalid_mappings = report.get("invalid_mappings", [])
        if invalid_mappings:
            details = "; ".join(
                f"{item.get('family')} -> {item.get('path')} ({item.get('reason')})"
                for item in invalid_mappings
            )
            raise GateError("Font resolution does not satisfy the requested ASS family: " + details)
        collisions = report.get("collisions", [])
        if collisions:
            names = ", ".join(str(item.get("attachment_name")) for item in collisions)
            raise GateError(
                "Font audit found same-name attachment files with different SHA-256: " + names
            )
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

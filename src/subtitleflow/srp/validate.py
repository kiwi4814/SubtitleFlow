from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..errors import ValidationError
from .schema import STANDARD_JSONL, read_json_strict, schema_registry, validator

MAX_NORMATIVE_BYTES = 32 * 1024 * 1024
MAX_RECORDS = 50_000
MAX_RECORD_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class RecordLoc:
    file: str
    line: int


@dataclass(slots=True)
class ValidatedPack:
    root: Path
    manifest: dict[str, Any]
    records: dict[str, list[dict[str, Any]]]
    counts: dict[str, int]


def _scope_key(scope: dict[str, Any]) -> tuple[str, str | None, str | None, str]:
    return (
        scope["series_id"],
        scope.get("title_id"),
        scope.get("branch_id"),
        scope["level"],
    )


def _scope_within_pack(scope: dict[str, Any], pack_scope: dict[str, Any]) -> bool:
    if scope["series_id"] != pack_scope["series_id"]:
        return False
    pack_title = pack_scope.get("title_id")
    pack_branch = pack_scope.get("branch_id")
    level = scope.get("level")

    if pack_title is None and pack_branch is None:
        return True
    if pack_title is not None and pack_branch is None:
        return level in {"title", "branch"} and scope.get("title_id") == pack_title
    if pack_title is None and pack_branch is not None:
        return scope.get("branch_id") == pack_branch and level in {"series_branch", "branch"}
    return (
        level == "branch"
        and scope.get("title_id") == pack_title
        and scope.get("branch_id") == pack_branch
    )


def _read_jsonl(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    total = 0
    try:
        with path.open("r", encoding="utf-8", errors="strict") as handle:
            for line_no, raw in enumerate(handle, 1):
                total += 1
                if total > MAX_RECORDS:
                    errors.append(f"{path.name}: exceeds maximum record count {MAX_RECORDS}")
                    break
                if not raw.strip():
                    errors.append(f"{path.name}:{line_no}: blank lines are not allowed")
                    continue
                if len(raw.encode("utf-8")) > MAX_RECORD_BYTES:
                    errors.append(f"{path.name}:{line_no}: record exceeds {MAX_RECORD_BYTES} bytes")
                    continue
                try:
                    record = read_json_strict_line(raw, path.name, line_no)
                except ValidationError as exc:
                    errors.append(str(exc))
                    continue
                if not isinstance(record, dict):
                    errors.append(f"{path.name}:{line_no}: JSONL record must be an object")
                    continue
                records.append(record)
    except UnicodeDecodeError:
        errors.append(f"{path.name}: invalid UTF-8")
    return records


def read_json_strict_line(raw: str, filename: str, line_no: int) -> Any:
    from .schema import loads_strict

    try:
        return loads_strict(raw, label=f"{filename}:{line_no}")
    except ValidationError as exc:
        raise ValidationError(str(exc)) from exc


def validate_pack_dir(pack_dir: Path) -> ValidatedPack:
    pack_dir = pack_dir.resolve()
    errors: list[str] = []
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ValidationError("SRP validation failed: manifest.json is missing")

    total_bytes = 0
    for filename in ("manifest.json", *STANDARD_JSONL.keys()):
        path = pack_dir / filename
        if path.exists():
            if not path.is_file() or path.is_symlink():
                errors.append(f"{filename}: must be a regular file")
            else:
                total_bytes += path.stat().st_size
    if total_bytes > MAX_NORMATIVE_BYTES:
        errors.append(f"normative SRP data exceeds {MAX_NORMATIVE_BYTES} bytes")

    try:
        manifest = read_json_strict(manifest_path)
    except ValidationError as exc:
        raise ValidationError(f"SRP validation failed: {exc}") from exc
    if not isinstance(manifest, dict):
        errors.append("manifest.json: root must be an object")
        manifest = {}

    registry = schema_registry()
    manifest_validator = validator("manifest.schema.json", registry)
    for err in sorted(manifest_validator.iter_errors(manifest), key=lambda item: list(item.path)):
        errors.append(f"manifest.json: schema: {err.message}")

    by_file: dict[str, list[dict[str, Any]]] = {name: [] for name in STANDARD_JSONL}
    records: dict[str, dict[str, Any]] = {}
    locs: dict[str, RecordLoc] = {}

    for data_file, schema_file in STANDARD_JSONL.items():
        path = pack_dir / data_file
        if not path.exists():
            continue
        parsed = _read_jsonl(path, errors)
        by_file[data_file] = parsed
        record_validator = validator(schema_file, registry)
        for line_no, record in enumerate(parsed, 1):
            for err in sorted(record_validator.iter_errors(record), key=lambda item: list(item.path)):
                errors.append(f"{data_file}:{line_no}: schema: {err.message}")
            record_id = record.get("id")
            if isinstance(record_id, str):
                if record_id in records:
                    first = locs[record_id]
                    errors.append(
                        f"{data_file}:{line_no}: duplicate id {record_id!r}; "
                        f"first seen at {first.file}:{first.line}"
                    )
                else:
                    records[record_id] = record
                    locs[record_id] = RecordLoc(data_file, line_no)

    pack_scope = manifest.get("scope") if isinstance(manifest, dict) else None
    scoped_files = (
        "entities.jsonl",
        "facts.jsonl",
        "terms.jsonl",
        "decisions.jsonl",
        "unresolved.jsonl",
    )
    if isinstance(pack_scope, dict) and "series_id" in pack_scope:
        for filename in scoped_files:
            for index, record in enumerate(by_file[filename], 1):
                scope = record.get("scope")
                if (
                    isinstance(scope, dict)
                    and "level" in scope
                    and not _scope_within_pack(scope, pack_scope)
                ):
                    errors.append(f"{filename}:{index}: record scope is outside manifest scope")

    entity_ids = {
        record.get("id")
        for record in by_file["entities.jsonl"]
        if isinstance(record.get("id"), str)
    }
    source_ids = {
        record.get("id")
        for record in by_file["sources.jsonl"]
        if isinstance(record.get("id"), str)
    }
    evidence_ids = {
        record.get("id")
        for record in by_file["evidence.jsonl"]
        if isinstance(record.get("id"), str)
    }

    def check_ids(
        filename: str,
        record: dict[str, Any],
        index: int,
        field: str,
        valid: set[str],
    ) -> None:
        values = record.get(field, [])
        if not isinstance(values, list):
            return
        for value in values:
            if isinstance(value, str) and value not in valid:
                errors.append(f"{filename}:{index}: dangling {field} reference {value!r}")

    for filename in scoped_files:
        for index, record in enumerate(by_file[filename], 1):
            check_ids(filename, record, index, "evidence_ids", evidence_ids)

    for index, record in enumerate(by_file["facts.jsonl"], 1):
        check_ids("facts.jsonl", record, index, "related_entities", entity_ids)

    for index, record in enumerate(by_file["terms.jsonl"], 1):
        entity_id = record.get("entity_id")
        if isinstance(entity_id, str) and entity_id not in entity_ids:
            errors.append(f"terms.jsonl:{index}: dangling entity_id reference {entity_id!r}")
        target = record.get("target", {})
        if isinstance(target, dict):
            canonical = target.get("value")
            groups = {
                "accepted_aliases": set(target.get("accepted_aliases", [])),
                "deprecated": set(target.get("deprecated", [])),
                "forbidden": set(target.get("forbidden", [])),
            }
            if isinstance(canonical, str):
                for name, values in groups.items():
                    if canonical in values:
                        errors.append(
                            f"terms.jsonl:{index}: canonical target value also appears in {name}"
                        )
            names = list(groups)
            for left_index in range(len(names)):
                for right_index in range(left_index + 1, len(names)):
                    overlap = groups[names[left_index]] & groups[names[right_index]]
                    if overlap:
                        errors.append(
                            f"terms.jsonl:{index}: target alias categories overlap between "
                            f"{names[left_index]} and {names[right_index]}: {sorted(overlap)!r}"
                        )

    for index, record in enumerate(by_file["decisions.jsonl"], 1):
        applies = record.get("applies_to", {})
        if isinstance(applies, dict):
            for entity_id in applies.get("entity_ids", []):
                if entity_id not in entity_ids:
                    errors.append(
                        f"decisions.jsonl:{index}: dangling applies_to.entity_ids "
                        f"reference {entity_id!r}"
                    )

    for index, record in enumerate(by_file["evidence.jsonl"], 1):
        source_id = record.get("source_id")
        if isinstance(source_id, str) and source_id not in source_ids:
            errors.append(f"evidence.jsonl:{index}: dangling source_id reference {source_id!r}")
        check_ids("evidence.jsonl", record, index, "related_records", set(records))

    for index, record in enumerate(by_file["unresolved.jsonl"], 1):
        check_ids("unresolved.jsonl", record, index, "related_records", set(records))

    seen_terms: dict[tuple[Any, ...], tuple[str, int]] = {}
    for index, record in enumerate(by_file["terms.jsonl"], 1):
        if record.get("status") != "accepted":
            continue
        scope = record.get("scope")
        target = record.get("target")
        if not isinstance(scope, dict) or not isinstance(target, dict):
            continue
        collision_key = (
            record.get("key"),
            *_scope_key(scope),
            target.get("language"),
        )
        if collision_key in seen_terms:
            first_id, first_line = seen_terms[collision_key]
            errors.append(
                f"terms.jsonl:{index}: accepted term conflicts with {first_id!r} at line "
                f"{first_line} for the same key/scope/target language"
            )
        else:
            seen_terms[collision_key] = (str(record.get("id")), index)

    seen_decisions: dict[tuple[Any, ...], tuple[str, int]] = {}
    for index, record in enumerate(by_file["decisions.jsonl"], 1):
        if record.get("status") != "accepted":
            continue
        scope = record.get("scope")
        if not isinstance(scope, dict):
            continue
        collision_key = (record.get("key"), *_scope_key(scope))
        if collision_key in seen_decisions:
            first_id, first_line = seen_decisions[collision_key]
            errors.append(
                f"decisions.jsonl:{index}: accepted decision conflicts with {first_id!r} at "
                f"line {first_line} for the same key/scope"
            )
        else:
            seen_decisions[collision_key] = (str(record.get("id")), index)

    if errors:
        rendered = "\n".join(f"- {error}" for error in errors)
        raise ValidationError(f"SRP validation failed with {len(errors)} error(s):\n{rendered}")

    return ValidatedPack(
        root=pack_dir,
        manifest=manifest,
        records=by_file,
        counts={filename: len(items) for filename, items in by_file.items()},
    )

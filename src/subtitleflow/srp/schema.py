from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from ..errors import ValidationError

STANDARD_JSONL: dict[str, str] = {
    "entities.jsonl": "entity.schema.json",
    "facts.jsonl": "fact.schema.json",
    "terms.jsonl": "term.schema.json",
    "decisions.jsonl": "decision.schema.json",
    "sources.jsonl": "source.schema.json",
    "evidence.jsonl": "evidence.schema.json",
    "unresolved.jsonl": "unresolved.schema.json",
}
NORMATIVE_FILES = ("manifest.json", *STANDARD_JSONL.keys())


def schema_dir() -> Path:
    return Path(__file__).resolve().parent / "schemas"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def loads_strict(payload: str, *, label: str) -> Any:
    try:
        return json.loads(payload, object_pairs_hook=_reject_duplicate_keys)
    except UnicodeError as exc:
        raise ValidationError(f"{label}: invalid UTF-8: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{label}: invalid JSON: {exc.msg} at line {exc.lineno}") from exc


def read_json_strict(path: Path) -> Any:
    try:
        payload = path.read_text(encoding="utf-8", errors="strict")
    except FileNotFoundError as exc:
        raise ValidationError(f"Missing SRP file: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{path.name}: invalid UTF-8") from exc
    return loads_strict(payload, label=path.name)


def schema_registry() -> Registry:
    registry = Registry()
    for path in schema_dir().glob("*.schema.json"):
        data = read_json_strict(path)
        registry = registry.with_resource(data["$id"], Resource.from_contents(data))
    return registry


def validator(filename: str, registry: Registry | None = None) -> Draft202012Validator:
    registry = registry or schema_registry()
    schema = read_json_strict(schema_dir() / filename)
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())

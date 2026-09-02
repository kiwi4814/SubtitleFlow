from __future__ import annotations

import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .errors import ValidationError


def read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise ValidationError(f"Missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    atomic_write_text(path, payload)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp_name)


def load_config(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = read_json(path)
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise ValidationError(
                "YAML config requested but PyYAML is not installed. "
                "Use JSON or install SubtitleFlow with the 'yaml' extra."
            ) from exc
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValidationError(f"Missing config file: {path}") from exc
        except Exception as exc:  # PyYAML exposes multiple parse exceptions.
            raise ValidationError(f"Invalid YAML in {path}: {exc}") from exc
    else:
        raise ValidationError(f"Unsupported config format: {path.suffix}")
    if not isinstance(data, dict):
        raise ValidationError(f"Config root must be an object: {path}")
    return data

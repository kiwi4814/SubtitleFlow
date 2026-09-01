from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import ValidationError
from .io import read_json, write_json
from .state import invalidate_after_source_or_canon_change
from .util import utc_now
from .workspace import TitlePaths


def _glossary_path(paths: TitlePaths, scope: str) -> Path:
    if scope == "project":
        return paths.project_canon / "glossary.json"
    if scope == "title":
        return paths.title_canon / "glossary.json"
    raise ValidationError("scope must be project or title")


def add_term(
    paths: TitlePaths,
    *,
    scope: str,
    term_id: str,
    canonical: str,
    aliases: list[str],
    auto_replace: bool,
    context_sensitive: bool,
    branches: list[str],
    notes: str | None,
) -> dict[str, Any]:
    if not term_id.strip() or not canonical.strip():
        raise ValidationError("term id and canonical are required")
    invalid_branches = set(branches) - {"clean", "tw", "jp"}
    if invalid_branches:
        raise ValidationError(f"Invalid branch names: {', '.join(sorted(invalid_branches))}")
    if auto_replace and context_sensitive:
        raise ValidationError("A context-sensitive term cannot be marked auto_replace")
    path = _glossary_path(paths, scope)
    data = read_json(path)
    terms = data.setdefault("terms", [])
    if any(item.get("id") == term_id for item in terms):
        raise ValidationError(f"Glossary term already exists: {term_id}")
    item = {
        "id": term_id,
        "canonical": canonical,
        "aliases": aliases,
        "auto_replace": auto_replace,
        "context_sensitive": context_sensitive,
        "branches": branches or ["clean", "tw", "jp"],
        "forbidden_aliases": aliases,
        "notes": notes,
        "created_at": utc_now(),
    }
    terms.append(item)
    write_json(path, data)
    if scope == "project":
        project = read_json(paths.project_config)
        project["canon_version"] = int(project.get("canon_version", 0)) + 1
        project["canon_updated_at"] = utc_now()
        write_json(paths.project_config, project)
        for title_dir in (paths.project / "titles").iterdir():
            state = title_dir / "state.json"
            if title_dir.is_dir() and state.exists():
                other = TitlePaths(paths.repo, paths.project_id, title_dir.name)
                invalidate_after_source_or_canon_change(other, reason="project canon changed")
    else:
        invalidate_after_source_or_canon_change(paths, reason="title canon changed")
    return item

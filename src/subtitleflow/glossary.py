from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .io import read_json
from .models import ChangeRecord
from .workspace import TitlePaths


@dataclass(slots=True)
class TermRule:
    id: str
    canonical: str
    aliases: list[str]
    auto_replace: bool
    context_sensitive: bool
    branches: list[str]
    forbidden_aliases: list[str]
    notes: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TermRule":
        term_id = str(data.get("id", "")).strip()
        canonical = str(data.get("canonical", "")).strip()
        if not term_id or not canonical:
            raise ValidationError("Glossary term requires id and canonical")
        aliases = [str(item).strip() for item in data.get("aliases", []) if str(item).strip()]
        forbidden_aliases = [
            str(item).strip() for item in data.get("forbidden_aliases", aliases) if str(item).strip()
        ]
        return cls(
            id=term_id,
            canonical=canonical,
            aliases=aliases,
            auto_replace=bool(data.get("auto_replace", False)),
            context_sensitive=bool(data.get("context_sensitive", False)),
            branches=[str(item) for item in data.get("branches", ["clean", "tw", "jp"])],
            forbidden_aliases=forbidden_aliases,
            notes=data.get("notes"),
        )


def _load_terms(path: Path) -> list[TermRule]:
    if not path.exists():
        return []
    data = read_json(path)
    return [TermRule.from_dict(item) for item in data.get("terms", [])]


def load_glossary(paths: TitlePaths) -> list[TermRule]:
    by_id: dict[str, TermRule] = {}
    for term in _load_terms(paths.project_canon / "glossary.json"):
        by_id[term.id] = term
    for term in _load_terms(paths.title_canon / "glossary.json"):
        by_id[term.id] = term
    return list(by_id.values())


def apply_glossary(text: str, rules: list[TermRule], branch: str) -> tuple[str, list[ChangeRecord], list[dict[str, str]]]:
    result = text
    changes: list[ChangeRecord] = []
    review_hits: list[dict[str, str]] = []
    candidates: list[tuple[str, TermRule]] = []
    for rule in rules:
        if branch not in rule.branches:
            continue
        for alias in rule.aliases:
            candidates.append((alias, rule))
    candidates.sort(key=lambda item: len(item[0]), reverse=True)

    for alias, rule in candidates:
        if alias not in result or alias == rule.canonical:
            continue
        if rule.auto_replace and not rule.context_sensitive:
            before = result
            result = result.replace(alias, rule.canonical)
            if result != before:
                changes.append(
                    ChangeRecord(
                        kind="terminology",
                        before=alias,
                        after=rule.canonical,
                        rule_id=rule.id,
                        note=rule.notes,
                    )
                )
        else:
            review_hits.append(
                {
                    "term_id": rule.id,
                    "alias": alias,
                    "suggested": rule.canonical,
                    "reason": rule.notes or "Context-sensitive terminology requires review",
                }
            )
    return result, changes, review_hits


def forbidden_hits(text: str, rules: list[TermRule], branch: str) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for rule in rules:
        if branch not in rule.branches:
            continue
        for alias in rule.forbidden_aliases:
            if alias and alias != rule.canonical and alias in text:
                hits.append({"term_id": rule.id, "alias": alias, "canonical": rule.canonical})
    return hits

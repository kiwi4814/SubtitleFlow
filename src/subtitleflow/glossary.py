from __future__ import annotations

from dataclasses import dataclass, field
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
    key: str | None = None
    enforcement: str = "locked"
    accepted_aliases: list[str] = field(default_factory=list)
    deprecated_aliases: list[str] = field(default_factory=list)
    source_forms: list[str] = field(default_factory=list)
    target_language: str | None = None
    origin: str = "local"
    scope: dict[str, Any] = field(default_factory=dict)
    pack_refs: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TermRule":
        term_id = str(data.get("id", "")).strip()
        canonical = str(data.get("canonical", "")).strip()
        if not term_id or not canonical:
            raise ValidationError("Glossary term requires id and canonical")
        aliases = [str(item).strip() for item in data.get("aliases", []) if str(item).strip()]
        forbidden_aliases = [
            str(item).strip()
            for item in data.get("forbidden_aliases", aliases)
            if str(item).strip()
        ]
        enforcement = str(data.get("enforcement", "locked"))
        if enforcement not in {"locked", "preferred", "informational"}:
            raise ValidationError(f"Invalid glossary enforcement: {enforcement}")
        return cls(
            id=term_id,
            canonical=canonical,
            aliases=aliases,
            auto_replace=bool(data.get("auto_replace", False)),
            context_sensitive=bool(data.get("context_sensitive", False)),
            branches=[str(item) for item in data.get("branches", ["clean", "tw", "jp"])],
            forbidden_aliases=forbidden_aliases,
            notes=data.get("notes"),
            key=str(data.get("key") or term_id),
            enforcement=enforcement,
            accepted_aliases=[str(item) for item in data.get("accepted_aliases", [])],
            deprecated_aliases=[str(item) for item in data.get("deprecated_aliases", [])],
            source_forms=[str(item) for item in data.get("source_forms", [])],
            target_language=data.get("target_language"),
            origin=str(data.get("origin", "local")),
            scope=dict(data.get("scope", {})),
            pack_refs=list(data.get("pack_refs", [])),
        )


def _load_terms(path: Path) -> list[TermRule]:
    if not path.exists():
        return []
    data = read_json(path)
    return [TermRule.from_dict(item) for item in data.get("terms", [])]


def load_local_glossary(paths: TitlePaths) -> list[TermRule]:
    by_id: dict[str, TermRule] = {}
    for term in _load_terms(paths.project_canon / "glossary.json"):
        term.origin = "local-project"
        by_id[term.id] = term
    for term in _load_terms(paths.title_canon / "glossary.json"):
        term.origin = "local-title"
        by_id[term.id] = term
    return list(by_id.values())


def _effective_rules(paths: TitlePaths) -> list[TermRule]:
    from .srp.registry import research_mode
    from .srp.resolver import ensure_resolved

    mode = research_mode(paths)
    if mode in {"off", "legacy"}:
        return load_local_glossary(paths)
    ensure_resolved(paths)
    data = read_json(paths.research_effective)
    result: list[TermRule] = []
    for branch, branch_data in data.get("branches", {}).items():
        for item in branch_data.get("terms", []):
            known = [str(value) for value in item.get("known_aliases", []) if str(value)]
            rule = TermRule(
                id=str(item.get("record_id") or item["key"]),
                canonical=str(item["canonical"]),
                aliases=known,
                auto_replace=bool(item.get("auto_replace", False)),
                context_sensitive=bool(item.get("context_sensitive", True)),
                branches=[branch],
                forbidden_aliases=[str(value) for value in item.get("forbidden_aliases", [])],
                notes=item.get("notes"),
                key=str(item["key"]),
                enforcement=str(item.get("enforcement", "informational")),
                accepted_aliases=[str(value) for value in item.get("accepted_aliases", [])],
                deprecated_aliases=[str(value) for value in item.get("deprecated_aliases", [])],
                source_forms=[str(value) for value in item.get("source_forms", [])],
                target_language=item.get("target_language"),
                origin=str(item.get("origin", "srp")),
                scope=dict(item.get("scope", {})),
                pack_refs=list(item.get("pack_refs", [])),
            )
            result.append(rule)
    return result


def load_glossary(paths: TitlePaths) -> list[TermRule]:
    return _effective_rules(paths)


def apply_glossary(
    text: str,
    rules: list[TermRule],
    branch: str,
) -> tuple[str, list[ChangeRecord], list[dict[str, str]]]:
    result = text
    changes: list[ChangeRecord] = []
    review_hits: list[dict[str, str]] = []
    candidates: list[tuple[str, TermRule]] = []
    for rule in rules:
        if branch not in rule.branches:
            continue
        for alias in rule.aliases:
            if alias not in rule.accepted_aliases:
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
                        rule_id=rule.key or rule.id,
                        note=rule.notes,
                    )
                )
        else:
            review_hits.append(
                {
                    "term_id": rule.key or rule.id,
                    "alias": alias,
                    "suggested": rule.canonical,
                    "reason": rule.notes
                    or f"{rule.enforcement} terminology requires contextual review",
                }
            )
    return result, changes, review_hits


def terminology_hits(text: str, rules: list[TermRule], branch: str) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for rule in rules:
        if branch not in rule.branches:
            continue
        categories = (
            ("forbidden", rule.forbidden_aliases),
            ("deprecated", rule.deprecated_aliases),
        )
        seen: set[tuple[str, str]] = set()
        for kind, aliases in categories:
            for alias in aliases:
                if not alias or alias == rule.canonical or alias in rule.accepted_aliases:
                    continue
                marker = (kind, alias)
                if marker in seen or alias not in text:
                    continue
                seen.add(marker)
                hits.append(
                    {
                        "term_id": rule.key or rule.id,
                        "alias": alias,
                        "canonical": rule.canonical,
                        "kind": kind,
                        "enforcement": rule.enforcement,
                        "origin": rule.origin,
                    }
                )
        categorized = set(rule.forbidden_aliases) | set(rule.deprecated_aliases)
        for alias in rule.aliases:
            if (
                alias
                and alias != rule.canonical
                and alias not in rule.accepted_aliases
                and alias not in categorized
                and alias in text
            ):
                hits.append(
                    {
                        "term_id": rule.key or rule.id,
                        "alias": alias,
                        "canonical": rule.canonical,
                        "kind": "noncanonical",
                        "enforcement": rule.enforcement,
                        "origin": rule.origin,
                    }
                )
    return hits


def forbidden_hits(text: str, rules: list[TermRule], branch: str) -> list[dict[str, str]]:
    return [item for item in terminology_hits(text, rules, branch) if item["kind"] == "forbidden"]

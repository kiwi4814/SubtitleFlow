from __future__ import annotations

from typing import Any

from ..io import atomic_write_text
from ..workspace import TitlePaths


def _term_line(term: dict[str, Any]) -> str:
    suffix = f" [{term.get('enforcement', 'informational')}]"
    aliases = term.get("deprecated_aliases", []) + term.get("forbidden_aliases", [])
    alias_text = f"; avoid: {', '.join(aliases)}" if aliases else ""
    return f"- `{term['key']}` → **{term['canonical']}**{suffix}{alias_text}"


def render_context(paths: TitlePaths, effective: dict[str, Any]) -> None:
    paths.research_context.mkdir(parents=True, exist_ok=True)
    summary = [
        f"# Research summary — {paths.project_id}/{paths.title_id}",
        "",
        f"Mode: `{effective.get('mode')}`",
        f"Bindings: {len(effective.get('bindings', []))}",
        f"Blocking conflicts: {effective.get('blocking_conflicts', 0)}",
        f"Blocking unresolved: {effective.get('blocking_unresolved', 0)}",
        "",
    ]
    conflicts = effective.get("conflicts", [])
    if conflicts:
        summary.append("## Conflicts")
        for item in conflicts:
            summary.append(f"- {item.get('kind')}: {item.get('key') or item.get('id')} — {item.get('message')}")
        summary.append("")
    atomic_write_text(paths.research_summary, "\n".join(summary).rstrip() + "\n")

    for branch, data in effective.get("branches", {}).items():
        lines = [
            f"# Effective research context — {branch}",
            "",
            f"SRP branch: `{data.get('srp_branch_id') or 'none'}`",
            "",
        ]
        terms = data.get("terms", [])
        if terms:
            lines.extend(["## Terminology", *[_term_line(item) for item in terms], ""])
        decisions = data.get("decisions", [])
        if decisions:
            lines.append("## Editorial decisions")
            for item in decisions:
                lines.append(
                    f"- `{item['key']}` [{item.get('enforcement', 'informational')}]: "
                    f"{item['directive']}"
                )
            lines.append("")
        facts = data.get("facts", [])
        if facts:
            lines.append("## Facts")
            for item in facts:
                status = item.get("status", "accepted")
                prefix = "[provisional] " if status == "provisional" else ""
                lines.append(f"- {prefix}{item.get('statement')}")
            lines.append("")
        entities = data.get("entities", [])
        if entities:
            lines.append("## Entities")
            for item in entities:
                name = item.get("primary_name", {}).get("text") or item.get("id")
                description = item.get("description")
                lines.append(f"- **{name}**" + (f": {description}" if description else ""))
            lines.append("")
        unresolved = data.get("unresolved", [])
        if unresolved:
            lines.append("## Unresolved")
            for item in unresolved:
                lines.append(f"- [{item.get('severity')}] {item.get('question')}")
            lines.append("")
        atomic_write_text(paths.research_context / f"{branch}.md", "\n".join(lines).rstrip() + "\n")

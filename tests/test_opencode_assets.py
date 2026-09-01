from __future__ import annotations

import json
import re
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"missing frontmatter: {path}"
    _open, block, _body = text.split("---", 2)
    result: dict[str, str] = {}
    for raw in block.splitlines():
        if not raw.strip() or raw.startswith(" ") or ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def test_opencode_v2_config_uses_current_permission_shape() -> None:
    config = json.loads((REPO / "opencode.jsonc").read_text(encoding="utf-8"))
    assert config["default_agent"] == "subtitle-orchestrator"
    assert isinstance(config["permissions"], list)
    text = (REPO / "opencode.jsonc").read_text(encoding="utf-8")
    assert '"permission"' not in text
    assert '"bash"' not in text
    assert '"task"' not in text
    assert any(
        rule == {"action": "edit", "resource": "projects/*/titles/*/source/*", "effect": "deny"}
        for rule in config["permissions"]
    )


def test_opencode_skills_are_discoverable_and_described() -> None:
    skill_dirs = sorted((REPO / ".opencode" / "skills").iterdir())
    assert skill_dirs
    for directory in skill_dirs:
        skill = directory / "SKILL.md"
        assert skill.is_file()
        meta = _frontmatter(skill)
        assert meta.get("description")
        assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", directory.name)


def test_opencode_agents_and_commands_have_required_metadata() -> None:
    for agent in (REPO / ".opencode" / "agents").glob("*.md"):
        meta = _frontmatter(agent)
        assert meta.get("description")
        assert meta.get("mode") in {"primary", "subagent", "all"}
        text = agent.read_text(encoding="utf-8")
        assert "permission:" not in text
    commands = list((REPO / ".opencode" / "commands").rglob("*.md"))
    assert commands
    for command in commands:
        meta = _frontmatter(command)
        assert meta.get("description")
        assert meta.get("agent") == "subtitle-orchestrator"

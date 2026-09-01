from __future__ import annotations

from .errors import GateError, ValidationError
from .io import read_json
from .review import pending_count
from .state import update_stage
from .workspace import TitlePaths


def _require_nonempty_file(path, label: str) -> None:
    if not path.is_file() or not path.read_text(encoding="utf-8", errors="replace").strip():
        raise GateError(f"{label} is missing or empty: {path}")


def mark_research_complete(paths: TitlePaths, *, note: str | None = None) -> None:
    _require_nonempty_file(paths.research / "context.md", "Research context")
    _require_nonempty_file(paths.research / "sources.md", "Research sources")
    update_stage(paths, "research", "passed", note=note)


def mark_semantic_qa_complete(paths: TitlePaths, *, note: str | None = None) -> None:
    if pending_count(paths):
        raise GateError("Semantic QA cannot pass while human review candidates are pending")
    _require_nonempty_file(paths.qa / "semantic-review.md", "Semantic QA report")
    update_stage(paths, "semantic_qa", "passed", note=note)


def mark_visual_qa_complete(paths: TitlePaths, branch: str, *, note: str | None = None) -> None:
    if branch not in {"tw", "jp"}:
        raise ValidationError("branch must be tw or jp")
    state = read_json(paths.state)
    render_stage = state.get("stages", {}).get(f"render_{branch}", {})
    if render_stage.get("status") != "passed":
        raise GateError(f"Visual QA cannot pass before render_{branch} is passed")
    preview_dir = paths.qa / "previews" / branch
    frames = [path for path in preview_dir.glob("*.png") if path.is_file() and path.stat().st_size > 0]
    if not frames:
        raise GateError(f"Visual QA cannot pass: no rendered {branch} preview frames exist")
    update_stage(paths, f"visual_{branch}", "passed", note=note, frames=len(frames))

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .errors import GateError
from .io import read_json
from .review import pending_count, unimported_proposal_files
from .state import state_summary, update_stage
from .util import ffmpeg_has_libass, which
from .workflow import active_branches
from .workspace import TitlePaths, find_repo_root, title_paths


@dataclass(frozen=True, slots=True)
class RuntimeCapabilities:
    ffmpeg: bool
    ffmpeg_libass: bool
    mkvtoolnix: bool
    full_video: bool
    exact_fonts: bool

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProductionPlan:
    project_id: str
    title_id: str
    current: dict[str, Any]
    next_action: str
    reason: str
    requires_human: bool
    can_auto_advance: bool
    command_hint: str | None
    branches: tuple[str, ...]
    deferred: tuple[str, ...]
    capabilities: RuntimeCapabilities

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["branches"] = list(self.branches)
        data["deferred"] = list(self.deferred)
        return data


def detect_runtime_capabilities(
    paths: TitlePaths,
    *,
    full_video: bool | None = None,
    exact_fonts: bool | None = None,
) -> RuntimeCapabilities:
    ffmpeg = bool(which("ffmpeg"))
    libass = ffmpeg and ffmpeg_has_libass()
    mkvtoolnix = bool(which("mkvmerge"))
    config = read_json(paths.title_config)
    configured_video = config.get("media", {}).get("video")
    if full_video is None:
        video_available = bool(configured_video and Path(str(configured_video)).expanduser().is_file())
    else:
        video_available = bool(full_video)

    if exact_fonts is None:
        fonts_stage = read_json(paths.state).get("stages", {}).get("fonts", {})
        fonts_available = fonts_stage.get("status") == "passed"
    else:
        fonts_available = bool(exact_fonts)

    return RuntimeCapabilities(
        ffmpeg=ffmpeg,
        ffmpeg_libass=libass,
        mkvtoolnix=mkvtoolnix,
        full_video=video_available,
        exact_fonts=fonts_available,
    )


def _passed(stages: dict[str, Any], name: str) -> bool:
    return stages.get(name, {}).get("status") == "passed"


def _deferred_checks(capabilities: RuntimeCapabilities) -> tuple[str, ...]:
    deferred: list[str] = []
    if not capabilities.ffmpeg_libass:
        deferred.append("libass-render")
    if not capabilities.exact_fonts:
        deferred.append("exact-font-render")
    if not capabilities.full_video:
        deferred.extend(("full-video-timing-qa", "scene-occlusion-review"))
    if not capabilities.mkvtoolnix:
        deferred.append("mkv-remux-verification")
    return tuple(deferred)


def mark_semantic_scan_complete(paths: TitlePaths, *, note: str | None = None) -> None:
    unimported = unimported_proposal_files(paths)
    if unimported:
        names = ", ".join(path.name for path in unimported)
        raise GateError(
            "Cannot mark semantic scan complete while proposal files are unimported: " + names
        )
    pending = pending_count(paths)
    if pending:
        raise GateError(
            f"Cannot mark semantic scan complete while {pending} review candidate(s) are pending"
        )
    details: dict[str, Any] = {"pending": 0, "semantic_scan_completed": True}
    if note:
        details["note"] = note
    update_stage(paths, "human_review", "passed", **details)


def plan_title(
    paths: TitlePaths,
    *,
    capabilities: RuntimeCapabilities | None = None,
) -> ProductionPlan:
    summary = state_summary(paths)
    stages = summary.get("stages", {})
    branches = tuple(active_branches(paths))
    capabilities = capabilities or detect_runtime_capabilities(paths)
    deferred = _deferred_checks(capabilities)

    if not _passed(stages, "normalize") or not _passed(stages, "alignment_and_seed"):
        return ProductionPlan(
            project_id=paths.project_id,
            title_id=paths.title_id,
            current=summary,
            next_action="prepare",
            reason="normalized workfiles/alignment are not current",
            requires_human=False,
            can_auto_advance=True,
            command_hint=f"subflow prepare {paths.project_id} {paths.title_id}",
            branches=branches,
            deferred=deferred,
            capabilities=capabilities,
        )

    unimported = unimported_proposal_files(paths)
    if unimported:
        names = ", ".join(path.name for path in unimported)
        return ProductionPlan(
            project_id=paths.project_id,
            title_id=paths.title_id,
            current=summary,
            next_action="import-semantic-proposals",
            reason=f"semantic proposal files are waiting to be imported: {names}",
            requires_human=False,
            can_auto_advance=True,
            command_hint=None,
            branches=branches,
            deferred=deferred,
            capabilities=capabilities,
        )

    pending = pending_count(paths)
    if pending:
        return ProductionPlan(
            project_id=paths.project_id,
            title_id=paths.title_id,
            current=summary,
            next_action="human-review",
            reason=f"{pending} semantic change candidate(s) require a decision",
            requires_human=True,
            can_auto_advance=False,
            command_hint=f"subflow review list {paths.project_id} {paths.title_id}",
            branches=branches,
            deferred=deferred,
            capabilities=capabilities,
        )

    if not _passed(stages, "human_review"):
        return ProductionPlan(
            project_id=paths.project_id,
            title_id=paths.title_id,
            current=summary,
            next_action="semantic-edit",
            reason="semantic scan has not been completed for the current prepared workfiles",
            requires_human=False,
            can_auto_advance=True,
            command_hint=None,
            branches=branches,
            deferred=deferred,
            capabilities=capabilities,
        )

    missing_compile = [branch for branch in branches if not _passed(stages, f"compile_{branch}")]
    if missing_compile:
        return ProductionPlan(
            project_id=paths.project_id,
            title_id=paths.title_id,
            current=summary,
            next_action="compile",
            reason="compiled ASS is missing or stale for: " + ", ".join(missing_compile),
            requires_human=False,
            can_auto_advance=True,
            command_hint=f"subflow compile {paths.project_id} {paths.title_id}",
            branches=branches,
            deferred=deferred,
            capabilities=capabilities,
        )

    if not _passed(stages, "qa"):
        return ProductionPlan(
            project_id=paths.project_id,
            title_id=paths.title_id,
            current=summary,
            next_action="qa",
            reason="deterministic QA is missing or stale",
            requires_human=False,
            can_auto_advance=True,
            command_hint=f"subflow qa {paths.project_id} {paths.title_id}",
            branches=branches,
            deferred=deferred,
            capabilities=capabilities,
        )

    config = read_json(paths.title_config)
    gates = config.get("quality_gates", {})
    if gates.get("require_semantic_qa", True) and not _passed(stages, "semantic_qa"):
        return ProductionPlan(
            project_id=paths.project_id,
            title_id=paths.title_id,
            current=summary,
            next_action="semantic-qa",
            reason="semantic QA approval is required for the current evidence snapshot",
            requires_human=True,
            can_auto_advance=False,
            command_hint=None,
            branches=branches,
            deferred=deferred,
            capabilities=capabilities,
        )

    if gates.get("require_visual_qa", True):
        missing_visual = [branch for branch in branches if not _passed(stages, f"visual_{branch}")]
        if missing_visual:
            return ProductionPlan(
                project_id=paths.project_id,
                title_id=paths.title_id,
                current=summary,
                next_action="visual-qa",
                reason="visual approval is required for: " + ", ".join(missing_visual),
                requires_human=True,
                can_auto_advance=False,
                command_hint=None,
                branches=branches,
                deferred=deferred,
                capabilities=capabilities,
            )

    if not _passed(stages, "release"):
        return ProductionPlan(
            project_id=paths.project_id,
            title_id=paths.title_id,
            current=summary,
            next_action="release",
            reason="all configured release gates are satisfied",
            requires_human=False,
            can_auto_advance=True,
            command_hint=f"subflow release {paths.project_id} {paths.title_id}",
            branches=branches,
            deferred=deferred,
            capabilities=capabilities,
        )

    if capabilities.full_video and capabilities.mkvtoolnix and not _passed(stages, "remux"):
        return ProductionPlan(
            project_id=paths.project_id,
            title_id=paths.title_id,
            current=summary,
            next_action="remux",
            reason="subtitle release is frozen and local media tooling is available",
            requires_human=False,
            can_auto_advance=True,
            command_hint=f"subflow remux {paths.project_id} {paths.title_id}",
            branches=branches,
            deferred=deferred,
            capabilities=capabilities,
        )

    return ProductionPlan(
        project_id=paths.project_id,
        title_id=paths.title_id,
        current=summary,
        next_action="complete",
        reason="no further mandatory action is available in this runtime",
        requires_human=False,
        can_auto_advance=False,
        command_hint=None,
        branches=branches,
        deferred=deferred,
        capabilities=capabilities,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan the next safe SubtitleFlow production action")
    parser.add_argument("project")
    parser.add_argument("title")
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args(argv)
    repo = args.repo.resolve() if args.repo else find_repo_root()
    plan = plan_title(title_paths(repo, args.project, args.title))
    print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

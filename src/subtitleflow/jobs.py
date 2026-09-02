from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from .errors import ValidationError
from .io import read_json, write_json
from .normalize import normalize_all
from .pipeline import plan_title
from .state import state_summary
from .workfile import build_all_workfiles
from .workspace import (
    add_source,
    configure_workflow_profile,
    create_project,
    create_title,
    title_paths,
)


@dataclass(frozen=True, slots=True)
class PreparedPortableJob:
    job_id: str
    project_id: str
    title_id: str
    series_id: str
    display_name: str
    workflow_profile: str
    workspace: str
    title_path: str
    imported_sources: dict[str, dict[str, Any]]
    normalized: dict[str, str]
    workfiles: dict[str, str]
    next_plan: dict[str, Any]
    repository_evidence: dict[str, Any]
    state: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _job_schema(source_root: Path) -> dict[str, Any]:
    path = source_root / "contracts" / "subtitle-job.schema.json"
    if not path.is_file():
        raise ValidationError(
            "Portable job contract is missing from source root: "
            f"{path}. Use a SubtitleFlow checkout/snapshot that includes contracts/."
        )
    return read_json(path)


def load_portable_job(path: Path, *, source_root: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ValidationError(f"Portable job file does not exist: {path}")
    data = read_json(path)
    try:
        Draft202012Validator(_job_schema(source_root)).validate(data)
    except JsonSchemaValidationError as exc:
        location = ".".join(str(item) for item in exc.absolute_path)
        where = f" at {location}" if location else ""
        raise ValidationError(f"Invalid portable job{where}: {exc.message}") from exc
    return data


def _role_inputs(job: dict[str, Any], *, source_root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    missing_role_hints: list[str] = []
    for raw in job.get("inputs", []):
        role = raw.get("role_hint")
        path_value = str(raw.get("path", ""))
        if role is None:
            missing_role_hints.append(path_value)
            continue
        role = str(role).upper()
        if role in result:
            raise ValidationError(f"Portable job contains duplicate role_hint {role}")
        source = Path(path_value).expanduser()
        if not source.is_absolute():
            source = source_root / source
        source = source.resolve()
        if not source.is_file():
            raise ValidationError(f"Portable job input does not exist: {source}")
        result[role] = source
    if missing_role_hints:
        raise ValidationError(
            "Deterministic portable prepare requires role_hint after adapter classification; "
            "missing for: " + ", ".join(missing_role_hints)
        )
    return result


def infer_workflow_profile(job: dict[str, Any]) -> str:
    roles = {
        str(item.get("role_hint")).upper()
        for item in job.get("inputs", [])
        if item.get("role_hint") is not None
    }
    intent = str(job.get("intent", "auto"))

    if "S" in roles:
        return "source-assisted" if "C" in roles else "single"
    if {"A", "D"}.issubset(roles) or intent == "tw-dub-zh-cn":
        return "dub"
    if {"A", "B", "C"}.issubset(roles) or intent == "jp-audio-zh-cn-ja":
        return "bilingual"
    return "auto"


def _configure_title_from_job(paths, job: dict[str, Any], profile: str) -> None:
    config = read_json(paths.title_config)
    configure_workflow_profile(config, profile)
    requirements = job.get("requirements", {})
    if isinstance(requirements, dict):
        editing_policy = requirements.get("editing_policy")
        if editing_policy is not None:
            config.setdefault("editorial", {})["editing_policy"] = str(editing_policy)
        style_profile = requirements.get("style_profile")
        if style_profile:
            config.setdefault("style", {})["profile"] = str(style_profile)
    write_json(paths.title_config, config)


def prepare_portable_job(
    job_path: Path,
    *,
    workspace: Path,
    source_root: Path,
    allow_no_opencc: bool = False,
) -> PreparedPortableJob:
    """Materialize a portable job through deterministic SubtitleFlow prepare.

    This intentionally stops after prepare. Semantic editing, Human Review, QA, rendering,
    release, and Remux remain owned by the existing state machine and ``plan_title``.
    Runtime adapters should call this function, inspect ``next_plan``, and continue through
    existing gates rather than reimplementing stage transitions.
    """
    source_root = source_root.expanduser().resolve()
    workspace = workspace.expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    job = load_portable_job(job_path, source_root=source_root)
    role_inputs = _role_inputs(job, source_root=source_root)

    project_id = str(job.get("project_id") or "portable")
    title_id = str(job.get("title_id") or job.get("job_id") or "title")
    series_id = str(job.get("series_id") or project_id)
    display_name = str(job.get("display_name") or title_id)
    job_id = str(job.get("job_id") or f"{project_id}-{title_id}")
    profile = infer_workflow_profile(job)

    project_path = workspace / "projects" / project_id
    if not project_path.exists():
        create_project(workspace, project_id, project_id)

    paths = title_paths(workspace, project_id, title_id)
    if paths.title.exists():
        raise ValidationError(
            "Portable job target title already exists in workspace: "
            f"{paths.title}. Use a fresh workspace or resume it through the planner instead."
        )
    create_title(
        workspace,
        project_id,
        title_id,
        display_name,
        series_id=series_id,
    )
    _configure_title_from_job(paths, job, profile)

    imported: dict[str, dict[str, Any]] = {}
    for role, source in sorted(role_inputs.items()):
        imported[role] = add_source(paths, role, source)

    normalized = normalize_all(paths)
    workfiles = build_all_workfiles(paths, allow_no_opencc=allow_no_opencc)
    plan = plan_title(paths).to_dict()
    requirements = job.get("requirements", {})
    use_repository_evidence = bool(
        requirements.get("use_repository_evidence", True)
        if isinstance(requirements, dict)
        else True
    )

    return PreparedPortableJob(
        job_id=job_id,
        project_id=paths.project_id,
        title_id=paths.title_id,
        series_id=series_id,
        display_name=display_name,
        workflow_profile=profile,
        workspace=str(workspace),
        title_path=str(paths.title),
        imported_sources=imported,
        normalized=normalized,
        workfiles=workfiles,
        next_plan=plan,
        repository_evidence={
            "requested": use_repository_evidence,
            "bound": False,
            "reason": (
                "Portable prepare materializes subtitle inputs only. Canon/SRP resolution is an "
                "adapter step and must be bound explicitly before semantic decisions."
                if use_repository_evidence
                else "Repository evidence was disabled by the job."
            ),
        },
        state=state_summary(paths),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a portable SubtitleFlow job")
    parser.add_argument("job", type=Path)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--allow-no-opencc", action="store_true")
    args = parser.parse_args(argv)
    result = prepare_portable_job(
        args.job,
        workspace=args.workspace,
        source_root=args.source_root,
        allow_no_opencc=args.allow_no_opencc,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

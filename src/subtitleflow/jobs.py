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
from .srp.archive import import_pack
from .srp.registry import bind_pack, map_branch, set_mode
from .srp.resolver import approve_research, resolve_research
from .srp.validate import validate_pack_dir
from .state import state_summary
from .workfile import build_all_workfiles
from .workflow import active_branches
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
    normalized: dict[str, Any]
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


def _repository_config(job: dict[str, Any]) -> dict[str, Any]:
    raw = job.get("repository", {})
    return dict(raw) if isinstance(raw, dict) else {}


def _requirements(job: dict[str, Any]) -> dict[str, Any]:
    raw = job.get("requirements", {})
    return dict(raw) if isinstance(raw, dict) else {}


def _repository_evidence_requested(job: dict[str, Any]) -> bool:
    return bool(_requirements(job).get("use_repository_evidence", True))


def _resolve_research_pack_path(job: dict[str, Any], *, source_root: Path) -> Path:
    repository = _repository_config(job)
    configured = repository.get("research_pack_path")
    if not isinstance(configured, str) or not configured.strip():
        raise ValidationError(
            "use_repository_evidence=true requires repository.research_pack_path after the "
            "runtime adapter selects a compatible immutable Canon/SRP snapshot"
        )
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = source_root / path
    path = path.resolve()
    if not path.is_dir():
        raise ValidationError(f"Pinned repository research pack does not exist: {path}")
    return path


def _branch_score(branch_id: str, *, intent: str, internal_branch: str) -> int:
    value = branch_id.casefold().replace("_", "-")
    tw_intent = internal_branch == "tw" or intent == "tw-dub-zh-cn"
    if tw_intent:
        score = 0
        score += 8 if "tw-dub" in value else -8
        score += 5 if "faithful" in value else 0
        score += 4 if "zh-hans" in value or "zh-cn" in value else 0
        score -= 4 if "candidate" in value else 0
        return score

    jp_intent = internal_branch in {"clean", "jp"} or intent in {
        "jp-audio-zh-cn",
        "jp-audio-zh-cn-ja",
        "polish-existing",
    }
    if jp_intent:
        score = 0
        score += 8 if "jp-audio" in value else -8
        score += 6 if "zh-cn" in value else 0
        score += 4 if "zh-hans" in value else 0
        score -= 7 if "zh-tw" in value else 0
        score += 1 if "modern" in value else 0
        score -= 4 if "candidate" in value else 0
        return score
    return 0


def select_srp_branch_id(
    branch_ids: list[str],
    *,
    intent: str,
    internal_branch: str,
) -> str:
    if not branch_ids:
        raise ValidationError("Pinned SRP does not declare any branch ids")
    scored = sorted(
        (
            (_branch_score(item, intent=intent, internal_branch=internal_branch), item)
            for item in branch_ids
        ),
        key=lambda item: (-item[0], item[1]),
    )
    best_score, best = scored[0]
    if best_score <= 0:
        raise ValidationError(
            f"No SRP branch is compatible with portable intent {intent!r} / {internal_branch!r}"
        )
    ties = [item for score, item in scored if score == best_score]
    if len(ties) != 1:
        raise ValidationError(
            "Pinned SRP branch selection is ambiguous for "
            f"{intent!r} / {internal_branch!r}: {', '.join(ties)}"
        )
    return best


def _bind_repository_research(
    paths,
    job: dict[str, Any],
    *,
    source_root: Path,
) -> dict[str, Any]:
    if not _repository_evidence_requested(job):
        return {
            "requested": False,
            "bound": False,
            "reason": "Repository evidence was disabled by the job.",
        }

    pack_path = _resolve_research_pack_path(job, source_root=source_root)
    validated = validate_pack_dir(pack_path)
    manifest = validated.manifest
    scope = manifest.get("scope", {})
    pack_series_id = scope.get("series_id") if isinstance(scope, dict) else None
    config = read_json(paths.title_config)
    title_series_id = str(config.get("series_id") or paths.project_id)
    if pack_series_id != title_series_id:
        raise ValidationError(
            "Pinned SRP series_id is incompatible with the portable title: "
            f"title uses {title_series_id}, pack uses {pack_series_id}"
        )

    imported = import_pack(paths, pack_path)
    pack_ref = f"{imported['pack_id']}@{imported['pack_version']}#{imported['pack_digest']}"
    set_mode(paths, "enforce")

    languages = manifest.get("languages", {})
    declared_branches = (
        [str(item) for item in languages.get("branches", [])]
        if isinstance(languages, dict)
        else []
    )
    mapping: dict[str, str] = {}
    intent = str(job.get("intent", "auto"))
    for internal_branch in active_branches(paths):
        srp_branch_id = select_srp_branch_id(
            declared_branches,
            intent=intent,
            internal_branch=internal_branch,
        )
        map_branch(paths, internal_branch, srp_branch_id)
        mapping[internal_branch] = srp_branch_id

    binding = bind_pack(paths, pack_ref)
    snapshot = resolve_research(paths)
    approval = approve_research(paths, note="portable job pinned repository SRP")
    repository = _repository_config(job)
    return {
        "requested": True,
        "bound": True,
        "repository": repository.get("full_name", "kiwi4814/SubtitleFlow"),
        "ref": repository.get("ref"),
        "commit_sha": repository.get("commit_sha"),
        "source_pack_path": str(pack_path),
        "pack_id": imported["pack_id"],
        "pack_version": imported["pack_version"],
        "pack_digest": imported["pack_digest"],
        "series_id": pack_series_id,
        "branch_map": mapping,
        "binding": binding,
        "snapshot": snapshot,
        "approval": approval,
    }


def prepare_portable_job(
    job_path: Path,
    *,
    workspace: Path,
    source_root: Path,
    allow_no_opencc: bool = False,
) -> PreparedPortableJob:
    """Materialize a portable job through deterministic SubtitleFlow prepare.

    A pinned repository SRP is imported, bound, resolved, and approved before prepare when the
    job requires repository evidence. Semantic editing, Human Review, QA, rendering, release,
    and Remux remain owned by the existing state machine and ``plan_title``.
    """
    source_root = source_root.expanduser().resolve()
    workspace = workspace.expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    job = load_portable_job(job_path, source_root=source_root)
    role_inputs = _role_inputs(job, source_root=source_root)

    requested_project_id = str(job.get("project_id") or "portable")
    requested_title_id = str(job.get("title_id") or job.get("job_id") or "title")
    requested_series_id = str(job.get("series_id") or requested_project_id)
    display_name = str(job.get("display_name") or requested_title_id)
    job_id = str(job.get("job_id") or f"{requested_project_id}-{requested_title_id}")
    profile = infer_workflow_profile(job)

    paths = title_paths(workspace, requested_project_id, requested_title_id)
    if not paths.project.exists():
        create_project(workspace, requested_project_id, requested_project_id)
    if paths.title.exists():
        raise ValidationError(
            "Portable job target title already exists in workspace: "
            f"{paths.title}. Use a fresh workspace or resume it through the planner instead."
        )
    create_title(
        workspace,
        requested_project_id,
        requested_title_id,
        display_name,
        series_id=requested_series_id,
    )
    _configure_title_from_job(paths, job, profile)
    persisted_config = read_json(paths.title_config)
    persisted_series_id = str(persisted_config.get("series_id") or paths.project_id)

    imported: dict[str, dict[str, Any]] = {}
    for role, source in sorted(role_inputs.items()):
        imported[role] = add_source(paths, role, source)

    repository_evidence = _bind_repository_research(paths, job, source_root=source_root)
    normalized = normalize_all(paths)
    workfiles = build_all_workfiles(paths, allow_no_opencc=allow_no_opencc)
    plan = plan_title(paths).to_dict()

    return PreparedPortableJob(
        job_id=job_id,
        project_id=paths.project_id,
        title_id=paths.title_id,
        series_id=persisted_series_id,
        display_name=display_name,
        workflow_profile=profile,
        workspace=str(workspace),
        title_path=str(paths.title),
        imported_sources=imported,
        normalized=normalized,
        workfiles=workfiles,
        next_plan=plan,
        repository_evidence=repository_evidence,
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

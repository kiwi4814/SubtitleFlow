from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import SourceIntegrityError, SubtitleFlowError, ValidationError
from .io import read_json, write_json
from .util import sha256_file, slugify, utc_now

SCHEMA_VERSION = 1
VALID_ROLES = {"A", "B", "C", "D", "S"}


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and (candidate / "projects").exists():
            return candidate
    raise SubtitleFlowError(
        "Could not find SubtitleFlow repository root. Run inside the cloned/unzipped project."
    )


@dataclass(frozen=True, slots=True)
class TitlePaths:
    repo: Path
    project_id: str
    title_id: str

    @property
    def project(self) -> Path:
        return self.repo / "projects" / self.project_id

    @property
    def title(self) -> Path:
        return self.project / "titles" / self.title_id

    @property
    def project_config(self) -> Path:
        return self.project / "project.json"

    @property
    def title_config(self) -> Path:
        return self.title / "title.json"

    @property
    def source(self) -> Path:
        return self.title / "source"

    @property
    def manifest(self) -> Path:
        return self.source / "manifest.json"

    @property
    def normalized(self) -> Path:
        return self.title / "normalized"

    @property
    def work(self) -> Path:
        return self.title / "work"

    @property
    def research(self) -> Path:
        return self.title / "research"

    @property
    def review(self) -> Path:
        return self.title / "review"

    @property
    def review_proposals(self) -> Path:
        return self.review / "proposals"

    @property
    def release(self) -> Path:
        return self.title / "release"

    @property
    def qa(self) -> Path:
        return self.title / "qa"

    @property
    def state(self) -> Path:
        return self.title / "state.json"

    @property
    def project_canon(self) -> Path:
        return self.project / "canon"

    @property
    def title_canon(self) -> Path:
        return self.title / "canon"


def title_paths(repo: Path, project_id: str, title_id: str) -> TitlePaths:
    return TitlePaths(repo=repo, project_id=slugify(project_id), title_id=slugify(title_id))


def create_project(repo: Path, project_id: str, display_name: str) -> Path:
    project_id = slugify(project_id)
    root = repo / "projects" / project_id
    if root.exists():
        raise SubtitleFlowError(f"Project already exists: {project_id}")
    (root / "canon" / "proposals").mkdir(parents=True, exist_ok=False)
    (root / "titles").mkdir()
    write_json(
        root / "project.json",
        {
            "schema_version": SCHEMA_VERSION,
            "project_id": project_id,
            "display_name": display_name,
            "created_at": utc_now(),
            "canon_version": 1,
            "defaults": {
                "target_locale": "zh-CN",
                "source_locale": "ja-JP",
                "minimal_editorial_intervention": True,
            },
        },
    )
    write_json(root / "canon" / "glossary.json", {"schema_version": 1, "terms": []})
    write_json(root / "canon" / "characters.json", {"schema_version": 1, "characters": []})
    write_json(root / "canon" / "decisions.json", {"schema_version": 1, "decisions": []})
    return root


def default_title_config(project_id: str, title_id: str, display_name: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "title_id": title_id,
        "display_name": display_name,
        "created_at": utc_now(),
        "workflow": {"profile": "auto"},
        "sources": {"A": None, "B": None, "C": None, "D": None, "S": None},
        "alignment": {
            "max_group": 3,
            "unmatched_penalty": 3.0,
            "review_confidence_below": 0.72,
        },
        "clean_branch": {
            "enabled": True,
            "language_source": "S",
            "timing_source": "S",
            "source_evidence": "C",
            "source_assisted": "auto",
            "traditional_to_simplified": False,
            "opencc_profile": "t2s",
        },
        "tw_branch": {
            "enabled": True,
            "language_source": "D",
            "timing_source": "A",
            "traditional_to_simplified": True,
            "opencc_profile": "t2s",
        },
        "jp_branch": {
            "enabled": True,
            "translation_source": "B",
            "japanese_source": "C",
            "timing_source": "A",
        },
        "style": {
            "profile": "kiwi-collector-v1",
            "mode": "hybrid",
            "overrides": {},
        },
        "ass": {
            "single_line_preferred": True,
            "max_visual_rows_warning": 4,
        },
        "fonts": {
            "attach_to_mkv": True,
            "require_for_release": True,
            "require_all_referenced": True,
            "directories": ["fonts/local"],
            "map_file": "fonts/font-map.json",
            "aliases": {},
        },
        "media": {
            "video": None,
            "output_mkv": None,
            "preserve_existing_tracks": True,
            "preserve_existing_attachments": True,
        },
        "release_names": {
            "clean": "简体中文｜精校",
            "tw": "简体中文｜台配",
            "jp": "简日双语｜日配",
        },
        "quality_gates": {
            "require_research": True,
            "require_semantic_qa": True,
            "require_visual_qa": True,
            "require_fonts": True,
        },
    }


def configure_workflow_profile(config: dict[str, Any], profile: str) -> dict[str, Any]:
    profile = profile.strip().lower()
    allowed = {"auto", "full", "single", "source-assisted", "dub", "bilingual"}
    if profile not in allowed:
        raise ValidationError(f"Unknown workflow profile {profile}; expected one of {', '.join(sorted(allowed))}")
    config.setdefault("workflow", {})["profile"] = profile
    return config


def create_title(repo: Path, project_id: str, title_id: str, display_name: str) -> Path:
    paths = title_paths(repo, project_id, title_id)
    if not paths.project.exists():
        raise SubtitleFlowError(f"Project does not exist: {paths.project_id}")
    if paths.title.exists():
        raise SubtitleFlowError(f"Title already exists: {paths.title_id}")
    for directory in (
        paths.source,
        paths.normalized,
        paths.work,
        paths.research,
        paths.review_proposals,
        paths.release,
        paths.qa,
        paths.title_canon,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    write_json(paths.title_config, default_title_config(paths.project_id, paths.title_id, display_name))
    write_json(paths.manifest, {"schema_version": 1, "sources": {}, "history": []})
    write_json(paths.title_canon / "glossary.json", {"schema_version": 1, "terms": []})
    write_json(paths.review / "candidates.json", {"schema_version": 1, "candidates": []})
    write_json(
        paths.state,
        {
            "schema_version": 1,
            "project_id": paths.project_id,
            "title_id": paths.title_id,
            "updated_at": utc_now(),
            "stages": {},
        },
    )
    return paths.title


def _make_read_only(path: Path) -> None:
    try:
        mode = path.stat().st_mode
        path.chmod(mode & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH)
    except OSError:
        # Hash verification remains authoritative; chmod is best-effort cross-platform defense.
        pass


def _make_writable(path: Path) -> None:
    try:
        path.chmod(path.stat().st_mode | stat.S_IWUSR)
    except OSError:
        pass


def add_source(
    paths: TitlePaths,
    role: str,
    source_path: Path,
    *,
    replace: bool = False,
) -> dict[str, Any]:
    role = role.upper()
    if role not in VALID_ROLES:
        raise ValidationError(f"Invalid source role {role}; expected A/B/C/D/S")
    source_path = source_path.expanduser().resolve()
    if not source_path.is_file():
        raise ValidationError(f"Source is not a file: {source_path}")
    if source_path.suffix.lower() not in {".ass", ".ssa", ".srt"}:
        raise ValidationError("Subtitle source must be ASS/SSA/SRT")

    manifest = read_json(paths.manifest)
    sources = manifest.setdefault("sources", {})
    existing = sources.get(role)
    if existing and not replace:
        raise SubtitleFlowError(f"Role {role} already imported; use --replace explicitly")

    if existing:
        old_path = paths.title / existing["path"]
        if old_path.exists():
            _make_writable(old_path)
            archive = paths.source / "_archive" / utc_now().replace(":", "-")
            archive.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_path), archive / old_path.name)
        manifest.setdefault("history", []).append({"role": role, "replaced": existing, "at": utc_now()})

    dest = paths.source / f"{role}{source_path.suffix.lower()}"
    shutil.copy2(source_path, dest)
    digest = sha256_file(dest)
    record = {
        "role": role,
        "path": str(dest.relative_to(paths.title)).replace(os.sep, "/"),
        "original_name": source_path.name,
        "sha256": digest,
        "size": dest.stat().st_size,
        "imported_at": utc_now(),
    }
    sources[role] = record
    write_json(paths.manifest, manifest)

    config = read_json(paths.title_config)
    config["sources"][role] = record["path"]
    write_json(paths.title_config, config)
    _make_read_only(dest)
    from .state import invalidate_after_source_or_canon_change

    invalidate_after_source_or_canon_change(paths, reason=f"source role {role} imported or replaced")
    return record


def verify_sources(paths: TitlePaths, roles: set[str] | None = None) -> dict[str, Any]:
    manifest = read_json(paths.manifest)
    results: list[dict[str, Any]] = []
    failed = False
    for role, record in sorted(manifest.get("sources", {}).items()):
        if roles and role not in roles:
            continue
        path = paths.title / record["path"]
        if not path.exists():
            results.append({"role": role, "status": "missing", "path": str(path)})
            failed = True
            continue
        actual = sha256_file(path)
        status = "ok" if actual == record["sha256"] else "modified"
        results.append(
            {
                "role": role,
                "status": status,
                "expected": record["sha256"],
                "actual": actual,
                "path": str(path),
            }
        )
        if status != "ok":
            failed = True
    report = {"ok": not failed, "results": results, "checked_at": utc_now()}
    if failed:
        raise SourceIntegrityError("One or more immutable source files changed; see source manifest")
    return report


def require_roles(paths: TitlePaths, roles: set[str]) -> dict[str, dict[str, Any]]:
    manifest = read_json(paths.manifest)
    sources = manifest.get("sources", {})
    missing = sorted(role for role in roles if role not in sources)
    if missing:
        raise ValidationError(f"Missing required source roles: {', '.join(missing)}")
    return {role: sources[role] for role in roles}

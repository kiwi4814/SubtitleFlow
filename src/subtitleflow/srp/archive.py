from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path, PurePosixPath

from ..errors import ValidationError
from ..io import read_json, write_json
from ..util import sha256_file, utc_now
from ..workspace import TitlePaths
from .schema import NORMATIVE_FILES
from .validate import ValidatedPack, validate_pack_dir

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 10_000
COPY_FILES = set(NORMATIVE_FILES) | {"README.md"}


def _safe_member_path(name: str) -> PurePosixPath:
    if "\\" in name:
        raise ValidationError(f"Unsafe SRP ZIP member path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValidationError(f"Unsafe SRP ZIP member path: {name!r}")
    return path


def _zip_member_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return bool(mode and stat.S_ISLNK(mode))


def _locate_pack_root(root: Path) -> Path:
    if (root / "manifest.json").is_file():
        return root
    manifests = list(root.glob("*/manifest.json"))
    if len(manifests) == 1:
        return manifests[0].parent
    raise ValidationError(
        "SRP input must contain manifest.json at the root or inside exactly one top-level directory"
    )


@contextmanager
def materialize_pack_input(input_path: Path) -> Iterator[tuple[Path, str | None]]:
    input_path = input_path.expanduser().resolve()
    if input_path.is_dir():
        for path in input_path.rglob("*"):
            if path.is_symlink():
                raise ValidationError(f"SRP directory contains a symlink: {path}")
        yield _locate_pack_root(input_path), None
        return
    if not input_path.is_file():
        raise ValidationError(f"SRP input does not exist: {input_path}")
    if not zipfile.is_zipfile(input_path):
        raise ValidationError("SRP input must be a directory or ZIP archive")

    archive_sha256 = sha256_file(input_path)
    with tempfile.TemporaryDirectory(prefix="subflow-srp-") as temp_name:
        temp = Path(temp_name)
        total = 0
        with zipfile.ZipFile(input_path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ARCHIVE_MEMBERS:
                raise ValidationError(
                    f"SRP ZIP has too many members: {len(infos)} > {MAX_ARCHIVE_MEMBERS}"
                )
            for info in infos:
                member = _safe_member_path(info.filename)
                if _zip_member_is_symlink(info):
                    raise ValidationError(f"SRP ZIP symlink is not allowed: {info.filename}")
                total += int(info.file_size)
                if total > MAX_ARCHIVE_BYTES:
                    raise ValidationError(
                        f"SRP ZIP expands beyond the {MAX_ARCHIVE_BYTES}-byte safety limit"
                    )
                target = temp.joinpath(*member.parts)
                resolved_parent = target.parent.resolve()
                if temp.resolve() not in (resolved_parent, *resolved_parent.parents):
                    raise ValidationError(f"Unsafe SRP ZIP member path: {info.filename!r}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
        yield _locate_pack_root(temp), archive_sha256


def compute_pack_digest(pack_root: Path) -> str:
    entries: list[dict[str, str | int]] = []
    for filename in NORMATIVE_FILES:
        path = pack_root / filename
        if not path.is_file():
            continue
        entries.append(
            {
                "path": filename,
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    payload = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _make_tree_read_only(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        if not path.is_file():
            continue
        with suppress(OSError):
            path.chmod(path.stat().st_mode & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH)


def _ensure_project_research(paths: TitlePaths) -> None:
    paths.project_research_packs.mkdir(parents=True, exist_ok=True)
    if not paths.project_research_registry.exists():
        write_json(paths.project_research_registry, {"schema_version": 1, "packs": []})


def _registry_entry(
    validated: ValidatedPack,
    *,
    digest: str,
    archive_sha256: str | None,
    relative_path: str,
) -> dict[str, object]:
    return {
        "pack_id": validated.manifest["pack_id"],
        "pack_version": validated.manifest["pack_version"],
        "pack_digest": digest,
        "archive_sha256": archive_sha256,
        "scope": validated.manifest["scope"],
        "path": relative_path,
        "counts": validated.counts,
        "imported_at": utc_now(),
    }


def import_pack(paths: TitlePaths, input_path: Path, *, dry_run: bool = False) -> dict[str, object]:
    _ensure_project_research(paths)
    with materialize_pack_input(input_path) as (pack_root, archive_sha256):
        validated = validate_pack_dir(pack_root)
        digest = compute_pack_digest(pack_root)
        digest_hex = digest.split(":", 1)[1]
        destination_root = (
            paths.project_research_packs
            / validated.manifest["pack_id"]
            / validated.manifest["pack_version"]
            / digest_hex
        )
        destination_pack = destination_root / "pack"
        relative_path = str(destination_pack.relative_to(paths.project))

        registry = read_json(paths.project_research_registry)
        existing = next(
            (
                item
                for item in registry.get("packs", [])
                if item.get("pack_id") == validated.manifest["pack_id"]
                and item.get("pack_version") == validated.manifest["pack_version"]
                and item.get("pack_digest") == digest
            ),
            None,
        )
        summary: dict[str, object] = {
            "ok": True,
            "dry_run": dry_run,
            "pack_id": validated.manifest["pack_id"],
            "pack_version": validated.manifest["pack_version"],
            "pack_digest": digest,
            "archive_sha256": archive_sha256,
            "scope": validated.manifest["scope"],
            "counts": validated.counts,
            "already_imported": existing is not None,
            "destination": relative_path,
        }
        if dry_run or existing is not None:
            return summary

        destination_root.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".import-", dir=destination_root.parent
        ) as temp_name:
            temp_root = Path(temp_name)
            temp_pack = temp_root / "pack"
            temp_pack.mkdir(parents=True)
            for filename in sorted(COPY_FILES):
                source = pack_root / filename
                if source.is_file():
                    shutil.copy2(source, temp_pack / filename)
            copied_digest = compute_pack_digest(temp_pack)
            if copied_digest != digest:
                raise ValidationError("SRP import copy verification failed: pack digest changed")
            import_record = _registry_entry(
                validated,
                digest=digest,
                archive_sha256=archive_sha256,
                relative_path=relative_path,
            )
            write_json(temp_root / "import.json", import_record)
            if destination_root.exists():
                raise ValidationError(
                    f"SRP immutable destination already exists: {destination_root}"
                )
            os.replace(temp_root, destination_root)

        _make_tree_read_only(destination_root)
        registry.setdefault("packs", []).append(
            _registry_entry(
                validated,
                digest=digest,
                archive_sha256=archive_sha256,
                relative_path=relative_path,
            )
        )
        registry["packs"] = sorted(
            registry["packs"],
            key=lambda item: (
                str(item.get("pack_id")),
                str(item.get("pack_version")),
                str(item.get("pack_digest")),
            ),
        )
        write_json(paths.project_research_registry, registry)
        return summary

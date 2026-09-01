from __future__ import annotations

from pathlib import Path
from typing import Any

from .formats import parse_subtitle
from .io import read_json, write_json
from .models import NormalizedSubtitle
from .state import update_stage
from .util import sha256_file
from .workspace import TitlePaths, require_roles, verify_sources


def normalize_role(paths: TitlePaths, role: str) -> Path:
    role = role.upper()
    sources = require_roles(paths, {role})
    verify_sources(paths, {role})
    record = sources[role]
    source_path = paths.title / record["path"]
    cues, metadata = parse_subtitle(source_path)
    # A source style name is classification evidence only: generic names such as Style2 stay
    # dialogue. Once an event is semantically classified as authored non-dialogue material,
    # however, hybrid mode preserves it without inventing a new position. Text-classified
    # translator/fansub credits remain excluded even if their style looks special.
    authored_roles = {
        "annotation",
        "screen-text",
        "title",
        "episode-title",
        "next-episode-title",
        "document",
        "prop",
    }
    for cue in cues:
        if cue.include_in_release and cue.semantic_role in authored_roles and not cue.protected:
            cue.protected = True
            cue.protected_reason = f"hybrid-preserved source style ({cue.semantic_role})"

    normalized = NormalizedSubtitle(
        schema_version=1,
        role=role,  # type: ignore[arg-type]
        source_file=record["path"],
        source_sha256=sha256_file(source_path),
        format=source_path.suffix.lower().lstrip("."),
        encoding=str(metadata.get("ass", {}).get("encoding", "auto"))
        if isinstance(metadata.get("ass"), dict)
        else "auto",
        cues=cues,
        protected_count=sum(cue.protected for cue in cues),
        metadata=metadata,
    )
    output = paths.normalized / f"{role}.json"
    write_json(output, normalized.to_dict())
    return output


def normalize_all(paths: TitlePaths) -> dict[str, Any]:
    manifest = read_json(paths.manifest)
    roles = sorted(manifest.get("sources", {}).keys())
    outputs = {role: str(normalize_role(paths, role).relative_to(paths.title)) for role in roles}
    update_stage(paths, "normalize", "passed", roles=roles, outputs=outputs)
    return {"roles": roles, "outputs": outputs}


def load_normalized(paths: TitlePaths, role: str) -> NormalizedSubtitle:
    data = read_json(paths.normalized / f"{role.upper()}.json")
    return NormalizedSubtitle.from_dict(data)

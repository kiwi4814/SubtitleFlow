from __future__ import annotations

from pathlib import Path
from typing import Any

from .formats import parse_subtitle
from .io import read_json, write_json
from .models import NormalizedSubtitle
from .state import update_stage
from .style import is_special_source_style
from .util import sha256_file
from .workspace import TitlePaths, require_roles, verify_sources


def normalize_role(paths: TitlePaths, role: str) -> Path:
    role = role.upper()
    sources = require_roles(paths, {role})
    verify_sources(paths, {role})
    record = sources[role]
    source_path = paths.title / record["path"]
    cues, metadata = parse_subtitle(source_path)
    if source_path.suffix.lower() in {".ass", ".ssa"}:
        for cue in cues:
            if not cue.protected and is_special_source_style(paths, cue.style):
                cue.protected = True
                cue.protected_reason = f"hybrid-preserved source style: {cue.style}"
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

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .errors import GateError, ValidationError
from .io import read_json
from .review import import_proposals
from .semantic_packet import semantic_packet_fingerprint
from .workspace import find_repo_root, title_paths

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def validate_semantic_proposal_envelope(paths, proposal_path: Path) -> dict[str, Any]:
    """Validate a portable AI proposal envelope against the current semantic-pass identity."""
    proposal_path = proposal_path.expanduser().resolve()
    if not proposal_path.is_file():
        raise ValidationError(f"Semantic proposal envelope does not exist: {proposal_path}")
    raw = read_json(proposal_path)
    if not isinstance(raw, dict):
        raise ValidationError("Semantic proposal envelope must be a JSON object")
    if raw.get("schema_version") != 1:
        raise ValidationError("Semantic proposal envelope schema_version must be 1")
    if raw.get("kind") != "subtitleflow-semantic-proposals":
        raise ValidationError(
            "Semantic proposal envelope kind must be subtitleflow-semantic-proposals"
        )

    project_id = str(raw.get("project_id", ""))
    title_id = str(raw.get("title_id", ""))
    branch = str(raw.get("branch", ""))
    if project_id != paths.project_id or title_id != paths.title_id:
        raise GateError(
            "Semantic proposal envelope targets a different title: "
            f"{project_id}/{title_id} != {paths.project_id}/{paths.title_id}"
        )
    if branch not in {"clean", "tw", "jp"}:
        raise ValidationError(f"Unknown semantic proposal branch: {branch!r}")

    packet_input_sha256 = str(raw.get("packet_input_sha256", ""))
    if not _SHA256_RE.fullmatch(packet_input_sha256):
        raise ValidationError("packet_input_sha256 must be a lowercase 64-character SHA-256")
    current = semantic_packet_fingerprint(paths, branch)
    if packet_input_sha256 != current:
        raise GateError(
            "Stale semantic proposal envelope: packet_input_sha256 no longer matches the "
            "current workfile/source/editorial/research snapshot. Export a new Semantic Packet "
            "and rerun the semantic pass."
        )

    candidates = raw.get("candidates")
    if not isinstance(candidates, list):
        raise ValidationError("Semantic proposal envelope candidates must be a list")
    for index, item in enumerate(candidates):
        if not isinstance(item, dict):
            raise ValidationError(f"Semantic proposal candidate {index} must be an object")
        if str(item.get("branch", "")) != branch:
            raise ValidationError(
                f"Semantic proposal candidate {index} branch does not match envelope branch {branch}"
            )
        for key in (
            "unit_id",
            "original_text",
            "proposed_text",
            "change_type",
            "reason",
            "confidence",
        ):
            if key not in item:
                raise ValidationError(f"Semantic proposal candidate {index} is missing {key}")
    return raw


def import_semantic_proposal_envelope(paths, proposal_path: Path):
    """Import packet-bound proposals through the existing Human Review candidate importer."""
    validate_semantic_proposal_envelope(paths, proposal_path)
    return import_proposals(paths, proposal_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import packet-bound SubtitleFlow semantic proposals into Human Review"
    )
    parser.add_argument("project")
    parser.add_argument("title")
    parser.add_argument("proposal", type=Path)
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args(argv)
    repo = args.repo.resolve() if args.repo else find_repo_root()
    paths = title_paths(repo, args.project, args.title)
    imported = import_semantic_proposal_envelope(paths, args.proposal)
    print(
        json.dumps(
            {
                "imported": len(imported),
                "candidate_ids": [candidate.candidate_id for candidate in imported],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

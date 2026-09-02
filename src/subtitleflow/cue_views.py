from __future__ import annotations

from collections.abc import Sequence

from .models import Cue
from .roles import is_semantic_evidence_role


def evidence_cues(cues: Sequence[Cue]) -> list[Cue]:
    """Return dialogue text that is usable as semantic evidence.

    ASS protection is a presentation/editing constraint, not a semantic-evidence constraint.
    Protected dialogue such as ``{\\pos(...)}日本語`` therefore remains available through
    its already-normalized ``plain_text`` while the original ASS event stays immutable.
    Drawings, credits, non-verbal accessibility captions, comments, empty text, and other
    non-semantic roles remain excluded.
    """
    return [
        cue
        for cue in cues
        if cue.event_type.lower() == "dialogue"
        and cue.plain_text.strip()
        and cue.include_in_release
        and is_semantic_evidence_role(cue.semantic_role)
    ]

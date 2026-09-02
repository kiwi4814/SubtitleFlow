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

    Concurrent cues sharing identical/near-identical timestamps are presentation splits of
    the same spoken utterance and are collapsed into single logical cues.
    """
    raw = [
        cue
        for cue in cues
        if cue.event_type.lower() == "dialogue"
        and cue.plain_text.strip()
        and cue.include_in_release
        and is_semantic_evidence_role(cue.semantic_role)
    ]
    if not raw:
        return []
    result: list[Cue] = []
    i = 0
    while i < len(raw):
        curr = raw[i]
        merged_text = [curr.plain_text.strip()]
        j = i + 1
        while j < len(raw):
            nxt = raw[j]
            if abs(nxt.start_ms - curr.start_ms) <= 200 and abs(nxt.end_ms - curr.end_ms) <= 200:
                merged_text.append(nxt.plain_text.strip())
                j += 1
            else:
                break
        from dataclasses import replace

        combined = replace(curr, plain_text=" ".join(merged_text))
        result.append(combined)
        i = j
    return result

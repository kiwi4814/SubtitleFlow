from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .models import AlignmentGroup, BranchUnit, Cue
from .text import normalize_dialogue_text

PairOperation = Literal[
    "exact-pair",
    "source-split",
    "source-merge",
    "source-gap",
    "unresolved",
]


@dataclass(slots=True)
class BilingualPair:
    id: str
    target_unit_id: str
    start_ms: int
    end_ms: int
    target_text: str
    source_text: str | None
    source_text_cue_ids: list[str] = field(default_factory=list)
    parent_source_cue_ids: list[str] = field(default_factory=list)
    operation: PairOperation = "exact-pair"
    confidence: float = 1.0
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReconciliationResult:
    pairs: list[BilingualPair]
    unmatched_source_cue_ids: list[str]
    semantic_risks: list[dict[str, Any]]

    def coverage(self) -> dict[str, Any]:
        total = len(self.pairs)
        counts = {
            "exact_pair": sum(item.operation == "exact-pair" for item in self.pairs),
            "source_split": sum(item.operation == "source-split" for item in self.pairs),
            "source_merge": sum(item.operation == "source-merge" for item in self.pairs),
            "source_gap": sum(item.operation == "source-gap" for item in self.pairs),
            "unresolved": sum(item.operation == "unresolved" for item in self.pairs),
            "fabricated": 0,
        }
        verified = counts["exact_pair"] + counts["source_split"] + counts["source_merge"]
        return {
            "schema_version": 1,
            "ordinary_target_dialogue": total,
            "strict_paired": verified,
            **counts,
            "verified_bilingual_coverage": round(verified / total, 6) if total else 1.0,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "pairs": [item.to_dict() for item in self.pairs],
            "unmatched_source_cue_ids": list(self.unmatched_source_cue_ids),
            "semantic_risks": list(self.semantic_risks),
            "coverage": self.coverage(),
        }


def _join(cues: list[Cue]) -> str:
    return normalize_dialogue_text("\n".join(item.plain_text for item in cues if item.plain_text.strip()))


def reconcile_groups(
    units: list[BranchUnit],
    source_cues: list[Cue],
    groups: list[AlignmentGroup],
    *,
    split_decisions: dict[str, str] | None = None,
) -> ReconciliationResult:
    """Turn alignment membership into release pairs without inventing source language.

    `split_decisions` maps target unit IDs to editor/AI-approved source fragments. A single
    source cue may only be split among target units that the alignment group already associates
    with that cue. N source cues -> 1 target is a provenance-preserving merge. N:M remains
    unresolved until an editor provides a narrower decision.
    """
    split_decisions = split_decisions or {}
    umap = {item.id: item for item in units}
    cmap = {item.id: item for item in source_cues}
    pairs: list[BilingualPair] = []
    unmatched_source: list[str] = []
    risks: list[dict[str, Any]] = []

    for group in groups:
        if not group.left_ids:
            unmatched_source.extend(group.right_ids)
            risks.append(
                {
                    "kind": "unmatched-source",
                    "source_cue_ids": list(group.right_ids),
                    "alignment_group": group.id,
                }
            )
            continue
        left = [umap[item] for item in group.left_ids if item in umap]
        right = [cmap[item] for item in group.right_ids if item in cmap]
        if not right:
            for unit in left:
                pairs.append(
                    BilingualPair(
                        id=f"pair-{len(pairs)+1:06d}",
                        target_unit_id=unit.id,
                        start_ms=unit.start_ms,
                        end_ms=unit.end_ms,
                        target_text=unit.final_text,
                        source_text=None,
                        operation="source-gap",
                        confidence=group.confidence,
                        flags=["SOURCE_GAP"],
                    )
                )
                risks.append({"kind": "source-gap", "unit_id": unit.id, "alignment_group": group.id})
            continue

        if len(left) == 1:
            unit = left[0]
            operation: PairOperation = "exact-pair" if len(right) == 1 else "source-merge"
            pairs.append(
                BilingualPair(
                    id=f"pair-{len(pairs)+1:06d}",
                    target_unit_id=unit.id,
                    start_ms=unit.start_ms,
                    end_ms=unit.end_ms,
                    target_text=unit.final_text,
                    source_text=_join(right),
                    source_text_cue_ids=[item.id for item in right],
                    parent_source_cue_ids=[item.id for item in right],
                    operation=operation,
                    confidence=group.confidence,
                )
            )
            if len(right) > 1:
                risks.append({"kind": "source-merge", "unit_id": unit.id, "source_cue_ids": group.right_ids})
            continue

        if len(right) == 1:
            parent = right[0]
            missing = [unit.id for unit in left if not split_decisions.get(unit.id, "").strip()]
            if missing:
                for unit in left:
                    fragment = split_decisions.get(unit.id, "").strip() or None
                    pairs.append(
                        BilingualPair(
                            id=f"pair-{len(pairs)+1:06d}",
                            target_unit_id=unit.id,
                            start_ms=unit.start_ms,
                            end_ms=unit.end_ms,
                            target_text=unit.final_text,
                            source_text=fragment,
                            source_text_cue_ids=[parent.id] if fragment else [],
                            parent_source_cue_ids=[parent.id],
                            operation="source-split" if fragment else "unresolved",
                            confidence=group.confidence,
                            flags=[] if fragment else ["split-decision-required"],
                        )
                    )
                risks.append(
                    {
                        "kind": "source-split-decision-required",
                        "target_unit_ids": list(group.left_ids),
                        "parent_source_cue_id": parent.id,
                    }
                )
            else:
                for unit in left:
                    pairs.append(
                        BilingualPair(
                            id=f"pair-{len(pairs)+1:06d}",
                            target_unit_id=unit.id,
                            start_ms=unit.start_ms,
                            end_ms=unit.end_ms,
                            target_text=unit.final_text,
                            source_text=split_decisions[unit.id].strip(),
                            source_text_cue_ids=[parent.id],
                            parent_source_cue_ids=[parent.id],
                            operation="source-split",
                            confidence=group.confidence,
                        )
                    )
            continue

        for unit in left:
            pairs.append(
                BilingualPair(
                    id=f"pair-{len(pairs)+1:06d}",
                    target_unit_id=unit.id,
                    start_ms=unit.start_ms,
                    end_ms=unit.end_ms,
                    target_text=unit.final_text,
                    source_text=None,
                    parent_source_cue_ids=list(group.right_ids),
                    operation="unresolved",
                    confidence=group.confidence,
                    flags=["n:m-reconciliation-required"],
                )
            )
        risks.append(
            {
                "kind": "n:m-reconciliation-required",
                "target_unit_ids": list(group.left_ids),
                "source_cue_ids": list(group.right_ids),
            }
        )

    return ReconciliationResult(
        pairs=pairs,
        unmatched_source_cue_ids=unmatched_source,
        semantic_risks=risks,
    )

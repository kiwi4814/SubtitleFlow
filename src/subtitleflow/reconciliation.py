from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .errors import ValidationError
from .models import AlignmentGroup, BranchUnit, Cue
from .text import normalize_dialogue_text

PairOperation = Literal[
    "exact-pair",
    "source-split",
    "source-merge",
    "source-gap",
    "unresolved",
]

FragmentDisposition = Literal[
    "presented",
    "merged_presented",
    "folded_with_reason",
    "parallel_reaction_omitted_with_reason",
    "nonverbal",
    "unresolved",
]

_FRAGMENT_DISPOSITIONS = {
    "presented",
    "merged_presented",
    "folded_with_reason",
    "parallel_reaction_omitted_with_reason",
    "nonverbal",
    "unresolved",
}
_PRESENTED_DISPOSITIONS = {"presented", "merged_presented"}
_FINAL_REF_ALLOWED_DISPOSITIONS = {*_PRESENTED_DISPOSITIONS, "folded_with_reason"}
_REASON_REQUIRED_DISPOSITIONS = {
    "folded_with_reason",
    "parallel_reaction_omitted_with_reason",
    "nonverbal",
}


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
class SourceFragment:
    id: str
    source_cue_id: str
    source_index: int
    start_ms: int
    end_ms: int
    text: str
    span_start: int
    span_end: int
    disposition: FragmentDisposition
    target_unit_ids: list[str] = field(default_factory=list)
    final_refs: list[str] = field(default_factory=list)
    reason: str | None = None
    explicit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourceEventAccounting:
    source_cue_id: str
    source_index: int
    fragment_ids: list[str]
    status: Literal["presented_full", "presented_partial", "resolved_nonpresented", "unresolved"]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReconciliationResult:
    pairs: list[BilingualPair]
    unmatched_source_cue_ids: list[str]
    semantic_risks: list[dict[str, Any]]
    source_fragments: list[SourceFragment] = field(default_factory=list)
    source_events: list[SourceEventAccounting] = field(default_factory=list)
    accounting_issues: list[dict[str, Any]] = field(default_factory=list)

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
        spoken = [item for item in self.source_fragments if item.disposition != "nonverbal"]
        resolved = [item for item in spoken if item.disposition != "unresolved"]
        return {
            "schema_version": 2,
            "ordinary_target_dialogue": total,
            "strict_paired": verified,
            **counts,
            "verified_bilingual_coverage": round(verified / total, 6) if total else 1.0,
            "source_spoken_fragments_total": len(spoken),
            "source_spoken_fragments_resolved": len(resolved),
            "source_spoken_fragments_unresolved": len(spoken) - len(resolved),
            "source_events_presented_full": sum(
                item.status == "presented_full" for item in self.source_events
            ),
            "source_events_presented_partial": sum(
                item.status == "presented_partial" for item in self.source_events
            ),
            "source_events_resolved_nonpresented": sum(
                item.status == "resolved_nonpresented" for item in self.source_events
            ),
            "source_events_unresolved": sum(
                item.status == "unresolved" for item in self.source_events
            ),
            "invalid_final_refs": sum(
                item.get("kind") == "invalid-final-ref" for item in self.accounting_issues
            ),
            "invalid_fragment_ownership": sum(
                item.get("kind") == "invalid-fragment-ownership" for item in self.accounting_issues
            ),
            "substantive_source_order_violations": sum(
                item.get("kind") == "substantive-source-order-violation"
                for item in self.accounting_issues
            ),
            "missing_disposition_reasons": sum(
                item.get("kind") == "missing-disposition-reason" for item in self.accounting_issues
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "pairs": [item.to_dict() for item in self.pairs],
            "unmatched_source_cue_ids": list(self.unmatched_source_cue_ids),
            "semantic_risks": list(self.semantic_risks),
            "source_fragments": [item.to_dict() for item in self.source_fragments],
            "source_events": [item.to_dict() for item in self.source_events],
            "accounting_issues": list(self.accounting_issues),
            "coverage": self.coverage(),
        }


def _join(cues: list[Cue]) -> str:
    return normalize_dialogue_text(
        "\n".join(item.plain_text for item in cues if item.plain_text.strip())
    )


def _source_text(cue: Cue) -> str:
    return normalize_dialogue_text(cue.plain_text)


def _decision_text(cue: Cue, decision: dict[str, Any]) -> tuple[str, int, int]:
    source = _source_text(cue)
    span = decision.get("span")
    if not isinstance(span, dict):
        raise ValidationError(f"Source fragment for {cue.id} must have a span object")
    try:
        start = int(span["start"])
        end = int(span["end"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(
            f"Source fragment for {cue.id} must have integer span.start/span.end"
        ) from exc
    if start < 0 or end <= start or end > len(source):
        raise ValidationError(f"Source fragment for {cue.id} has an invalid span {start}:{end}")
    actual = source[start:end]
    supplied = decision.get("text")
    if supplied is not None and normalize_dialogue_text(str(supplied)) != actual:
        raise ValidationError(f"Source fragment for {cue.id} does not match its declared span")
    return actual, start, end


def _explicit_fragment_map(
    source_cues: list[Cue],
    fragment_decisions: dict[str, list[dict[str, Any]]] | None,
) -> dict[str, list[dict[str, Any]]]:
    if fragment_decisions is None:
        return {}
    if not isinstance(fragment_decisions, dict):
        raise ValidationError("source_fragment_decisions must be an object")
    source_ids = {item.id for item in source_cues}
    result: dict[str, list[dict[str, Any]]] = {}
    seen_ids: set[str] = set()
    for source_id, raw_items in fragment_decisions.items():
        if source_id not in source_ids:
            raise ValidationError(
                f"Source fragment decision references missing source cue: {source_id}"
            )
        if not isinstance(raw_items, list) or not raw_items:
            raise ValidationError(
                f"Source fragment decisions for {source_id} must be a non-empty array"
            )
        items: list[dict[str, Any]] = []
        occupied: list[tuple[int, int]] = []
        cue = next(item for item in source_cues if item.id == source_id)
        for index, raw in enumerate(raw_items, 1):
            if not isinstance(raw, dict):
                raise ValidationError(
                    f"Source fragment decision {source_id}#{index} must be an object"
                )
            decision = dict(raw)
            disposition = str(decision.get("disposition", "unresolved"))
            if disposition not in _FRAGMENT_DISPOSITIONS:
                raise ValidationError(
                    f"Source fragment decision {source_id}#{index} has unknown disposition: {disposition}"
                )
            text, start, end = _decision_text(cue, decision)
            if any(start < other_end and end > other_start for other_start, other_end in occupied):
                raise ValidationError(
                    f"Source fragment decisions for {source_id} have overlapping spans"
                )
            occupied.append((start, end))
            fragment_id = str(decision.get("id") or f"{source_id}#fragment-{index:02d}")
            if fragment_id in seen_ids:
                raise ValidationError(f"Duplicate source fragment id: {fragment_id}")
            seen_ids.add(fragment_id)
            targets = decision.get("target_unit_ids", [])
            if not isinstance(targets, list):
                raise ValidationError(
                    f"Source fragment {fragment_id} target_unit_ids must be an array"
                )
            decision.update(
                {
                    "id": fragment_id,
                    "text": text,
                    "span_start": start,
                    "span_end": end,
                    "disposition": disposition,
                    "target_unit_ids": [str(item) for item in targets],
                    "reason": str(decision["reason"]).strip()
                    if decision.get("reason") is not None
                    else None,
                }
            )
            items.append(decision)
        result[source_id] = sorted(items, key=lambda item: (item["span_start"], item["span_end"]))
    return result


def _implicit_split_fragments(
    cue: Cue,
    pairs: list[BilingualPair],
) -> list[tuple[str, int, int, BilingualPair]] | None:
    source = _source_text(cue)
    cursor = 0
    result: list[tuple[str, int, int, BilingualPair]] = []
    for pair in pairs:
        fragment = normalize_dialogue_text(pair.source_text or "")
        if not fragment:
            return None
        start = source.find(fragment, cursor)
        if start < 0:
            return None
        end = start + len(fragment)
        result.append((fragment, start, end, pair))
        cursor = end
    return result


def _gap_fragments(
    cue: Cue,
    covered: list[tuple[int, int]],
    *,
    explicit: bool,
) -> list[SourceFragment]:
    source = _source_text(cue)
    fragments: list[SourceFragment] = []
    cursor = 0
    for start, end in sorted(covered):
        if source[cursor:start].strip():
            fragments.append(
                SourceFragment(
                    id=f"{cue.id}#unresolved-{len(fragments) + 1:02d}",
                    source_cue_id=cue.id,
                    source_index=cue.index,
                    start_ms=cue.start_ms,
                    end_ms=cue.end_ms,
                    text=source[cursor:start],
                    span_start=cursor,
                    span_end=start,
                    disposition="unresolved",
                    explicit=explicit,
                )
            )
        cursor = max(cursor, end)
    if source[cursor:].strip():
        fragments.append(
            SourceFragment(
                id=f"{cue.id}#unresolved-{len(fragments) + 1:02d}",
                source_cue_id=cue.id,
                source_index=cue.index,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                text=source[cursor:],
                span_start=cursor,
                span_end=len(source),
                disposition="unresolved",
                explicit=explicit,
            )
        )
    return fragments


def _account_source_fragments(
    source_cues: list[Cue],
    pairs: list[BilingualPair],
    fragment_decisions: dict[str, list[dict[str, Any]]] | None,
) -> tuple[list[SourceFragment], list[SourceEventAccounting], list[dict[str, Any]]]:
    explicit = _explicit_fragment_map(source_cues, fragment_decisions)
    pair_by_target = {item.target_unit_id: item for item in pairs}
    ordered_pairs = sorted(pairs, key=lambda item: (item.start_ms, item.end_ms, item.id))
    pair_order = {item.id: index for index, item in enumerate(ordered_pairs)}
    fragments: list[SourceFragment] = []
    issues: list[dict[str, Any]] = []

    for cue in source_cues:
        cue_pairs = [item for item in pairs if cue.id in item.parent_source_cue_ids]
        decisions = explicit.get(cue.id)
        if decisions is not None:
            covered: list[tuple[int, int]] = []
            for decision in decisions:
                target_ids = list(decision["target_unit_ids"])
                final_refs: list[str] = []
                for target_id in target_ids:
                    pair = pair_by_target.get(target_id)
                    if pair is None:
                        issues.append(
                            {
                                "kind": "invalid-final-ref",
                                "fragment_id": decision["id"],
                                "target_unit_id": target_id,
                            }
                        )
                        continue
                    if cue.id not in pair.parent_source_cue_ids:
                        issues.append(
                            {
                                "kind": "invalid-fragment-ownership",
                                "fragment_id": decision["id"],
                                "source_cue_id": cue.id,
                                "final_ref": pair.id,
                            }
                        )
                        continue
                    if pair.id in final_refs:
                        issues.append(
                            {
                                "kind": "duplicate-final-ref",
                                "fragment_id": decision["id"],
                                "final_ref": pair.id,
                            }
                        )
                        continue
                    final_refs.append(pair.id)
                disposition = decision["disposition"]
                if disposition in _PRESENTED_DISPOSITIONS and not final_refs:
                    issues.append(
                        {
                            "kind": "presented-fragment-without-final-ref",
                            "fragment_id": decision["id"],
                        }
                    )
                if disposition not in _FINAL_REF_ALLOWED_DISPOSITIONS and final_refs:
                    issues.append(
                        {
                            "kind": "nonpresented-fragment-with-final-ref",
                            "fragment_id": decision["id"],
                        }
                    )
                if disposition in _REASON_REQUIRED_DISPOSITIONS and not decision["reason"]:
                    issues.append(
                        {
                            "kind": "missing-disposition-reason",
                            "fragment_id": decision["id"],
                        }
                    )
                fragments.append(
                    SourceFragment(
                        id=decision["id"],
                        source_cue_id=cue.id,
                        source_index=cue.index,
                        start_ms=cue.start_ms,
                        end_ms=cue.end_ms,
                        text=decision["text"],
                        span_start=decision["span_start"],
                        span_end=decision["span_end"],
                        disposition=disposition,
                        target_unit_ids=target_ids,
                        final_refs=final_refs,
                        reason=decision["reason"],
                        explicit=True,
                    )
                )
                covered.append((decision["span_start"], decision["span_end"]))
            fragments.extend(_gap_fragments(cue, covered, explicit=True))
            continue

        split_pairs = [item for item in cue_pairs if item.operation == "source-split"]
        split = _implicit_split_fragments(cue, split_pairs) if split_pairs else None
        if split is not None:
            covered = []
            for index, (text, start, end, pair) in enumerate(split, 1):
                fragments.append(
                    SourceFragment(
                        id=f"{cue.id}#fragment-{index:02d}",
                        source_cue_id=cue.id,
                        source_index=cue.index,
                        start_ms=cue.start_ms,
                        end_ms=cue.end_ms,
                        text=text,
                        span_start=start,
                        span_end=end,
                        disposition="presented",
                        target_unit_ids=[pair.target_unit_id],
                        final_refs=[pair.id],
                    )
                )
                covered.append((start, end))
            fragments.extend(_gap_fragments(cue, covered, explicit=False))
            continue

        presented_pairs = [
            item
            for item in cue_pairs
            if item.operation in {"exact-pair", "source-merge"} and item.source_text
        ]
        if presented_pairs:
            disposition: FragmentDisposition = (
                "merged_presented"
                if any(item.operation == "source-merge" for item in presented_pairs)
                else "presented"
            )
            source = _source_text(cue)
            fragments.append(
                SourceFragment(
                    id=f"{cue.id}#full",
                    source_cue_id=cue.id,
                    source_index=cue.index,
                    start_ms=cue.start_ms,
                    end_ms=cue.end_ms,
                    text=source,
                    span_start=0,
                    span_end=len(source),
                    disposition=disposition,
                    target_unit_ids=[item.target_unit_id for item in presented_pairs],
                    final_refs=[item.id for item in presented_pairs],
                )
            )
            continue

        source = _source_text(cue)
        fragments.append(
            SourceFragment(
                id=f"{cue.id}#full",
                source_cue_id=cue.id,
                source_index=cue.index,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
                text=source,
                span_start=0,
                span_end=len(source),
                disposition="unresolved",
            )
        )

    fragments_by_cue: dict[str, list[SourceFragment]] = {}
    for fragment in fragments:
        fragments_by_cue.setdefault(fragment.source_cue_id, []).append(fragment)

    events: list[SourceEventAccounting] = []
    for cue in source_cues:
        items = fragments_by_cue.get(cue.id, [])
        unresolved = [item for item in items if item.disposition == "unresolved"]
        presented = [item for item in items if item.disposition in _PRESENTED_DISPOSITIONS]
        if unresolved:
            status = "presented_partial" if presented else "unresolved"
        elif presented:
            status = "presented_full"
        else:
            status = "resolved_nonpresented"
        events.append(
            SourceEventAccounting(
                source_cue_id=cue.id,
                source_index=cue.index,
                fragment_ids=[item.id for item in items],
                status=status,
            )
        )

    presented_fragments = [item for item in fragments if item.final_refs]
    for source_id, items in fragments_by_cue.items():
        ordered = sorted(
            (item for item in items if item.final_refs), key=lambda item: item.span_start
        )
        previous: SourceFragment | None = None
        for item in ordered:
            if previous is not None and min(pair_order[ref] for ref in item.final_refs) < max(
                pair_order[ref] for ref in previous.final_refs
            ):
                issues.append(
                    {
                        "kind": "substantive-source-order-violation",
                        "source_cue_id": source_id,
                        "previous_fragment_id": previous.id,
                        "fragment_id": item.id,
                    }
                )
            previous = item

    ordered_fragments = sorted(
        presented_fragments,
        key=lambda item: (item.start_ms, item.end_ms, item.source_index, item.span_start),
    )
    previous = None
    for item in ordered_fragments:
        if (
            previous is not None
            and previous.source_cue_id != item.source_cue_id
            and previous.end_ms <= item.start_ms
            and min(pair_order[ref] for ref in item.final_refs)
            < max(pair_order[ref] for ref in previous.final_refs)
        ):
            issues.append(
                {
                    "kind": "substantive-source-order-violation",
                    "previous_fragment_id": previous.id,
                    "fragment_id": item.id,
                }
            )
        previous = item

    return fragments, events, issues


def _project_explicit_fragments(
    pairs: list[BilingualPair],
    fragments: list[SourceFragment],
) -> None:
    explicit_source_ids = {item.source_cue_id for item in fragments if item.explicit}
    if not explicit_source_ids:
        return
    for pair in pairs:
        if not explicit_source_ids.intersection(pair.parent_source_cue_ids):
            continue
        selected = [
            item
            for item in fragments
            if pair.id in item.final_refs and item.disposition in _PRESENTED_DISPOSITIONS
        ]
        selected.sort(key=lambda item: (item.source_index, item.span_start))
        pair.source_text = (
            normalize_dialogue_text("\n".join(item.text for item in selected)) or None
        )
        pair.source_text_cue_ids = list(dict.fromkeys(item.source_cue_id for item in selected))
        if pair.source_text is None and pair.operation != "source-gap":
            pair.operation = "unresolved"
            if "fragment-presentation-required" not in pair.flags:
                pair.flags.append("fragment-presentation-required")


def reconcile_groups(
    units: list[BranchUnit],
    source_cues: list[Cue],
    groups: list[AlignmentGroup],
    *,
    split_decisions: dict[str, str] | None = None,
    fragment_decisions: dict[str, list[dict[str, Any]]] | None = None,
) -> ReconciliationResult:
    """Turn alignment membership into release pairs without inventing source language.

    `split_decisions` maps target unit IDs to editor/AI-approved source fragments. A single
    source cue may only be split among target units that the alignment group already associates
    with that cue. N source cues -> 1 target is a provenance-preserving merge. N:M remains
    unresolved until an editor provides a narrower decision.
    """
    split_decisions = dict(split_decisions or {})
    explicit_fragments = _explicit_fragment_map(source_cues, fragment_decisions)
    fragment_text_by_target: dict[str, list[str]] = {}
    for decisions in explicit_fragments.values():
        for decision in decisions:
            if decision["disposition"] not in _PRESENTED_DISPOSITIONS:
                continue
            for target_id in decision["target_unit_ids"]:
                fragment_text_by_target.setdefault(target_id, []).append(decision["text"])
    for target_id, fragments in fragment_text_by_target.items():
        split_decisions.setdefault(target_id, normalize_dialogue_text("\n".join(fragments)))
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
                        id=f"pair-{len(pairs) + 1:06d}",
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
                risks.append(
                    {"kind": "source-gap", "unit_id": unit.id, "alignment_group": group.id}
                )
            continue

        if len(left) == 1:
            unit = left[0]
            operation: PairOperation = "exact-pair" if len(right) == 1 else "source-merge"
            pairs.append(
                BilingualPair(
                    id=f"pair-{len(pairs) + 1:06d}",
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
                risks.append(
                    {"kind": "source-merge", "unit_id": unit.id, "source_cue_ids": group.right_ids}
                )
            continue

        if len(right) == 1:
            parent = right[0]
            missing = [unit.id for unit in left if not split_decisions.get(unit.id, "").strip()]
            if missing:
                for unit in left:
                    fragment = split_decisions.get(unit.id, "").strip() or None
                    pairs.append(
                        BilingualPair(
                            id=f"pair-{len(pairs) + 1:06d}",
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
                            id=f"pair-{len(pairs) + 1:06d}",
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
                    id=f"pair-{len(pairs) + 1:06d}",
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

    source_fragments, source_events, accounting_issues = _account_source_fragments(
        source_cues, pairs, fragment_decisions
    )
    _project_explicit_fragments(pairs, source_fragments)
    return ReconciliationResult(
        pairs=pairs,
        unmatched_source_cue_ids=unmatched_source,
        semantic_risks=risks,
        source_fragments=source_fragments,
        source_events=source_events,
        accounting_issues=accounting_issues,
    )

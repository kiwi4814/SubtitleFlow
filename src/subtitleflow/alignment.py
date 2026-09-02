from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass

from .models import AlignmentGroup, Cue


@dataclass(slots=True)
class AlignmentResult:
    groups: list[AlignmentGroup]
    total_cost: float
    estimated_offset_ms: int
    semantic_risks: list[dict[str, object]] | None = None

    def to_dict(self) -> dict[str, object]:
        risks = self.semantic_risks or []
        return {
            "schema_version": 2,
            "total_cost": round(self.total_cost, 6),
            "estimated_offset_ms": self.estimated_offset_ms,
            "groups": [group.to_dict() for group in self.groups],
            "semantic_risks": risks,
            "summary": {
                "group_count": len(self.groups),
                "matched": sum(bool(g.left_ids and g.right_ids) for g in self.groups),
                "unmatched_left": sum(bool(g.left_ids and not g.right_ids) for g in self.groups),
                "unmatched_right": sum(bool(g.right_ids and not g.left_ids) for g in self.groups),
                "low_confidence": sum(
                    g.confidence < 0.72 for g in self.groups if g.left_ids and g.right_ids
                ),
                "semantic_risk_count": len(risks),
            },
        }


def editable_cues(cues: Sequence[Cue]) -> list[Cue]:
    return [
        cue
        for cue in cues
        if cue.event_type.lower() == "dialogue"
        and not cue.protected
        and cue.plain_text.strip()
        and cue.include_in_release
        and cue.semantic_role in {"dialogue", "song-op", "song-ed", "song-insert"}
    ]


def _activity_intervals(cues: Sequence[Cue]) -> list[tuple[int, int]]:
    """Collapse subtitle events into density-independent active time spans."""
    spans = sorted((cue.start_ms, cue.end_ms) for cue in cues if cue.end_ms > cue.start_ms)
    if not spans:
        return []
    merged: list[tuple[int, int]] = []
    start, end = spans[0]
    for next_start, next_end in spans[1:]:
        if next_start <= end:
            end = max(end, next_end)
            continue
        merged.append((start, end))
        start, end = next_start, next_end
    merged.append((start, end))
    return merged


def _activity_overlap_ms(
    left: Sequence[tuple[int, int]],
    right: Sequence[tuple[int, int]],
    offset_ms: int,
) -> int:
    """Return active-time intersection after shifting right by ``-offset_ms``."""
    i = 0
    j = 0
    overlap = 0
    while i < len(left) and j < len(right):
        left_start, left_end = left[i]
        right_start = right[j][0] - offset_ms
        right_end = right[j][1] - offset_ms
        overlap += max(0, min(left_end, right_end) - max(left_start, right_start))
        if left_end <= right_end:
            i += 1
        else:
            j += 1
    return overlap


def _activity_similarity(
    left: Sequence[tuple[int, int]],
    right: Sequence[tuple[int, int]],
    offset_ms: int,
) -> float:
    left_total = sum(end - start for start, end in left)
    right_total = sum(end - start for start, end in right)
    if left_total <= 0 or right_total <= 0:
        return 0.0
    overlap = _activity_overlap_ms(left, right, offset_ms)
    return (2.0 * overlap) / (left_total + right_total)


def _best_activity_offset(
    left: Sequence[tuple[int, int]],
    right: Sequence[tuple[int, int]],
    *,
    start_ms: int,
    end_ms: int,
    step_ms: int,
) -> tuple[int, float]:
    best_offset = 0
    best_score = -1.0
    for offset in range(start_ms, end_ms + 1, step_ms):
        score = _activity_similarity(left, right, offset)
        if score > best_score + 1e-12 or (
            abs(score - best_score) <= 1e-12 and abs(offset) < abs(best_offset)
        ):
            best_offset = offset
            best_score = score
    return best_offset, best_score


def estimate_offset_ms(left: Sequence[Cue], right: Sequence[Cue]) -> int:
    """Estimate a coarse global timing shift without depending on cue density."""
    if not left or not right:
        return 0
    left_activity = _activity_intervals(left)
    right_activity = _activity_intervals(right)
    if not left_activity or not right_activity:
        return 0

    coarse_offset, coarse_score = _best_activity_offset(
        left_activity,
        right_activity,
        start_ms=-120_000,
        end_ms=120_000,
        step_ms=1_000,
    )
    refine_start = max(-120_000, coarse_offset - 1_000)
    refine_end = min(120_000, coarse_offset + 1_000)
    refined_offset, refined_score = _best_activity_offset(
        left_activity,
        right_activity,
        start_ms=refine_start,
        end_ms=refine_end,
        step_ms=100,
    )

    zero_score = _activity_similarity(left_activity, right_activity, 0)
    best_score = max(coarse_score, refined_score)
    if best_score <= 0.0:
        return 0
    if refined_offset != 0 and best_score - zero_score < 0.01:
        return 0
    return refined_offset


def _span(cues: Sequence[Cue], start: int, count: int, offset_ms: int = 0) -> tuple[int, int]:
    selected = cues[start : start + count]
    return selected[0].start_ms - offset_ms, selected[-1].end_ms - offset_ms


def _match_cost(
    left: Sequence[Cue],
    right: Sequence[Cue],
    i: int,
    j: int,
    gl: int,
    gr: int,
    offset_ms: int,
) -> float:
    if gl > 1:
        for k in range(i, i + gl - 1):
            if left[k + 1].start_ms - left[k].end_ms > 600:
                return float("inf")
    if gr > 1:
        for k in range(j, j + gr - 1):
            if right[k + 1].start_ms - right[k].end_ms > 600:
                return float("inf")
    ls, le = _span(left, i, gl)
    rs, re = _span(right, j, gr, offset_ms)
    ldur = max(1, le - ls)
    rdur = max(1, re - rs)
    union_start = min(ls, rs)
    union_end = max(le, re)
    union = max(1, union_end - union_start)
    overlap = max(0, min(le, re) - max(ls, rs))
    overlap_ratio = overlap / union
    if overlap <= 0 or overlap_ratio < 0.20:
        return float("inf")
    boundary = (abs(ls - rs) + abs(le - re)) / 2_000.0
    midpoint = abs((ls + le) - (rs + re)) / 4_000.0
    duration_ratio = abs(math.log(ldur / rdur))
    complexity = 0.12 * max(0, gl + gr - 2)
    return (
        0.65 * boundary
        + 0.55 * midpoint
        + 1.15 * (1 - overlap_ratio)
        + 0.35 * duration_ratio
        + complexity
    )


def _unmatched_cost(cue: Cue, penalty: float) -> float:
    duration = max(0, cue.end_ms - cue.start_ms)
    return penalty + min(1.5, duration / 15_000.0)


def _plain_join(cues: Sequence[Cue], ids: list[str]) -> str:
    wanted = set(ids)
    return " ".join(
        item.plain_text for item in cues if item.id in wanted and item.plain_text.strip()
    )


def _risk_signals(
    groups: list[AlignmentGroup],
    left: Sequence[Cue],
    right: Sequence[Cue],
    *,
    threshold: float = 0.72,
) -> list[dict[str, object]]:
    risks: list[dict[str, object]] = []
    number_re = re.compile(r"\d+(?:[.,]\d+)?")
    negation_re = re.compile(
        r"(?:\u306a\u3044|\u307e\u305b\u3093|\u306a\u304b\u3063\u305f|\u3058\u3083\u306a\u3044|\u3067\u306f\u306a\u3044|\u4e0d|\u6ca1|\u65e0|\u672a|\u522b|\u4e0d\u8981|not|n't|never)",
        re.I,
    )
    for group in groups:
        base = {"alignment_group": group.id, "kind": group.kind, "confidence": group.confidence}
        if group.kind != "1:1":
            risk_kind = {
                "unmatched-left": "unmatched-target",
                "unmatched-right": "unmatched-source",
            }.get(group.kind, "n:m-alignment")
            risks.append({**base, "risk": risk_kind})
        if group.left_ids and group.right_ids and group.confidence < threshold:
            risks.append({**base, "risk": "low-confidence"})
        if not group.left_ids or not group.right_ids:
            continue
        left_text = _plain_join(left, group.left_ids)
        right_text = _plain_join(right, group.right_ids)
        if left_text and right_text:
            length_ratio = max(len(left_text), len(right_text)) / max(
                1, min(len(left_text), len(right_text))
            )
            if length_ratio >= 4.0:
                risks.append(
                    {**base, "risk": "abnormal-text-length-ratio", "ratio": round(length_ratio, 3)}
                )
            left_numbers = number_re.findall(left_text)
            right_numbers = number_re.findall(right_text)
            if left_numbers and right_numbers and left_numbers != right_numbers:
                risks.append(
                    {
                        **base,
                        "risk": "number-conflict",
                        "left": left_numbers,
                        "right": right_numbers,
                    }
                )
            if bool(negation_re.search(left_text)) != bool(negation_re.search(right_text)):
                risks.append({**base, "risk": "negation-conflict"})
        left_styles = {item.style for item in left if item.id in set(group.left_ids) and item.style}
        right_styles = {
            item.style for item in right if item.id in set(group.right_ids) and item.style
        }
        if len(left_styles) == 1 and len(right_styles) == 1 and left_styles != right_styles:
            risks.append(
                {
                    **base,
                    "risk": "speaker-or-role-mismatch",
                    "left_styles": sorted(left_styles),
                    "right_styles": sorted(right_styles),
                }
            )
    return risks


def align_cues(
    left: Sequence[Cue],
    right: Sequence[Cue],
    *,
    max_group: int = 3,
    max_left_group: int | None = None,
    max_right_group: int | None = None,
    unmatched_penalty: float = 3.0,
    offset_ms: int | None = None,
) -> AlignmentResult:
    left = list(left)
    right = list(right)
    n, m = len(left), len(right)
    if n == 0 and m == 0:
        return AlignmentResult(groups=[], total_cost=0.0, estimated_offset_ms=0, semantic_risks=[])
    if max_group < 1:
        raise ValueError("max_group must be at least 1")
    left_group_limit = max_group if max_left_group is None else max_left_group
    right_group_limit = max_group if max_right_group is None else max_right_group
    if left_group_limit < 1 or right_group_limit < 1:
        raise ValueError("max_left_group and max_right_group must be at least 1")
    offset = estimate_offset_ms(left, right) if offset_ms is None else offset_ms

    inf = float("inf")
    dp = [[inf] * (m + 1) for _ in range(n + 1)]
    back: list[list[tuple[int, int, int, int, float] | None]] = [
        [None] * (m + 1) for _ in range(n + 1)
    ]
    dp[0][0] = 0.0

    for i in range(n + 1):
        for j in range(m + 1):
            base = dp[i][j]
            if math.isinf(base):
                continue
            if i < n:
                cost = _unmatched_cost(left[i], unmatched_penalty)
                if base + cost < dp[i + 1][j]:
                    dp[i + 1][j] = base + cost
                    back[i + 1][j] = (i, j, 1, 0, cost)
            if j < m:
                cost = _unmatched_cost(right[j], unmatched_penalty)
                if base + cost < dp[i][j + 1]:
                    dp[i][j + 1] = base + cost
                    back[i][j + 1] = (i, j, 0, 1, cost)
            for gl in range(1, left_group_limit + 1):
                if i + gl > n:
                    break
                for gr in range(1, right_group_limit + 1):
                    if j + gr > m:
                        break
                    cost = _match_cost(left, right, i, j, gl, gr, offset)
                    ni, nj = i + gl, j + gr
                    if base + cost < dp[ni][nj]:
                        dp[ni][nj] = base + cost
                        back[ni][nj] = (i, j, gl, gr, cost)

    i, j = n, m
    reversed_groups: list[AlignmentGroup] = []
    serial = 0
    while i > 0 or j > 0:
        step = back[i][j]
        if step is None:
            raise RuntimeError(f"Alignment backtrace failed at ({i}, {j})")
        pi, pj, gl, gr, cost = step
        left_sel = left[pi:i]
        right_sel = right[pj:j]
        if left_sel:
            start_ms, end_ms = left_sel[0].start_ms, left_sel[-1].end_ms
        elif right_sel:
            start_ms = right_sel[0].start_ms - offset
            end_ms = right_sel[-1].end_ms - offset
        else:
            raise RuntimeError("Empty alignment transition")
        if gl and gr:
            kind = f"{gl}:{gr}"
            confidence = max(0.0, min(1.0, math.exp(-cost / 2.8)))
        elif gl:
            kind = "unmatched-left"
            confidence = 0.0
        else:
            kind = "unmatched-right"
            confidence = 0.0
        serial += 1
        reversed_groups.append(
            AlignmentGroup(
                id=f"align-{serial:06d}",
                left_ids=[cue.id for cue in left_sel],
                right_ids=[cue.id for cue in right_sel],
                start_ms=start_ms,
                end_ms=end_ms,
                cost=round(cost, 6),
                confidence=round(confidence, 6),
                kind=kind,
            )
        )
        i, j = pi, pj

    groups = list(reversed(reversed_groups))
    for index, group in enumerate(groups, start=1):
        group.id = f"align-{index:06d}"
    return AlignmentResult(
        groups=groups,
        total_cost=dp[n][m],
        estimated_offset_ms=offset,
        semantic_risks=_risk_signals(groups, left, right),
    )

from subtitleflow.alignment import align_cues, estimate_offset_ms
from subtitleflow.models import Cue


def cue(idx: int, start: int, end: int, text: str = "x") -> Cue:
    return Cue(id=f"c{idx}", index=idx, start_ms=start, end_ms=end, text=text, plain_text=text)


def test_alignment_one_to_one() -> None:
    left = [cue(1, 1000, 2000), cue(2, 3000, 4000)]
    right = [cue(1, 1100, 2100), cue(2, 3100, 4100)]
    result = align_cues(left, right)
    matched = [group for group in result.groups if group.left_ids and group.right_ids]
    assert [group.kind for group in matched] == ["1:1", "1:1"]
    assert all(group.confidence > 0.7 for group in matched)


def test_alignment_two_to_one() -> None:
    left = [cue(1, 1000, 1800), cue(2, 1850, 3000)]
    right = [cue(1, 1000, 3000)]
    result = align_cues(left, right, max_group=3)
    matched = [group for group in result.groups if group.left_ids and group.right_ids]
    assert any(group.kind == "2:1" for group in matched)


def test_alignment_estimates_global_offset() -> None:
    left = [cue(i, i * 2000, i * 2000 + 1000) for i in range(1, 8)]
    right = [cue(i, i * 2000 + 5000, i * 2000 + 6000) for i in range(1, 8)]
    result = align_cues(left, right)
    assert abs(result.estimated_offset_ms - 5000) <= 1
    assert sum(g.kind == "1:1" for g in result.groups) == 7


def test_offset_estimation_ignores_duplicate_event_density_and_leading_captions() -> None:
    left = [
        cue(1, 10_000, 11_500),
        cue(2, 20_000, 21_500),
        cue(3, 30_000, 31_500),
        cue(4, 40_000, 41_500),
        cue(5, 50_000, 51_500),
    ]
    right = [
        cue(101, 1_000, 2_000, "sfx"),
        cue(102, 2_500, 3_000, "sfx"),
    ]
    for index, item in enumerate(left, start=1):
        start = item.start_ms + 5_000
        end = item.end_ms + 5_000
        right.extend(
            [
                cue(200 + index * 2, start, end, "upper"),
                cue(201 + index * 2, start, end, "lower"),
            ]
        )

    assert estimate_offset_ms(left, right) == 5_000


def test_alignment_can_keep_left_units_atomic_for_bilingual_reconciliation() -> None:
    left = [
        cue(1, 1000, 1900),
        cue(2, 1950, 3000),
        cue(3, 3100, 4100),
    ]
    right = [
        cue(101, 1000, 1500),
        cue(102, 1500, 2300),
        cue(103, 2300, 3000),
        cue(104, 3100, 3600),
        cue(105, 3600, 4100),
    ]

    symmetric = align_cues(left, right, max_group=3)
    assert any(len(group.left_ids) > 1 for group in symmetric.groups if group.right_ids)

    atomic = align_cues(
        left,
        right,
        max_group=3,
        max_left_group=1,
        max_right_group=3,
    )
    matched = [group for group in atomic.groups if group.left_ids and group.right_ids]
    assert matched
    assert all(len(group.left_ids) == 1 for group in matched)
    represented_left = [cue_id for group in atomic.groups for cue_id in group.left_ids]
    assert represented_left == ["c1", "c2", "c3"]

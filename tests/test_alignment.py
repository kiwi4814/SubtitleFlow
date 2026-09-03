from subtitleflow.alignment import align_cues, alignment_cues, estimate_offset_ms
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


def test_alignment_offset_ignores_extra_leading_and_trailing_cues() -> None:
    left = [cue(i, i * 10_000, i * 10_000 + 1000) for i in range(1, 5)]
    right = [
        cue(1, 1000, 2000),
        cue(2, 2000, 3000),
        *[cue(i + 2, i * 10_000 + 7000, i * 10_000 + 8000) for i in range(1, 5)],
        cue(7, 80_000, 81_000),
    ]

    assert estimate_offset_ms(left, right) == 7000


def test_alignment_uses_plain_text_from_protected_ass_event() -> None:
    source = cue(1, 1100, 2100, r"{\pos(100,100)}こんにちは")
    source.protected = True

    selected = alignment_cues([source], include_protected=True)
    assert [item.plain_text for item in selected] == ["こんにちは"]

    result = align_cues([cue(1, 1000, 2000, "你好")], selected)
    matched = [group for group in result.groups if group.left_ids and group.right_ids]
    assert [group.kind for group in matched] == ["1:1"]

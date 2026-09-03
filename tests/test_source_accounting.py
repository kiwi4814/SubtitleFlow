from __future__ import annotations

from subtitleflow.models import AlignmentGroup, BranchUnit, Cue
from subtitleflow.reconciliation import reconcile_groups


def unit(idx: int, start: int, end: int) -> BranchUnit:
    return BranchUnit(
        id=f"jp-{idx:06d}",
        start_ms=start,
        end_ms=end,
        timing_cue_ids=[f"a{idx}"],
        source_cue_ids=[f"b{idx}"],
        raw_text=f"中文{idx}",
        normalized_text=f"中文{idx}",
        final_text=f"中文{idx}",
    )


def cue(idx: int, start: int, end: int, text: str) -> Cue:
    return Cue(id=f"c{idx}", index=idx, start_ms=start, end_ms=end, text=text, plain_text=text)


def group(idx: int, left: list[str], right: list[str]) -> AlignmentGroup:
    return AlignmentGroup(
        id=f"align-{idx:06d}",
        left_ids=left,
        right_ids=right,
        start_ms=1000,
        end_ms=3000,
        cost=0.2,
        confidence=0.9,
        kind=f"{len(left)}:{len(right)}",
    )


def fragment(
    fragment_id: str,
    source: str,
    text: str,
    disposition: str,
    *,
    targets: list[str] | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    start = source.index(text)
    result: dict[str, object] = {
        "id": fragment_id,
        "span": {"start": start, "end": start + len(text)},
        "text": text,
        "disposition": disposition,
        "target_unit_ids": targets or [],
    }
    if reason is not None:
        result["reason"] = reason
    return result


def test_partial_source_event_is_not_closed_by_one_final_ref() -> None:
    target = unit(1, 1000, 3000)
    source_text = "タイムパトロールだ 観念しろ"
    source = cue(1, 1000, 3000, source_text)

    result = reconcile_groups(
        [target],
        [source],
        [group(1, [target.id], [source.id])],
        fragment_decisions={
            source.id: [
                fragment(
                    "c1#call",
                    source_text,
                    "タイムパトロールだ",
                    "presented",
                    targets=[target.id],
                ),
                fragment("c1#command", source_text, "観念しろ", "unresolved"),
            ]
        },
    )

    assert result.pairs[0].source_text == "タイムパトロールだ"
    assert result.source_events[0].status == "presented_partial"
    assert result.coverage()["source_spoken_fragments_unresolved"] == 1
    assert result.coverage()["source_events_presented_partial"] == 1


def test_meaningful_short_source_defaults_to_unresolved() -> None:
    source = cue(1, 1000, 2000, "目が回る！")
    result = reconcile_groups([], [source], [group(1, [], [source.id])])

    assert result.source_fragments[0].disposition == "unresolved"
    assert result.source_events[0].status == "unresolved"
    assert result.coverage()["source_spoken_fragments_unresolved"] == 1


def test_explicit_nonpresented_fragment_requires_and_uses_reason() -> None:
    source_text = "あっ"
    source = cue(1, 1000, 2000, source_text)
    decisions = {
        source.id: [
            fragment(
                "c1#reaction",
                source_text,
                source_text,
                "parallel_reaction_omitted_with_reason",
                reason="Simultaneous reaction is intentionally folded from presentation.",
            )
        ]
    }
    result = reconcile_groups(
        [], [source], [group(1, [], [source.id])], fragment_decisions=decisions
    )

    assert result.source_events[0].status == "resolved_nonpresented"
    assert result.coverage()["source_spoken_fragments_unresolved"] == 0
    assert result.coverage()["missing_disposition_reasons"] == 0

    decisions[source.id][0].pop("reason")
    missing_reason = reconcile_groups(
        [], [source], [group(1, [], [source.id])], fragment_decisions=decisions
    )
    assert missing_reason.coverage()["missing_disposition_reasons"] == 1


def test_folded_fragment_can_reference_the_presentation_that_absorbed_it() -> None:
    target = unit(1, 1000, 2000)
    source_text = "呼んだ 重複説明"
    source = cue(1, 1000, 2000, source_text)
    result = reconcile_groups(
        [target],
        [source],
        [group(1, [target.id], [source.id])],
        fragment_decisions={
            source.id: [
                fragment(
                    "c1#presented",
                    source_text,
                    "呼んだ",
                    "presented",
                    targets=[target.id],
                ),
                fragment(
                    "c1#folded",
                    source_text,
                    "重複説明",
                    "folded_with_reason",
                    targets=[target.id],
                    reason="Meaning is already carried by the same presentation unit.",
                ),
            ]
        },
    )

    assert result.source_events[0].status == "presented_full"
    assert result.pairs[0].source_text == "呼んだ"
    assert not any(
        item["kind"] == "nonpresented-fragment-with-final-ref" for item in result.accounting_issues
    )


def test_fragment_cannot_leak_to_pair_owned_by_adjacent_source() -> None:
    targets = [unit(1, 1000, 2000), unit(2, 2000, 3000)]
    sources = [
        cue(1, 1000, 2000, "ちょ… ちょっと"),
        cue(2, 2000, 3000, "むちゃだよ そんな 定員オーバーだ 降りてくれ"),
    ]
    decisions = {
        sources[0].id: [
            fragment(
                "c1#speech",
                sources[0].plain_text,
                sources[0].plain_text,
                "presented",
                targets=[targets[1].id],
            )
        ]
    }
    result = reconcile_groups(
        targets,
        sources,
        [
            group(1, [targets[0].id], [sources[0].id]),
            group(2, [targets[1].id], [sources[1].id]),
        ],
        fragment_decisions=decisions,
    )

    assert result.coverage()["invalid_fragment_ownership"] == 1


def test_repeated_short_sources_keep_identity_and_expose_order_inversion() -> None:
    targets = [unit(1, 1000, 2000), unit(2, 2000, 3000)]
    sources = [cue(1, 1000, 1500, "うん"), cue(2, 2000, 2500, "うん")]
    result = reconcile_groups(
        targets,
        sources,
        [
            group(1, [targets[0].id], [sources[1].id]),
            group(2, [targets[1].id], [sources[0].id]),
        ],
    )

    assert {item.id for item in result.source_fragments} == {"c1#full", "c2#full"}
    assert result.coverage()["substantive_source_order_violations"] == 1


def test_simultaneous_identical_calls_keep_separate_refs_without_false_order_error() -> None:
    targets = [unit(1, 1000, 1800), unit(2, 1800, 2600)]
    sources = [cue(1, 1000, 2200, "ドラえもん！"), cue(2, 1050, 2250, "ドラえもん！")]
    result = reconcile_groups(
        targets,
        sources,
        [
            group(1, [targets[0].id], [sources[0].id]),
            group(2, [targets[1].id], [sources[1].id]),
        ],
    )

    assert [item.final_refs for item in result.source_fragments] == [
        ["pair-000001"],
        ["pair-000002"],
    ]
    assert result.coverage()["substantive_source_order_violations"] == 0


def test_invalid_final_ref_is_reported() -> None:
    target = unit(1, 1000, 2000)
    source = cue(1, 1000, 2000, "日本語")
    result = reconcile_groups(
        [target],
        [source],
        [group(1, [target.id], [source.id])],
        fragment_decisions={
            source.id: [
                fragment(
                    "c1#speech",
                    source.plain_text,
                    source.plain_text,
                    "presented",
                    targets=["jp-999999"],
                )
            ]
        },
    )

    assert result.coverage()["invalid_final_refs"] == 1
    assert result.pairs[0].operation == "unresolved"


def test_legacy_split_decisions_derive_complete_fragment_coverage() -> None:
    targets = [unit(1, 1000, 2000), unit(2, 2000, 3000)]
    source = cue(1, 1000, 3000, "A。そしてB。")
    result = reconcile_groups(
        targets,
        [source],
        [group(1, [item.id for item in targets], [source.id])],
        split_decisions={targets[0].id: "A。", targets[1].id: "そしてB。"},
    )

    assert [item.text for item in result.source_fragments] == ["A。", "そしてB。"]
    assert result.source_events[0].status == "presented_full"
    assert result.coverage()["source_spoken_fragments_unresolved"] == 0


def test_structured_fragments_drive_one_source_to_two_target_projection() -> None:
    targets = [unit(1, 1000, 2000), unit(2, 2000, 3000)]
    source_text = "これ 本物？ もちろんさ"
    source = cue(1, 1000, 3000, source_text)
    result = reconcile_groups(
        targets,
        [source],
        [group(1, [item.id for item in targets], [source.id])],
        fragment_decisions={
            source.id: [
                fragment(
                    "c1#question",
                    source_text,
                    "これ 本物？",
                    "presented",
                    targets=[targets[0].id],
                ),
                fragment(
                    "c1#answer",
                    source_text,
                    "もちろんさ",
                    "presented",
                    targets=[targets[1].id],
                ),
            ]
        },
    )

    assert [item.operation for item in result.pairs] == ["source-split", "source-split"]
    assert [item.source_text for item in result.pairs] == ["これ 本物？", "もちろんさ"]
    assert result.source_events[0].status == "presented_full"

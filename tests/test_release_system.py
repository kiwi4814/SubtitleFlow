from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from subtitleflow.alignment import align_cues
from subtitleflow.editorial import (
    TranslationQualityAssessment,
    editorial_context,
    policy_action,
)
from subtitleflow.evidence import evidence_grade
from subtitleflow.layout import block_geometry
from subtitleflow.models import AlignmentGroup, BranchUnit, ChangeRecord, Cue
from subtitleflow.reconciliation import reconcile_groups
from subtitleflow.roles import classify_event_role


def unit(idx: int, start: int, end: int, text: str = "中文") -> BranchUnit:
    return BranchUnit(
        id=f"jp-{idx:06d}",
        start_ms=start,
        end_ms=end,
        timing_cue_ids=[f"a{idx}"],
        source_cue_ids=[f"b{idx}"],
        raw_text=text,
        normalized_text=text,
        final_text=text,
    )


def cue(idx: int, start: int, end: int, text: str = "日本語") -> Cue:
    return Cue(id=f"c{idx}", index=idx, start_ms=start, end_ms=end, text=text, plain_text=text)


def group(left: list[str], right: list[str], kind: str, confidence: float = 0.9) -> AlignmentGroup:
    return AlignmentGroup(
        id="align-000001",
        left_ids=left,
        right_ids=right,
        start_ms=1000,
        end_ms=3000,
        cost=0.2,
        confidence=confidence,
        kind=kind,
    )


def styles() -> tuple[dict[str, str], dict[str, str], dict[str, float]]:
    zh = {"Fontsize": "60", "ScaleY": "105", "Outline": "2"}
    ja = {"Fontsize": "50", "ScaleY": "100", "Outline": "2"}
    layout = {
        "clean_bottom_anchor_ratio": 0.944,
        "bilingual_bottom_anchor_ratio": 0.9583,
        "song_bottom_anchor_ratio": 0.9583,
        "target_line_height_em": 1.12,
        "source_line_height_em": 1.12,
        "inter_language_gap_em": 0.24,
    }
    return zh, ja, layout


def test_human_preserve_blocks_style_only_rewrite() -> None:
    context = editorial_context(
        {
            "editorial": {
                "translation_provenance": "human-fansub",
                "translation_trust": "high",
                "editing_policy": "preserve",
            }
        }
    )
    assert policy_action(context, "fluency") == "block"
    assert policy_action(context, "mistranslation") == "review"


def test_human_proofread_allows_semantic_correction() -> None:
    context = editorial_context(
        {
            "editorial": {
                "translation_provenance": "human-fansub",
                "translation_trust": "unknown",
                "editing_policy": "proofread",
            }
        }
    )
    assert policy_action(context, "mistranslation") == "allow"
    assert policy_action(context, "fluency") == "allow"


def test_human_retranslate_allows_substantial_rewrite() -> None:
    context = editorial_context(
        {"editorial": {"translation_provenance": "human-fansub", "editing_policy": "retranslate"}}
    )
    assert policy_action(context, "substantial-rewrite") == "allow"
    assert policy_action(context, "full-retranslation") == "allow"


def test_official_provenance_does_not_lock_proofread() -> None:
    context = editorial_context(
        {
            "editorial": {
                "translation_provenance": "official",
                "translation_trust": "medium",
                "editing_policy": "proofread",
            }
        }
    )
    assert policy_action(context, "mistranslation") == "allow"


def test_user_policy_has_priority_over_auto_recommendation() -> None:
    config = {
        "editorial": {
            "editing_policy": "proofread",
            "quality_assessment": {
                "semantic_accuracy": 0.99,
                "terminology_consistency": 0.99,
                "fluency": 0.98,
                "omission_risk": 0.01,
                "mistranslation_risk": 0.01,
                "alignment_risk": 0.01,
                "confidence": 0.99,
            },
        }
    }
    context = editorial_context(config)
    assert context.effective_policy == "proofread"
    assert context.policy_source == "user-config"


def test_auto_requires_assessment_then_recommends_policy() -> None:
    assert editorial_context({"editorial": {"editing_policy": "auto"}}).assessment_required
    assessment = TranslationQualityAssessment(0.98, 0.96, 0.95, 0.03, 0.02, 0.05, confidence=0.9)
    config = {"editorial": {"editing_policy": "auto", "quality_assessment": assessment.to_dict()}}
    assert editorial_context(config).effective_policy == "preserve"


def test_evidence_conflict_is_primary_explicit_not_corroborated() -> None:
    assert (
        evidence_grade(primary_explicit=True, independent_support=True, secondary_conflict=True)
        == "B+"
    )
    assert (
        evidence_grade(primary_explicit=True, independent_support=True, secondary_conflict=False)
        == "A"
    )


def test_one_source_to_two_targets_requires_and_preserves_split_provenance() -> None:
    units = [unit(1, 1000, 2000), unit(2, 2000, 3000)]
    source = [cue(1, 1000, 3000, "A。そしてB。")]
    result = reconcile_groups(
        units,
        source,
        [group([units[0].id, units[1].id], [source[0].id], "2:1")],
        split_decisions={units[0].id: "A。", units[1].id: "そしてB。"},
    )
    assert [item.operation for item in result.pairs] == ["source-split", "source-split"]
    assert all(item.parent_source_cue_ids == [source[0].id] for item in result.pairs)


def test_two_sources_to_one_target_merges_with_all_source_ids() -> None:
    units = [unit(1, 1000, 3000)]
    source = [cue(1, 1000, 1800, "A。"), cue(2, 1800, 3000, "B。")]
    result = reconcile_groups(
        units, source, [group([units[0].id], [item.id for item in source], "1:2")]
    )
    pair = result.pairs[0]
    assert pair.operation == "source-merge"
    assert pair.source_text_cue_ids == ["c1", "c2"]
    assert "A。" in pair.source_text and "B。" in pair.source_text


def test_source_gap_never_generates_source_text() -> None:
    units = [unit(1, 1000, 2000)]
    result = reconcile_groups(units, [], [group([units[0].id], [], "unmatched-left", 0.0)])
    assert result.pairs[0].operation == "source-gap"
    assert result.pairs[0].source_text is None
    assert result.coverage()["fabricated"] == 0


def test_unresolved_source_split_does_not_duplicate_whole_source() -> None:
    units = [unit(1, 1000, 2000), unit(2, 2000, 3000)]
    source = [cue(1, 1000, 3000, "A。そしてB。")]
    result = reconcile_groups(
        units, source, [group([item.id for item in units], [source[0].id], "2:1")]
    )
    assert all(item.operation == "unresolved" for item in result.pairs)
    assert all(item.source_text is None for item in result.pairs)


def test_alignment_grouping_emits_semantic_risk_without_translation_verdict() -> None:
    left = [cue(1, 1000, 1600, "一"), cue(2, 1600, 2200, "二"), cue(3, 2200, 3000, "三")]
    right = [cue(9, 1000, 3000, "まとめ")]
    result = align_cues(left, right, max_group=3)
    assert any(item["risk"] == "n:m-alignment" for item in result.semantic_risks or [])
    assert not any("translation-error" in str(item) for item in result.semantic_risks or [])


def test_bilingual_1_plus_1_places_target_above_source() -> None:
    zh, ja, layout = styles()
    geometry = block_geometry(
        play_res_x=1920,
        play_res_y=1080,
        target_style=zh,
        source_style=ja,
        layout=layout,
        target_text="中文",
        source_text="日本語",
        mode="bilingual",
    )
    assert geometry.target_y < geometry.source_y


def test_bilingual_1_plus_2_keeps_target_above_all_source_rows() -> None:
    zh, ja, layout = styles()
    geometry = block_geometry(
        play_res_x=1920,
        play_res_y=1080,
        target_style=zh,
        source_style=ja,
        layout=layout,
        target_text="中文",
        source_text="日本語一\n日本語二",
        mode="bilingual",
    )
    assert geometry.target_y < geometry.source_y - geometry.source_height


def test_clean_geometry_does_not_reserve_japanese_row() -> None:
    zh, ja, layout = styles()
    clean = block_geometry(
        play_res_x=1920,
        play_res_y=1080,
        target_style=zh,
        source_style=None,
        layout=layout,
        target_text="中文",
        mode="clean",
    )
    bilingual = block_geometry(
        play_res_x=1920,
        play_res_y=1080,
        target_style=zh,
        source_style=ja,
        layout=layout,
        target_text="中文",
        source_text="日本語",
        mode="bilingual",
    )
    assert clean.target_y > bilingual.target_y
    assert clean.source_y is None


def test_op_bilingual_uses_same_order_contract() -> None:
    zh, ja, layout = styles()
    geometry = block_geometry(
        play_res_x=1920,
        play_res_y=1080,
        target_style=zh,
        source_style=ja,
        layout=layout,
        target_text="中文歌词",
        source_text="日本語歌詞",
        mode="bilingual",
        semantic_role="song-op",
    )
    assert geometry.target_y < geometry.source_y


def test_op_two_source_rows_cannot_invert() -> None:
    zh, ja, layout = styles()
    geometry = block_geometry(
        play_res_x=1920,
        play_res_y=1080,
        target_style=zh,
        source_style=ja,
        layout=layout,
        target_text="中文歌词",
        source_text="日本語一\n日本語二",
        mode="bilingual",
        semantic_role="song-op",
    )
    assert geometry.target_y < geometry.source_y - geometry.source_height


def test_source_style2_is_not_implicitly_screen_text_or_top() -> None:
    role = classify_event_role(style="Style2", text="普通对白")
    assert role.role == "dialogue"
    assert role.position_intent == "preserve"


def test_screen_text_style_is_role_evidence_not_forced_top() -> None:
    role = classify_event_role(style="Sign", text="吊销驾照")
    assert role.role == "screen-text"
    assert role.position_intent == "preserve"


def test_translator_note_and_credit_are_excluded_by_default() -> None:
    role = classify_event_role(style="Default", text="字幕制作：https://example.com/fansub")
    assert role.role == "staff-credit"
    assert not role.include_by_default


def test_change_record_can_carry_full_evidence_audit() -> None:
    record = ChangeRecord(
        kind="human-approved-semantic",
        before="Y",
        after="X",
        reason="Japanese source is explicit",
        primary_evidence={"role": "C", "supports": "X"},
        secondary_evidence=[{"role": "A", "supports": "Y"}],
        authority_domain="semantic",
        evidence_grade="B+",
        source_conflicts=["English supports Y", "Original Chinese differs"],
        confidence=0.96,
        review_status="approved",
        final_decision="approve",
    )
    data = record.to_dict()
    assert data["before"] == "Y" and data["after"] == "X"
    assert data["evidence_grade"] == "B+"
    assert data["source_conflicts"]


def test_kiwi_style_profile_copies_do_not_drift() -> None:
    repo = Path(__file__).resolve().parents[1]
    assert (repo / "styles/kiwi-collector-v1.json").read_bytes() == (
        repo / "src/subtitleflow/styles/kiwi-collector-v1.json"
    ).read_bytes()


def test_real_libass_synthetic_renderer_smoke(tmp_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg not installed")
    filters = subprocess.run(
        [ffmpeg, "-hide_banner", "-filters"], text=True, capture_output=True, check=True
    ).stdout
    if " ass " not in filters:
        pytest.skip("ffmpeg has no libass filter")
    ass = tmp_path / "specimen.ass"
    ass.write_text(
        """[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: ZH,DejaVu Sans,60,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,2,10,10,0,1\nStyle: JA,DejaVu Sans,50,&H0000FFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,0,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:01.00,0:00:03.00,ZH,,0,0,0,,{\\an2\\pos(960,900)}ZH\nDialogue: 0,0:00:01.00,0:00:03.00,JA,,0,0,0,,{\\an2\\pos(960,1030)}JA line 1\\NJA line 2\n""",
        encoding="utf-8",
    )
    out = tmp_path / "frame.png"
    proc = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "verbose",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=1920x1080:r=1:d=0.1",
            "-vf",
            f"setpts=PTS+2/TB,ass={ass}",
            "-frames:v",
            "1",
            "-y",
            str(out),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    assert out.is_file() and out.stat().st_size > 0
    assert "fontselect" in proc.stderr.casefold()

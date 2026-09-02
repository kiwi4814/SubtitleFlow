from subtitleflow.alignment import editable_cues
from subtitleflow.cue_views import evidence_cues
from subtitleflow.models import Cue
from subtitleflow.roles import classify_event_role


def test_protected_positioned_dialogue_is_evidence_but_not_editable():
    cue = Cue(
        id="ass-000001",
        index=0,
        start_ms=1000,
        end_ms=2000,
        text=r"{\pos(960,900)}日本語",
        plain_text="日本語",
        protected=True,
        protected_reason=r"complex ASS tag \pos(",
        semantic_role="dialogue",
    )

    assert editable_cues([cue]) == []
    assert evidence_cues([cue]) == [cue]


def test_drawing_credit_and_accessibility_sfx_are_not_semantic_evidence():
    drawing = Cue(
        id="ass-000001",
        index=0,
        start_ms=1000,
        end_ms=2000,
        text=r"{\p1}m 0 0 l 10 10",
        plain_text="m 0 0 l 10 10",
        protected=True,
        protected_reason="ASS drawing mode",
        semantic_role="protected-fx",
    )
    credit = Cue(
        id="ass-000002",
        index=1,
        start_ms=2000,
        end_ms=3000,
        text="字幕制作：Example",
        plain_text="字幕制作：Example",
        protected=False,
        semantic_role="staff-credit",
        include_in_release=False,
    )
    sfx = Cue(
        id="ass-000003",
        index=2,
        start_ms=3000,
        end_ms=4000,
        text="(雷鳴)",
        plain_text="(雷鳴)",
        protected=True,
        protected_reason=r"complex ASS tag \pos(",
        semantic_role="accessibility-sfx",
    )

    assert evidence_cues([drawing, credit, sfx]) == []


def test_accessibility_sfx_classifier_is_conservative():
    assert classify_event_role(style="Default", text="♬～").role == "accessibility-sfx"
    assert classify_event_role(style="Default", text="(鳴き声)").role == "accessibility-sfx"
    assert classify_event_role(style="Default", text="(雷鳴)").role == "accessibility-sfx"
    assert classify_event_role(style="Default", text="(ｻｲﾚﾝ)").role == "accessibility-sfx"

    assert classify_event_role(style="Default", text="(スネ夫)").role == "dialogue"
    assert classify_event_role(style="Default", text="(一同)えっ？").role == "dialogue"
    assert classify_event_role(style="Default", text="ピー助！").role == "dialogue"


def test_ruby_style_is_preserved_as_annotation_not_semantic_dialogue():
    classification = classify_event_role(style="Rubi", text="ももたろうじるし")
    assert classification.role == "annotation"
    assert classification.basis == "ruby-style"

    ruby = Cue(
        id="ass-000004",
        index=3,
        start_ms=4000,
        end_ms=5000,
        text="ももたろうじるし",
        plain_text="ももたろうじるし",
        style="Rubi",
        protected=True,
        protected_reason=r"complex ASS tag \pos(",
        semantic_role=classification.role,
    )
    assert evidence_cues([ruby]) == []

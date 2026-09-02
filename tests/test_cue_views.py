from subtitleflow.alignment import editable_cues
from subtitleflow.cue_views import evidence_cues
from subtitleflow.models import Cue


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


def test_drawing_and_credit_are_not_semantic_evidence():
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

    assert evidence_cues([drawing, credit]) == []

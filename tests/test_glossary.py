from subtitleflow.glossary import TermRule, apply_glossary, forbidden_hits, terminology_hits


def test_glossary_safe_and_context_rules() -> None:
    rules = [
        TermRule("doraemon", "哆啦A梦", ["小叮当"], True, False, ["tw", "jp"], ["小叮当"]),
        TermRule("bell", "哆啦美", ["叮铃"], False, True, ["tw", "jp"], ["叮铃"]),
    ]
    text, changes, reviews = apply_glossary("小叮当和叮铃", rules, "jp")
    assert text == "哆啦A梦和叮铃"
    assert len(changes) == 1
    assert reviews[0]["alias"] == "叮铃"
    assert forbidden_hits(text, rules, "jp")[0]["alias"] == "叮铃"


def test_m01_locked_time_cloth_canon_is_deterministic() -> None:
    rules = [
        TermRule(
            "time-cloth",
            "时光布",
            ["时光包巾"],
            True,
            False,
            ["jp"],
            ["时光包巾"],
            source_forms=["タイムふろしき"],
            enforcement="locked",
        )
    ]

    text, changes, reviews = apply_glossary("拿出时光包巾", rules, "jp")
    assert text == "拿出时光布"
    assert len(changes) == 1
    assert reviews == []
    assert terminology_hits("拿出时光包巾", rules, "jp")[0]["kind"] == "forbidden"


def test_unfrozen_long_tail_term_is_not_rewritten_by_core() -> None:
    text, changes, reviews = apply_glossary("进入露营舱", [], "jp")

    assert text == "进入露营舱"
    assert changes == []
    assert reviews == []
    assert terminology_hits(text, [], "jp") == []

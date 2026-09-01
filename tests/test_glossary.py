from subtitleflow.glossary import TermRule, apply_glossary, forbidden_hits


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

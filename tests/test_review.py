from pathlib import Path

from conftest import write_ass
from subtitleflow.canon import add_term
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.review import decide_candidate, import_proposals, pending_count
from subtitleflow.workfile import build_all_workfiles, load_workfile
from subtitleflow.workspace import add_source, create_project, create_title, title_paths


def bootstrap(tmp_path: Path, sample_cues):
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    paths = title_paths(tmp_path, "demo", "movie")
    a = write_ass(tmp_path / "a.ass", sample_cues)
    b = write_ass(tmp_path / "b.ass", sample_cues)
    c = write_ass(
        tmp_path / "c.ass",
        [(s, e, f"日本語{idx}") for idx, (s, e, _t) in enumerate(sample_cues, start=1)],
    )
    d = write_ass(tmp_path / "d.ass", sample_cues)
    for role, path in [("A", a), ("B", b), ("C", c), ("D", d)]:
        add_source(paths, role, path)
    add_term(
        paths,
        scope="project",
        term_id="doraemon",
        canonical="哆啦A梦",
        aliases=["小叮当"],
        auto_replace=True,
        context_sensitive=False,
        branches=["tw", "jp"],
        notes="test",
    )
    # Avoid OpenCC dependency in unit tests; input is already simplified.
    config = read_json(paths.title_config)
    config["tw_branch"]["traditional_to_simplified"] = False
    write_json(paths.title_config, config)
    normalize_all(paths)
    build_all_workfiles(paths)
    return paths


def test_review_approval_applies_only_after_decision(tmp_path: Path, sample_cues) -> None:
    paths = bootstrap(tmp_path, sample_cues)
    work = load_workfile(paths, "jp")
    unit = work.units[0]
    proposal = tmp_path / "proposal.json"
    write_json(
        proposal,
        {
            "branch": "jp",
            "unit_id": unit.id,
            "original_text": unit.final_text,
            "proposed_text": unit.final_text + "！",
            "reason": "测试语义修改",
            "confidence": 0.99,
            "severity": "high",
        },
    )
    imported = import_proposals(paths, proposal)
    assert pending_count(paths) == 1
    assert load_workfile(paths, "jp").units[0].final_text == unit.final_text
    decide_candidate(paths, imported[0].candidate_id, "approve")
    assert pending_count(paths) == 0
    assert load_workfile(paths, "jp").units[0].final_text.endswith("！")

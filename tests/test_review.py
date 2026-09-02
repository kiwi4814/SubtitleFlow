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


def test_review_approval_rejects_stale_source_evidence_even_when_text_is_unchanged(
    tmp_path: Path, sample_cues
) -> None:
    import pytest

    from subtitleflow.errors import GateError
    from subtitleflow.workfile import save_workfile

    paths = bootstrap(tmp_path, sample_cues)
    work = load_workfile(paths, "jp")
    unit = work.units[0]
    proposal = tmp_path / "proposal-stale-evidence.json"
    write_json(
        proposal,
        {
            "branch": "jp",
            "unit_id": unit.id,
            "original_text": unit.final_text,
            "proposed_text": unit.final_text + "！",
            "reason": "测试证据绑定",
            "confidence": 0.9,
        },
    )
    imported = import_proposals(paths, proposal)

    changed = load_workfile(paths, "jp")
    changed.units[0].source_text = "別の日本語証拠"
    # final_text remains exactly the same; old protection based on original_text alone
    # would have allowed this proposal to be approved against different evidence.
    save_workfile(paths, changed)

    with pytest.raises(GateError, match="timing or source evidence changed"):
        decide_candidate(paths, imported[0].candidate_id, "approve")


def test_repo_proposal_is_archived_after_import(tmp_path: Path, sample_cues) -> None:
    paths = bootstrap(tmp_path, sample_cues)
    unit = load_workfile(paths, "jp").units[0]
    proposal = paths.review_proposals / "semantic-proposal.json"
    write_json(
        proposal,
        {
            "branch": "jp",
            "unit_id": unit.id,
            "original_text": unit.final_text,
            "proposed_text": unit.final_text + "！",
            "reason": "archive provenance",
            "confidence": 0.8,
        },
    )
    imported = import_proposals(paths, proposal)
    assert not proposal.exists()
    archived = list((paths.review_proposals / "_imported").glob("*.json"))
    assert len(archived) == 1
    assert imported[0].proposal_source == str(archived[0].relative_to(paths.title)).replace(
        "\\", "/"
    )
    assert imported[0].proposal_sha256


def test_review_approval_rejects_stale_canon_context(tmp_path: Path, sample_cues) -> None:
    import pytest

    from subtitleflow.errors import GateError

    paths = bootstrap(tmp_path, sample_cues)
    unit = load_workfile(paths, "jp").units[0]
    proposal = tmp_path / "proposal-stale-canon.json"
    write_json(
        proposal,
        {
            "branch": "jp",
            "unit_id": unit.id,
            "original_text": unit.final_text,
            "proposed_text": unit.final_text + "！",
            "reason": "canon context binding",
            "confidence": 0.9,
        },
    )
    imported = import_proposals(paths, proposal)
    characters = read_json(paths.project_canon / "characters.json")
    characters["characters"].append({"name": "new-context"})
    write_json(paths.project_canon / "characters.json", characters)

    with pytest.raises(GateError, match="canon, research, or source manifest changed"):
        decide_candidate(paths, imported[0].candidate_id, "approve")

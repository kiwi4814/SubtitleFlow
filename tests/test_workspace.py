from pathlib import Path

import pytest
from conftest import write_ass

from subtitleflow.errors import SourceIntegrityError
from subtitleflow.workspace import (
    add_source,
    create_project,
    create_title,
    title_paths,
    verify_sources,
)


def test_source_is_hashed_and_mutation_detected(tmp_path: Path, sample_cues) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    source = write_ass(tmp_path / "source.ass", sample_cues)
    paths = title_paths(tmp_path, "demo", "movie")
    add_source(paths, "A", source)
    assert verify_sources(paths)["ok"] is True
    stored = paths.source / "A.ass"
    stored.chmod(0o644)
    stored.write_text(stored.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(SourceIntegrityError):
        verify_sources(paths)


def test_source_replace_preserves_unique_hashed_archive_and_blocks_tampered_source(
    tmp_path: Path, sample_cues
) -> None:
    from subtitleflow.io import read_json

    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    paths = title_paths(tmp_path, "demo", "movie")
    first = write_ass(tmp_path / "first.ass", sample_cues)
    second = write_ass(tmp_path / "second.ass", [(0, 1000, "second")])
    third = write_ass(tmp_path / "third.ass", [(0, 1000, "third")])

    first_record = add_source(paths, "S", first)
    add_source(paths, "S", second, replace=True)
    manifest = read_json(paths.manifest)
    history = manifest["history"]
    assert len(history) == 1
    archived = paths.title / history[0]["replaced"]["archived_path"]
    assert archived.is_file()
    assert history[0]["replaced"]["archived_sha256"] == first_record["sha256"]

    # Mutating the active immutable source must be detected before a replacement can hide it.
    active = paths.source / "S.ass"
    active.chmod(0o644)
    active.write_text(active.read_text(encoding="utf-8") + "\nTAMPERED", encoding="utf-8")
    with pytest.raises(SourceIntegrityError):
        add_source(paths, "S", third, replace=True)
    assert len(read_json(paths.manifest)["history"]) == 1

from pathlib import Path

import pytest

from conftest import write_ass
from subtitleflow.errors import SourceIntegrityError
from subtitleflow.workspace import add_source, create_project, create_title, title_paths, verify_sources


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

from pathlib import Path

from subtitleflow.media import expand_media_path


def test_expand_media_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    assert expand_media_path("${MEDIA_ROOT}/movie.mkv") == (tmp_path / "movie.mkv").resolve()

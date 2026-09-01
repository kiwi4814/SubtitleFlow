from __future__ import annotations

import tomllib
from pathlib import Path

import subtitleflow


def _pyproject() -> dict:
    return tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))


def test_pep639_license_metadata_has_no_legacy_license_classifier() -> None:
    project = _pyproject()['project']
    assert project['license'] == 'MIT'
    assert all(not item.startswith('License ::') for item in project.get('classifiers', []))


def test_package_version_matches_project_metadata() -> None:
    project = _pyproject()['project']
    assert subtitleflow.__version__ == project['version']


def test_bundled_style_profile_is_packaged_and_versioned() -> None:
    repo = Path(__file__).resolve().parents[1]
    profile = repo / 'src' / 'subtitleflow' / 'styles' / 'kiwi-collector-v1.json'
    assert profile.is_file()
    import json
    data = json.loads(profile.read_text(encoding='utf-8'))
    assert data['id'] == 'kiwi-collector-v1'
    assert data['styles']['SF-ZH']['Fontname'] == 'WenQuanYi Micro Hei'
    assert data['styles']['SF-JA']['PrimaryColour'] == '&H000E95CE'
    assert data['event_overrides']['SF-ZH'] == r'\blur2'


def test_repository_contains_no_font_binaries() -> None:
    repo = Path(__file__).resolve().parents[1]
    forbidden = {'.ttf', '.otf', '.ttc', '.otc'}
    binaries = [path for path in repo.rglob('*') if path.is_file() and path.suffix.lower() in forbidden]
    assert all(path.is_relative_to(repo / 'fonts' / 'local') for path in binaries)

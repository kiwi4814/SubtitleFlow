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

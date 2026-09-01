from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from conftest import write_ass
from subtitleflow.compile import compile_all
from subtitleflow.fonts import audit_fonts, install_registered_fonts
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.util import sha256_file
from subtitleflow.workfile import build_all_workfiles
from subtitleflow.workspace import (
    add_source,
    configure_workflow_profile,
    create_project,
    create_title,
    title_paths,
)


def _make_test_font(path: Path, family: str) -> Path:
    pytest.importorskip("fontTools")
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    fb = FontBuilder(1024, isTTF=True)
    glyph_order = [".notdef", "space", "A"]
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap({32: "space", 65: "A"})
    glyphs = {}
    for name in glyph_order:
        pen = TTGlyphPen(None)
        glyphs[name] = pen.glyph()
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({name: (600, 0) for name in glyph_order})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable(
        {
            "familyName": family,
            "styleName": "Regular",
            "fullName": family,
            "uniqueFontIdentifier": f"SubtitleFlow-{family}",
            "psName": "SubtitleFlowTest-Regular",
            "version": "Version 1.0",
        }
    )
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    fb.setupMaxp()
    path.parent.mkdir(parents=True, exist_ok=True)
    fb.save(path)
    return path


def _write_registry(repo: Path, *, font: Path, canonical_file: str, family: str, aliases: list[str]) -> Path:
    registry = repo / "fonts" / "font-registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        registry,
        {
            "schema_version": 1,
            "id": "test-registry",
            "fonts": [
                {
                    "id": "dialogue",
                    "canonical_file": canonical_file,
                    "family": family,
                    "aliases": aliases,
                    "internal_names": aliases,
                    "postscript": "SubtitleFlowTest-Regular",
                    "version": "Version 1.0",
                    "sha256": sha256_file(font),
                    "size": font.stat().st_size,
                    "mime_type": "font/ttf",
                    "roles": ["zh_dialogue"],
                    "license": {"project_bundling": "disabled"},
                }
            ],
        },
    )
    return registry


def test_v030_default_registry_freezes_verified_user_font_identities() -> None:
    repo = Path(__file__).resolve().parents[1]
    data = json.loads((repo / "fonts" / "font-registry.json").read_text(encoding="utf-8"))
    assert data["id"] == "subtitleflow-default-fonts-v1"
    expected = {
        "dialogue": (
            "WenQuanYi Micro Hei",
            "wqy-microhei.ttc",
            "e4bca8df123ce01b104780f576ea1a58b9a5ff1662a91124b6d3180cb6c88212",
        ),
        "annotation": (
            "Source Han Sans CN Heavy",
            "SourceHanSansCN-Heavy.otf",
            "88c749b0a54a0800124ded6544e399302ed224aa49992ea364b88769f825c54c",
        ),
        "movie_title": (
            "CloudZongYiGBK",
            "Reeji-CloudZongYiGBK.ttf",
            "cdad5e1446c45a472fe085f99a661e2dbaa035cc9c3f5fb80efee8744f92f4d1",
        ),
        "screen_text": (
            "方正粗圆_GBK",
            "FZY4K.TTF",
            "c071e0e91406af290cfbb495c42ae56a36cca7a501c11cb6613893d5adb951c0",
        ),
        "formal_screen_text": (
            "Source Han Serif CN",
            "SourceHanSerifCN-Regular.otf",
            "3754ea669c530e2473354f8f6d9f79680a44d7e26ec7d00eeabee4a7e0753c5d",
        ),
    }
    actual = {
        entry["id"]: (entry["family"], entry["canonical_file"], entry["sha256"])
        for entry in data["fonts"]
    }
    assert actual == expected
    assert all(entry["license"]["project_bundling"] == "disabled" for entry in data["fonts"])


def test_font_install_matches_by_sha_and_renames_to_registry_canonical_file(tmp_path: Path) -> None:
    source_font = _make_test_font(tmp_path / "source" / "ugly-name.ttf", "Legacy Family")
    _write_registry(
        tmp_path,
        font=source_font,
        canonical_file="Canonical.ttf",
        family="Canonical Family",
        aliases=["Legacy Family"],
    )
    archive = tmp_path / "fonts.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(source_font, arcname="#U4e71#U7801.ttf")

    report = install_registered_fonts(tmp_path, archive)
    installed = tmp_path / "fonts" / "local" / "Canonical.ttf"
    assert report["ok"] is True
    assert installed.is_file()
    assert sha256_file(installed) == sha256_file(source_font)
    assert report["installed"][0]["action"] == "installed"
    assert report["verification"]["installed"][0]["metadata_verified"] is True


def test_font_audit_uses_registry_alias_but_freezes_canonical_attachment_name(tmp_path: Path) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='subtitleflow-test'\nversion='0'\n", encoding="utf-8"
    )
    source_font = _make_test_font(tmp_path / "source-font.ttf", "文泉驿微米黑")
    _write_registry(
        tmp_path,
        font=source_font,
        canonical_file="wqy-microhei.ttf",
        family="WenQuanYi Micro Hei",
        aliases=["文泉驿微米黑"],
    )
    local_font = tmp_path / "fonts" / "local" / "wqy-microhei.ttf"
    local_font.parent.mkdir(parents=True, exist_ok=True)
    local_font.write_bytes(source_font.read_bytes())

    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    paths = title_paths(tmp_path, "demo", "movie")
    config = read_json(paths.title_config)
    configure_workflow_profile(config, "single")
    write_json(paths.title_config, config)
    add_source(
        paths,
        "S",
        write_ass(tmp_path / "single.ass", [("0:00:01.00", "0:00:02.00", "字幕")]),
    )
    normalize_all(paths)
    build_all_workfiles(paths)
    compile_all(paths)

    report = audit_fonts(paths)
    assert report["ok"] is True
    assert report["registry"]["id"] == "test-registry"
    assert report["attachments"][0]["families"] == ["WenQuanYi Micro Hei"]
    assert report["attachments"][0]["attachment_name"] == "wqy-microhei.ttf"
    assert report["attachments"][0]["registry"]["id"] == "dialogue"
    assert "文泉驿微米黑" in report["attachments"][0]["metadata"]["families"]


def test_registry_exact_sha_resolves_without_fonttools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='subtitleflow-test'\nversion='0'\n", encoding="utf-8"
    )
    source_font = _make_test_font(tmp_path / "source-font.ttf", "Legacy Family")
    _write_registry(
        tmp_path,
        font=source_font,
        canonical_file="Canonical.ttf",
        family="Canonical Family",
        aliases=["Legacy Family"],
    )
    local_font = tmp_path / "fonts" / "local" / "Canonical.ttf"
    local_font.parent.mkdir(parents=True, exist_ok=True)
    local_font.write_bytes(source_font.read_bytes())

    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    paths = title_paths(tmp_path, "demo", "movie")
    config = read_json(paths.title_config)
    configure_workflow_profile(config, "single")
    write_json(paths.title_config, config)
    add_source(
        paths,
        "S",
        write_ass(tmp_path / "single.ass", [("0:00:01.00", "0:00:02.00", "字幕")]),
    )
    normalize_all(paths)
    build_all_workfiles(paths)
    compile_all(paths)
    # Force the generated dialogue style to request the custom registry family.
    compiled = paths.release / "movie.zh-CN.ass"
    compiled.write_text(
        compiled.read_text(encoding="utf-8").replace("WenQuanYi Micro Hei", "Canonical Family"),
        encoding="utf-8",
    )
    monkeypatch.setattr("subtitleflow.fonts.fonttools_available", lambda: False)

    report = audit_fonts(paths, write_report=False)
    assert report["ok"] is True
    assert report["attachments"][0]["attachment_name"] == "Canonical.ttf"
    assert report["attachments"][0]["sha256"] == sha256_file(source_font)
    assert report["attachments"][0]["metadata_verified"] is False

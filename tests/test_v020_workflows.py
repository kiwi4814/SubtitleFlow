from __future__ import annotations

from pathlib import Path

import pytest

from conftest import ASS_HEADER, ass_dialogue, write_ass
from subtitleflow.compile import compile_all
from subtitleflow.errors import GateError
from subtitleflow.fonts import audit_fonts, referenced_font_families, require_font_attachments
from subtitleflow.formats.ass import parse_ass
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.release import create_release_manifest
from subtitleflow.remux import build_remux_command
from subtitleflow.style import ass_style_values, event_override_tag
from subtitleflow.workfile import build_all_workfiles, load_workfile
from subtitleflow.workspace import (
    add_source,
    configure_workflow_profile,
    create_project,
    create_title,
    title_paths,
)
from subtitleflow.qa import run_all_qa


def _repo(tmp_path: Path):
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='subtitleflow-test'\nversion='0'\n", encoding="utf-8"
    )
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    return title_paths(tmp_path, "demo", "movie")


def _set_profile(paths, profile: str) -> None:
    config = read_json(paths.title_config)
    configure_workflow_profile(config, profile)
    write_json(paths.title_config, config)


def _make_test_font(path: Path, family: str = "文泉驿微米黑") -> Path:
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
            "fullName": f"{family} Regular",
            "uniqueFontIdentifier": "SubtitleFlowTestFont",
            "psName": "SubtitleFlowTestFont-Regular",
            "version": "Version 1.0",
        }
    )
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    fb.setupMaxp()
    path.parent.mkdir(parents=True, exist_ok=True)
    fb.save(path)
    return path


def test_single_profile_keeps_self_timing_and_uses_final_kiwi_style(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _set_profile(paths, "single")
    source = write_ass(
        tmp_path / "single.ass",
        [
            ("0:00:01.23", "0:00:03.45", "第一句"),
            ("0:00:04.56", "0:00:06.78", "第二句"),
        ],
    )
    add_source(paths, "S", source)
    normalize_all(paths)
    build_all_workfiles(paths)
    work = load_workfile(paths, "clean")
    assert [(unit.start_ms, unit.end_ms) for unit in work.units] == [(1230, 3450), (4560, 6780)]
    assert work.metadata["self_contained_timing"] is True
    assert work.metadata["source_assisted"] is False

    outputs = compile_all(paths)
    compiled = Path(outputs["clean"])
    text = compiled.read_text(encoding="utf-8")
    assert "Style: SF-ZH,文泉驿微米黑,60,&H00D2D2D2" in text
    assert r"{\blur2}第一句" in text
    style = ass_style_values(paths, "SF-ZH")
    assert style["ScaleY"] == "105"
    assert style["Outline"] == "2"
    assert style["Shadow"] == "0"
    assert event_override_tag(paths, "SF-ZH") == r"\blur2"


def test_source_assisted_profile_adds_source_evidence_without_retiming(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _set_profile(paths, "source-assisted")
    s = write_ass(
        tmp_path / "s.ass",
        [("0:00:01.00", "0:00:03.00", "你好"), ("0:00:03.10", "0:00:05.00", "走吧")],
    )
    c = write_ass(
        tmp_path / "c.ass",
        [("0:00:01.12", "0:00:03.12", "こんにちは"), ("0:00:03.22", "0:00:05.12", "行こう")],
    )
    add_source(paths, "S", s)
    add_source(paths, "C", c)
    normalize_all(paths)
    build_all_workfiles(paths)
    work = load_workfile(paths, "clean")
    assert [(unit.start_ms, unit.end_ms) for unit in work.units] == [(1000, 3000), (3100, 5000)]
    assert work.metadata["source_assisted"] is True
    assert [unit.source_text for unit in work.units] == ["こんにちは", "行こう"]


def test_source_assisted_profile_requires_c(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _set_profile(paths, "source-assisted")
    add_source(paths, "S", write_ass(tmp_path / "s.ass", [("0:00:01.00", "0:00:02.00", "字幕")]))
    normalize_all(paths)
    with pytest.raises(GateError, match="missing source roles"):
        build_all_workfiles(paths)


def test_hybrid_preserves_plain_special_style_without_complex_tags(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _set_profile(paths, "single")
    special_header = ASS_HEADER.replace(
        "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,40,40,50,1",
        "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,40,40,50,1\n"
        "Style: Note,Arial,40,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,8,40,40,40,1",
    )
    source = tmp_path / "hybrid.ass"
    source.write_text(
        special_header
        + ass_dialogue("0:00:01.00", "0:00:03.00", "普通对白")
        + "\n"
        + ass_dialogue("0:00:02.00", "0:00:04.00", "顶部注释", style="Note")
        + "\n",
        encoding="utf-8",
    )
    add_source(paths, "S", source)
    normalize_all(paths)
    normalized = read_json(paths.normalized / "S.json")
    note = next(cue for cue in normalized["cues"] if cue["style"] == "Note")
    assert note["protected"] is True
    assert "hybrid-preserved source style" in note["protected_reason"]
    build_all_workfiles(paths)
    work = load_workfile(paths, "clean")
    assert [unit.final_text for unit in work.units] == ["普通对白"]
    output = Path(compile_all(paths)["clean"])
    doc = parse_ass(output)
    assert any(event.fields.get("Style") == "Note" and "顶部注释" in event.raw_line for event in doc.events)


def test_font_reference_scanner_normalizes_vertical_font_prefix(tmp_path: Path) -> None:
    source = tmp_path / "fonts.ass"
    source.write_text(
        ASS_HEADER.replace("Style: Default,Arial,48", "Style: Default,@方正粗圆_GBK,48")
        + ass_dialogue("0:00:01.00", "0:00:02.00", r"{\fn思源宋体 CN}测试")
        + "\n",
        encoding="utf-8",
    )
    refs = referenced_font_families(source)
    assert "方正粗圆_GBK" in refs
    assert "思源宋体 CN" in refs
    assert all(not family.startswith("@") for family in refs)


def test_font_audit_release_freezes_sha_and_remux_uses_modern_attachment_options(tmp_path: Path) -> None:
    paths = _repo(tmp_path)
    _set_profile(paths, "single")
    source = write_ass(tmp_path / "single.ass", [("0:00:01.00", "0:00:03.00", "字幕")])
    add_source(paths, "S", source)
    font = _make_test_font(tmp_path / "fonts" / "local" / "wqy-microhei.ttf")
    write_json(
        tmp_path / "fonts" / "font-map.json",
        {"schema_version": 1, "families": {"文泉驿微米黑": ["local/wqy-microhei.ttf"]}},
    )
    config = read_json(paths.title_config)
    config["quality_gates"].update(
        {"require_research": False, "require_semantic_qa": False, "require_visual_qa": False}
    )
    write_json(paths.title_config, config)

    normalize_all(paths)
    build_all_workfiles(paths)
    compile_all(paths)
    report = audit_fonts(paths)
    assert report["ok"] is True
    assert len(report["attachments"]) == 1
    assert report["attachments"][0]["families"] == ["文泉驿微米黑"]
    assert report["attachments"][0]["mime_type"] == "font/ttf"

    qa = run_all_qa(paths)
    assert qa["ok"] is True
    manifest = create_release_manifest(paths)
    frozen = manifest["font_attachments"]
    assert len(frozen) == 1
    assert frozen[0]["attachment_name"] == "wqy-microhei.ttf"

    cmd = build_remux_command(
        video=Path("/tmp/video.mkv"),
        output=Path("/tmp/out.mkv"),
        clean_ass=paths.release / "movie.zh-CN.ass",
        font_attachments=frozen,
    )
    assert "--attachment-mime-type" in cmd
    assert "font/ttf" in cmd
    assert "--attachment-name" in cmd
    assert "wqy-microhei.ttf" in cmd
    assert "--attach-file" in cmd

    font.write_bytes(font.read_bytes() + b"changed")
    with pytest.raises(GateError, match="changed after audit"):
        require_font_attachments(paths)

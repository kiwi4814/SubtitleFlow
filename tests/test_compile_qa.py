import re
from pathlib import Path

from conftest import ass_dialogue, write_ass

from subtitleflow.canon import add_term
from subtitleflow.compile import compile_all
from subtitleflow.formats.ass import parse_ass
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.qa import run_all_qa
from subtitleflow.release import create_release_manifest
from subtitleflow.workfile import build_all_workfiles
from subtitleflow.workspace import add_source, create_project, create_title, title_paths

_POS_Y_RE = re.compile(r"\\pos\([^,]+,\s*([-+]?\d+(?:\.\d+)?)\)")


def _disable_external_release_gates(paths) -> None:
    config = read_json(paths.title_config)
    config["tw_branch"]["traditional_to_simplified"] = False
    config["quality_gates"] = {
        "require_research": False,
        "require_semantic_qa": False,
        "require_visual_qa": False,
        "require_fonts": False,
    }
    config["fonts"]["require_for_release"] = False
    write_json(paths.title_config, config)


def _style_font_size(text: str, style_name: str) -> float:
    style_format: list[str] = []
    for line in text.splitlines():
        if line.lstrip().casefold().startswith("format:") and "Fontsize" in line:
            fields = [item.strip() for item in line.partition(":")[2].split(",")]
            if "Name" in fields and "Fontsize" in fields:
                style_format = fields
        elif line.lstrip().casefold().startswith("style:") and style_format:
            values = [item.strip() for item in line.partition(":")[2].split(",")]
            if len(values) != len(style_format):
                continue
            fields = dict(zip(style_format, values, strict=True))
            if fields.get("Name") == style_name:
                return float(fields["Fontsize"])
    raise AssertionError(f"Style {style_name} not found")


def _event_y(text: str) -> float:
    match = _POS_Y_RE.search(text)
    assert match is not None
    return float(match.group(1))


def test_compile_preserves_protected_and_release_passes(tmp_path: Path, sample_cues) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    paths = title_paths(tmp_path, "demo", "movie")
    protected = ass_dialogue("0:00:08.00", "0:00:10.00", r"{\pos(300,100)}SIGN")
    a = write_ass(tmp_path / "a.ass", sample_cues, extra=[protected])
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
        notes=None,
    )
    _disable_external_release_gates(paths)
    normalize_all(paths)
    build_all_workfiles(paths)
    outputs = compile_all(paths)
    tw = parse_ass(Path(outputs["tw"]))
    jp = parse_ass(Path(outputs["jp"]))
    assert any("SIGN" in event.raw_line for event in tw.events)
    assert any("SIGN" in event.raw_line for event in jp.events)
    zh_events = [event for event in jp.events if event.fields.get("Style") == "SF-ZH"]
    ja_events = [event for event in jp.events if event.fields.get("Style") == "SF-JA"]
    assert zh_events and ja_events
    assert any("日本語" in event.fields.get("Text", "") for event in ja_events)
    ja_by_span = {(event.start_ms, event.end_ms): event for event in ja_events}
    paired = [event for event in zh_events if (event.start_ms, event.end_ms) in ja_by_span]
    assert paired
    for zh in paired:
        ja = ja_by_span[(zh.start_ms, zh.end_ms)]
        assert _event_y(zh.fields["Text"]) < _event_y(ja.fields["Text"])
    qa = run_all_qa(paths)
    assert qa["ok"] is True
    manifest = create_release_manifest(paths)
    assert len(manifest["files"]) == 2


def test_compile_scales_generated_font_size_to_authored_playres(
    tmp_path: Path, sample_cues
) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    paths = title_paths(tmp_path, "demo", "movie")
    source = write_ass(tmp_path / "source.ass", sample_cues)
    authored = source.read_text(encoding="utf-8").replace("PlayResX: 1920", "PlayResX: 640")
    authored = authored.replace("PlayResY: 1080", "PlayResY: 480")
    source.write_text(authored, encoding="utf-8")
    add_source(paths, "S", source)
    _disable_external_release_gates(paths)
    normalize_all(paths)
    build_all_workfiles(paths)
    output = Path(compile_all(paths)["clean"])
    text = output.read_text(encoding="utf-8")
    assert "PlayResX: 640" in text
    assert "PlayResY: 480" in text
    script_size = _style_font_size(text, "SF-ZH")
    assert abs(script_size - (60 * 480 / 1080)) < 0.001
    assert abs(script_size * 1080 / 480 - 60) < 0.01


def test_jp_source_gap_never_fabricates_japanese(tmp_path: Path, sample_cues) -> None:
    (tmp_path / "projects").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n", encoding="utf-8")
    create_project(tmp_path, "demo", "Demo")
    create_title(tmp_path, "demo", "movie", "Movie")
    paths = title_paths(tmp_path, "demo", "movie")
    a = write_ass(tmp_path / "a.ass", sample_cues)
    b = write_ass(tmp_path / "b.ass", sample_cues)
    c = write_ass(tmp_path / "c.ass", [])
    for role, path in [("A", a), ("B", b), ("C", c)]:
        add_source(paths, role, path)
    _disable_external_release_gates(paths)
    normalize_all(paths)
    build_all_workfiles(paths)
    coverage = read_json(paths.work / "bilingual-coverage.json")
    assert coverage["source_gap"] == len(sample_cues)
    assert coverage["fabricated"] == 0
    jp = parse_ass(Path(compile_all(paths)["jp"]))
    assert sum(event.fields.get("Style") == "SF-ZH" for event in jp.events) == len(sample_cues)
    assert not any(event.fields.get("Style") == "SF-JA" for event in jp.events)

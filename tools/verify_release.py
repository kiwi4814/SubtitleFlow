from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from subtitleflow.canon import add_term
from subtitleflow.compile import compile_all
from subtitleflow.formats.ass import build_event_line, make_dialogue_values, parse_ass, render_from_template
from subtitleflow.io import read_json, write_json
from subtitleflow.normalize import normalize_all
from subtitleflow.qa import run_all_qa
from subtitleflow.release import create_release_manifest
from subtitleflow.util import sha256_file
from subtitleflow.workfile import build_all_workfiles
from subtitleflow.workspace import add_source, create_project, create_title, title_paths, verify_sources


def write_synthetic_c_from_ass(source: Path, target: Path) -> None:
    doc = parse_ass(source)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,42,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,2,30,30,40,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    from subtitleflow.timecode import format_ass_time
    serial = 0
    for event in doc.events:
        if event.event_type.lower() != "dialogue" or event.protected:
            continue
        serial += 1
        lines.append(
            f"Dialogue: 0,{format_ass_time(event.start_ms)},{format_ass_time(event.end_ms)},Default,,0,0,0,,日本語テスト{serial:04d}"
        )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_large_ass(source: Path) -> dict:
    before = sha256_file(source)
    with tempfile.TemporaryDirectory(prefix="subtitleflow-stress-") as tmp:
        root = Path(tmp)
        (root / "projects").mkdir()
        (root / "pyproject.toml").write_text("[project]\nname='verify'\nversion='0'\n", encoding="utf-8")
        create_project(root, "stress", "Stress")
        create_title(root, "stress", "title", "Doraemon stress fixture")
        paths = title_paths(root, "stress", "title")
        c = root / "C.ass"
        write_synthetic_c_from_ass(source, c)
        for role, file in [("A", source), ("B", source), ("C", c), ("D", source)]:
            add_source(paths, role, file)
        cfg = read_json(paths.title_config)
        cfg["tw_branch"]["traditional_to_simplified"] = False
        # Stress verification exercises deterministic mechanics; editorial/visual gates are
        # independently covered by dedicated tests and the synthetic video verification.
        cfg["quality_gates"] = {
            "require_research": False,
            "require_semantic_qa": False,
            "require_visual_qa": False,
            "require_fonts": False,
        }
        cfg["fonts"]["require_for_release"] = False
        write_json(paths.title_config, cfg)
        for term_id, canonical, aliases in [
            ("doraemon", "哆啦A梦", ["小叮当", "机器猫"]),
            ("suneo", "小夫", ["阿福"]),
            ("gian", "胖虎", ["技安"]),
            ("shizuka", "静香", ["宜静"]),
        ]:
            add_term(paths, scope="project", term_id=term_id, canonical=canonical, aliases=aliases,
                     auto_replace=True, context_sensitive=False, branches=["tw", "jp"], notes="stress test")
        normalize_all(paths)
        work = build_all_workfiles(paths)
        compiled = compile_all(paths)
        qa = run_all_qa(paths)
        manifest = create_release_manifest(paths)
        verify_sources(paths)
        a_norm = read_json(paths.normalized / "A.json")
        return {
            "source_sha256_before": before,
            "source_sha256_after": sha256_file(source),
            "source_unchanged": before == sha256_file(source),
            "events": len(a_norm["cues"]),
            "protected": a_norm["protected_count"],
            "workfiles": work,
            "compiled": {k: Path(v).name for k, v in compiled.items()},
            "qa_ok": qa["ok"],
            "release_files": [item["name"] for item in manifest["files"]],
        }


def protected_roundtrip(source: Path) -> dict:
    doc = parse_ass(source)
    protected = [event for event in doc.events if event.protected]
    if not protected:
        return {"protected": 0, "roundtrip": True}
    values = make_dialogue_values(doc.events_format, start_ms=1000, end_ms=2000, text="TEST", style="SF-ZH")
    text = render_from_template(doc, [(1000, 1_000_000, build_event_line(doc.events_format, values))])
    retained = sum(1 for event in protected if event.raw_line in text)
    return {"protected": len(protected), "retained": retained, "roundtrip": retained == len(protected)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doraemon-ass", type=Path)
    parser.add_argument("--complex-ass", type=Path)
    parser.add_argument("--output", type=Path, default=Path("verification/verification-results.json"))
    args = parser.parse_args()
    result = {"large_ass": None, "complex_ass": None}
    if args.doraemon_ass:
        result["large_ass"] = run_large_ass(args.doraemon_ass.resolve())
    if args.complex_ass:
        result["complex_ass"] = protected_roundtrip(args.complex_ass.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

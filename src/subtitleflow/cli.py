from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

from .canon import add_term
from .compile import compile_all
from .doctor import doctor_report
from .errors import SubtitleFlowError
from .fonts import audit_fonts, install_registered_fonts, verify_registered_fonts
from .gates import mark_research_complete, mark_semantic_qa_complete, mark_visual_qa_complete
from .io import read_json, write_json
from .media import probe_media, render_previews
from .normalize import normalize_all
from .qa import run_all_qa
from .release import create_release_manifest
from .remux import remux
from .review import decide_candidate, import_proposals, list_candidates, render_review_markdown
from .srp.archive import compute_pack_digest, import_pack, materialize_pack_input
from .srp.diff import diff_research
from .srp.registry import (
    bind_pack,
    list_packs,
    map_branch,
    research_status,
    set_mode,
    unbind_pack,
)
from .srp.resolver import approve_research, resolve_research
from .srp.validate import validate_pack_dir
from .state import invalidate_stages, state_summary
from .style import load_style_profile
from .workfile import build_all_workfiles
from .workspace import (
    add_source,
    configure_workflow_profile,
    create_project,
    create_title,
    find_repo_root,
    set_title_series_id,
    title_paths,
    verify_sources,
)


def _repo(args: argparse.Namespace) -> Path:
    return Path(args.repo).resolve() if getattr(args, "repo", None) else find_repo_root()


def _paths(args: argparse.Namespace):
    return title_paths(_repo(args), args.project, args.title)


def _project_paths(args: argparse.Namespace):
    return title_paths(_repo(args), args.project, "research-registry")


def _print(data: Any, *, as_json: bool = False) -> None:
    if isinstance(data, str) and not as_json:
        print(data, end="" if data.endswith("\n") else "\n")
        return
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{key}: {json.dumps(value, ensure_ascii=False)}")
            else:
                print(f"{key}: {value}")
    else:
        print(data)


def cmd_doctor(args: argparse.Namespace) -> Any:
    return doctor_report()


def cmd_project_init(args: argparse.Namespace) -> Any:
    path = create_project(_repo(args), args.project, args.name or args.project)
    return {"created": str(path)}


def cmd_title_init(args: argparse.Namespace) -> Any:
    repo = _repo(args)
    path = create_title(
        repo,
        args.project,
        args.title,
        args.name or args.title,
        series_id=args.series_id,
    )
    paths = title_paths(repo, args.project, args.title)
    data = read_json(paths.title_config)
    configure_workflow_profile(data, args.profile)
    write_json(paths.title_config, data)
    return {"created": str(path), "workflow_profile": args.profile}


def cmd_title_set_series(args: argparse.Namespace) -> Any:
    return set_title_series_id(_paths(args), args.series_id)


def cmd_title_set_media(args: argparse.Namespace) -> Any:
    paths = _paths(args)
    data = read_json(paths.title_config)
    media = data.setdefault("media", {})
    if args.video:
        media["video"] = args.video
    if args.output:
        media["output_mkv"] = args.output
    write_json(paths.title_config, data)
    invalidate_stages(
        paths,
        ("render_clean", "render_tw", "render_jp", "visual_clean", "visual_tw", "visual_jp", "release", "remux"),
        reason="media configuration changed",
    )
    return media


def cmd_style_show(args: argparse.Namespace) -> Any:
    profile = load_style_profile(_paths(args))
    profile.pop("_profile_path", None)
    return profile


def cmd_style_set(args: argparse.Namespace) -> Any:
    paths = _paths(args)
    data = read_json(paths.title_config)
    data.setdefault("style", {})["profile"] = args.profile
    # Validate the prospective configuration before persisting it. A typo must not
    # leave title.json pointing at a profile that cannot be loaded.
    profile = load_style_profile(paths, config=data)
    write_json(paths.title_config, data)
    invalidate_stages(
        paths,
        ("compile_clean", "compile_tw", "compile_jp", "fonts", "qa", "semantic_qa", "render_clean", "render_tw", "render_jp", "visual_clean", "visual_tw", "visual_jp", "release", "remux"),
        reason="style profile changed",
    )
    return {"profile": profile.get("id"), "display_name": profile.get("display_name")}


def cmd_fonts_audit(args: argparse.Namespace) -> Any:
    return audit_fonts(
        _paths(args),
        extra_dirs=[Path(value).expanduser().resolve() for value in args.font_dir],
        map_file=Path(args.map_file).expanduser().resolve() if args.map_file else None,
    )


def cmd_fonts_install(args: argparse.Namespace) -> Any:
    return install_registered_fonts(
        _repo(args),
        Path(args.source),
        registry_file=Path(args.registry_file).expanduser().resolve() if args.registry_file else None,
        replace=args.replace,
    )


def cmd_fonts_verify(args: argparse.Namespace) -> Any:
    return verify_registered_fonts(
        _repo(args),
        registry_file=Path(args.registry_file).expanduser().resolve() if args.registry_file else None,
    )


def cmd_source_add(args: argparse.Namespace) -> Any:
    return add_source(_paths(args), args.role, Path(args.file), replace=args.replace)


def cmd_source_verify(args: argparse.Namespace) -> Any:
    roles = {item.upper() for item in args.role} if args.role else None
    return verify_sources(_paths(args), roles)


def cmd_normalize(args: argparse.Namespace) -> Any:
    return normalize_all(_paths(args))


def cmd_prepare(args: argparse.Namespace) -> Any:
    paths = _paths(args)
    normalized = normalize_all(paths)
    work = build_all_workfiles(paths, allow_no_opencc=args.allow_no_opencc)
    return {"normalized": normalized, "workfiles": work, "status": state_summary(paths)}


def cmd_status(args: argparse.Namespace) -> Any:
    return state_summary(_paths(args))


def cmd_research_validate_pack(args: argparse.Namespace) -> Any:
    with materialize_pack_input(Path(args.path)) as (pack_root, archive_sha256):
        validated = validate_pack_dir(pack_root)
        return {
            "ok": True,
            "manifest": validated.manifest,
            "counts": validated.counts,
            "pack_digest": compute_pack_digest(pack_root),
            "archive_sha256": archive_sha256,
        }


def cmd_research_import(args: argparse.Namespace) -> Any:
    return import_pack(_project_paths(args), Path(args.path), dry_run=args.dry_run)


def cmd_research_list(args: argparse.Namespace) -> Any:
    return {"packs": list_packs(_project_paths(args))}


def cmd_research_set_mode(args: argparse.Namespace) -> Any:
    return set_mode(_paths(args), args.mode)


def cmd_research_map_branch(args: argparse.Namespace) -> Any:
    return map_branch(_paths(args), args.branch, args.srp_branch)


def cmd_research_bind(args: argparse.Namespace) -> Any:
    return bind_pack(_paths(args), args.pack_ref)


def cmd_research_unbind(args: argparse.Namespace) -> Any:
    return unbind_pack(_paths(args), args.pack_ref)


def cmd_research_resolve(args: argparse.Namespace) -> Any:
    return resolve_research(_paths(args))


def cmd_research_diff(args: argparse.Namespace) -> Any:
    return diff_research(_paths(args))


def cmd_research_approve(args: argparse.Namespace) -> Any:
    return approve_research(_paths(args), note=args.note)


def cmd_research_status(args: argparse.Namespace) -> Any:
    return research_status(_paths(args))


def cmd_research_mark(args: argparse.Namespace) -> Any:
    paths = _paths(args)
    mark_research_complete(paths, note=args.note)
    return state_summary(paths)


def cmd_canon_add(args: argparse.Namespace) -> Any:
    return add_term(
        _paths(args),
        scope=args.scope,
        term_id=args.id,
        canonical=args.canonical,
        aliases=args.alias,
        auto_replace=args.auto,
        context_sensitive=args.context_sensitive,
        branches=args.branch or ["clean", "tw", "jp"],
        notes=args.notes,
        key=args.key,
        enforcement=args.enforcement,
    )


def cmd_review_import(args: argparse.Namespace) -> Any:
    candidates = import_proposals(_paths(args), Path(args.file))
    return {"imported": [candidate.to_dict() for candidate in candidates]}


def cmd_review_list(args: argparse.Namespace) -> Any:
    candidates = list_candidates(_paths(args), status=args.status)
    if args.markdown:
        return render_review_markdown(candidates)
    return {"candidates": [candidate.to_dict() for candidate in candidates]}


def cmd_review_decide(args: argparse.Namespace) -> Any:
    candidate = decide_candidate(
        _paths(args),
        args.candidate,
        args.decision,
        note=args.note,
        custom_text=args.text,
    )
    return candidate.to_dict()


def cmd_compile(args: argparse.Namespace) -> Any:
    return compile_all(_paths(args), preview=args.preview)


def cmd_qa(args: argparse.Namespace) -> Any:
    return run_all_qa(_paths(args))


def cmd_semantic_qa_mark(args: argparse.Namespace) -> Any:
    paths = _paths(args)
    mark_semantic_qa_complete(paths, note=args.note)
    return state_summary(paths)


def cmd_visual_qa_mark(args: argparse.Namespace) -> Any:
    paths = _paths(args)
    mark_visual_qa_complete(paths, args.branch, note=args.note)
    return state_summary(paths)


def cmd_render(args: argparse.Namespace) -> Any:
    files = render_previews(
        _paths(args),
        args.branch,
        video=Path(args.video).resolve() if args.video else None,
        max_frames=args.max_frames,
    )
    return {"frames": [str(path) for path in files]}


def cmd_media_probe(args: argparse.Namespace) -> Any:
    return probe_media(Path(args.file).resolve())


def cmd_release(args: argparse.Namespace) -> Any:
    return create_release_manifest(_paths(args))


def cmd_remux(args: argparse.Namespace) -> Any:
    cmd = remux(
        _paths(args),
        video=Path(args.video).resolve() if args.video else None,
        output=Path(args.output).resolve() if args.output else None,
        dry_run=args.dry_run,
        force=args.force,
    )
    return {"command": shlex.join(cmd), "executed": not args.dry_run}


def add_title_selector(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("project")
    parser.add_argument("title")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="subflow", description="SubtitleFlow production pipeline")
    parser.add_argument("--repo", help="Repository root; auto-detected by default")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor", help="Check runtime/tool availability")
    p.set_defaults(func=cmd_doctor)

    project = sub.add_parser("project", help="Project/series operations")
    project_sub = project.add_subparsers(dest="project_command", required=True)
    p = project_sub.add_parser("init")
    p.add_argument("project")
    p.add_argument("--name")
    p.set_defaults(func=cmd_project_init)

    title = sub.add_parser("title", help="Title/movie/episode operations")
    title_sub = title.add_subparsers(dest="title_command", required=True)
    p = title_sub.add_parser("init")
    add_title_selector(p)
    p.add_argument("--name")
    p.add_argument("--profile", choices=["auto", "full", "single", "source-assisted", "dub", "bilingual"], default="auto")
    p.add_argument("--series-id")
    p.set_defaults(func=cmd_title_init)
    p = title_sub.add_parser("set-series", help="Set the title's SRP/canon series identity")
    add_title_selector(p)
    p.add_argument("series_id")
    p.set_defaults(func=cmd_title_set_series)
    p = title_sub.add_parser("set-media")
    add_title_selector(p)
    p.add_argument("--video")
    p.add_argument("--output")
    p.set_defaults(func=cmd_title_set_media)

    style = sub.add_parser("style", help="ASS style profile operations")
    style_sub = style.add_subparsers(dest="style_command", required=True)
    p = style_sub.add_parser("show")
    add_title_selector(p)
    p.set_defaults(func=cmd_style_show)
    p = style_sub.add_parser("set")
    add_title_selector(p)
    p.add_argument("profile")
    p.set_defaults(func=cmd_style_set)

    fonts = sub.add_parser("fonts", help="Resolve and audit ASS font dependencies")
    fonts_sub = fonts.add_subparsers(dest="fonts_command", required=True)
    p = fonts_sub.add_parser(
        "install",
        help="Import user-provided registered fonts into gitignored fonts/local",
    )
    p.add_argument("source", help="Font file, directory, or ZIP archive")
    p.add_argument("--registry-file")
    p.add_argument("--replace", action="store_true")
    p.set_defaults(func=cmd_fonts_install)
    p = fonts_sub.add_parser("verify", help="Verify local registered fonts by SHA and Name Table")
    p.add_argument("--registry-file")
    p.set_defaults(func=cmd_fonts_verify)
    p = fonts_sub.add_parser("audit")
    add_title_selector(p)
    p.add_argument("--font-dir", action="append", default=[])
    p.add_argument("--map-file")
    p.set_defaults(func=cmd_fonts_audit)

    source = sub.add_parser("source", help="Immutable source operations")
    source_sub = source.add_subparsers(dest="source_command", required=True)
    p = source_sub.add_parser("add")
    add_title_selector(p)
    p.add_argument("role", choices=["A", "B", "C", "D", "S", "a", "b", "c", "d", "s"])
    p.add_argument("file")
    p.add_argument("--replace", action="store_true")
    p.set_defaults(func=cmd_source_add)
    p = source_sub.add_parser("verify")
    add_title_selector(p)
    p.add_argument("--role", action="append", choices=["A", "B", "C", "D", "S"])
    p.set_defaults(func=cmd_source_verify)

    p = sub.add_parser("normalize", help="Normalize all imported subtitle roles")
    add_title_selector(p)
    p.set_defaults(func=cmd_normalize)

    p = sub.add_parser("prepare", help="Verify, normalize, align, and seed both branches")
    add_title_selector(p)
    p.add_argument("--allow-no-opencc", action="store_true", help="Diagnostics only: skip T2S if OpenCC is missing")
    p.set_defaults(func=cmd_prepare)

    p = sub.add_parser("status", help="Show durable workflow state")
    add_title_selector(p)
    p.set_defaults(func=cmd_status)

    research = sub.add_parser("research", help="Optional SRP research-pack operations")
    research_sub = research.add_subparsers(dest="research_command", required=True)

    p = research_sub.add_parser("validate-pack", help="Validate an SRP/1.0 directory or ZIP")
    p.add_argument("path")
    p.set_defaults(func=cmd_research_validate_pack)

    p = research_sub.add_parser("import", help="Import an immutable SRP snapshot into a project")
    p.add_argument("project")
    p.add_argument("path")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_research_import)

    p = research_sub.add_parser("list", help="List imported SRP snapshots for a project")
    p.add_argument("project")
    p.set_defaults(func=cmd_research_list)

    p = research_sub.add_parser("set-mode", help="Set off/advisory/enforce for a title")
    add_title_selector(p)
    p.add_argument("mode", choices=["off", "advisory", "enforce"])
    p.set_defaults(func=cmd_research_set_mode)

    p = research_sub.add_parser("map-branch", help="Map a SubtitleFlow branch to an SRP branch id")
    add_title_selector(p)
    p.add_argument("branch", choices=["clean", "tw", "jp"])
    p.add_argument("srp_branch", nargs="?")
    p.set_defaults(func=cmd_research_map_branch)

    p = research_sub.add_parser("bind", help="Pin an imported SRP snapshot to a title")
    add_title_selector(p)
    p.add_argument("pack_ref")
    p.set_defaults(func=cmd_research_bind)

    p = research_sub.add_parser("unbind", help="Remove an SRP binding from a title")
    add_title_selector(p)
    p.add_argument("pack_ref")
    p.set_defaults(func=cmd_research_unbind)

    p = research_sub.add_parser("resolve", help="Compile deterministic Effective Knowledge")
    add_title_selector(p)
    p.set_defaults(func=cmd_research_resolve)

    p = research_sub.add_parser("diff", help="Preview Effective Knowledge changes")
    add_title_selector(p)
    p.set_defaults(func=cmd_research_diff)

    p = research_sub.add_parser("approve", help="Approve the current resolved Research snapshot")
    add_title_selector(p)
    p.add_argument("--note")
    p.set_defaults(func=cmd_research_approve)

    p = research_sub.add_parser("status", help="Show research mode, bindings, resolve, and gate state")
    add_title_selector(p)
    p.set_defaults(func=cmd_research_status)

    p = research_sub.add_parser(
        "mark-complete",
        help="Legacy v0.3 alias; native v0.4 titles should use research approve",
    )
    add_title_selector(p)
    p.add_argument("--note")
    p.set_defaults(func=cmd_research_mark)

    canon = sub.add_parser("canon", help="Canon/glossary operations")
    canon_sub = canon.add_subparsers(dest="canon_command", required=True)
    p = canon_sub.add_parser("add-term")
    add_title_selector(p)
    p.add_argument("--scope", choices=["project", "title"], default="project")
    p.add_argument("--id", required=True)
    p.add_argument("--key")
    p.add_argument(
        "--enforcement",
        choices=["locked", "preferred", "informational"],
        default="locked",
    )
    p.add_argument("--canonical", required=True)
    p.add_argument("--alias", action="append", default=[])
    p.add_argument("--auto", action="store_true")
    p.add_argument("--context-sensitive", action="store_true")
    p.add_argument("--branch", action="append", choices=["clean", "tw", "jp"])
    p.add_argument("--notes")
    p.set_defaults(func=cmd_canon_add)

    review = sub.add_parser("review", help="Human review gate")
    review_sub = review.add_subparsers(dest="review_command", required=True)
    p = review_sub.add_parser("import")
    add_title_selector(p)
    p.add_argument("file")
    p.set_defaults(func=cmd_review_import)
    p = review_sub.add_parser("list")
    add_title_selector(p)
    p.add_argument("--status", choices=["pending", "approved", "rejected", "superseded"])
    p.add_argument("--markdown", action="store_true")
    p.set_defaults(func=cmd_review_list)
    p = review_sub.add_parser("decide")
    add_title_selector(p)
    p.add_argument("candidate")
    p.add_argument("decision", choices=["approve", "reject", "custom"])
    p.add_argument("--text")
    p.add_argument("--note")
    p.set_defaults(func=cmd_review_decide)

    p = sub.add_parser("compile", help="Compile release ASS files")
    add_title_selector(p)
    p.add_argument("--preview", action="store_true", help="Allow compile with pending reviews; output is marked preview")
    p.set_defaults(func=cmd_compile)

    p = sub.add_parser("qa", help="Run structural, terminology, layout, and compiled ASS QA")
    add_title_selector(p)
    p.set_defaults(func=cmd_qa)

    semantic_qa = sub.add_parser("semantic-qa", help="Independent semantic QA gate")
    semantic_qa_sub = semantic_qa.add_subparsers(dest="semantic_qa_command", required=True)
    p = semantic_qa_sub.add_parser("mark-complete")
    add_title_selector(p)
    p.add_argument("--note")
    p.set_defaults(func=cmd_semantic_qa_mark)

    visual_qa = sub.add_parser("visual-qa", help="Human/vision approval gate for rendered subtitle frames")
    visual_qa_sub = visual_qa.add_subparsers(dest="visual_qa_command", required=True)
    p = visual_qa_sub.add_parser("mark-complete")
    add_title_selector(p)
    p.add_argument("branch", choices=["clean", "tw", "jp"])
    p.add_argument("--note")
    p.set_defaults(func=cmd_visual_qa_mark)

    p = sub.add_parser("render", help="Render representative ASS frames with ffmpeg/libass")
    add_title_selector(p)
    p.add_argument("branch", choices=["clean", "tw", "jp"])
    p.add_argument("--video")
    p.add_argument("--max-frames", type=int, default=12)
    p.set_defaults(func=cmd_render)

    media = sub.add_parser("media", help="Media utilities")
    media_sub = media.add_subparsers(dest="media_command", required=True)
    p = media_sub.add_parser("probe")
    p.add_argument("file")
    p.set_defaults(func=cmd_media_probe)

    p = sub.add_parser("release", help="Freeze a QA-passed subtitle release manifest")
    add_title_selector(p)
    p.set_defaults(func=cmd_release)

    p = sub.add_parser("remux", help="Remux release subtitles into an MKV with MKVToolNix")
    add_title_selector(p)
    p.add_argument("--video")
    p.add_argument("--output")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_remux)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
        _print(result, as_json=args.json)
        return 0
    except SubtitleFlowError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a compact AI-friendly index for one SubtitleFlow evidence series directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


TITLE_PREFIXES = ("M", "SBM")


def _subtitle_files(root: Path) -> list[str]:
    result: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".ass", ".ssa", ".srt", ".vtt"}:
            result.append(path.relative_to(root).as_posix())
    return result


def _title_entry(series_root: Path, title_dir: Path) -> dict[str, object]:
    categories: dict[str, list[str]] = {}
    for child in sorted(title_dir.iterdir()):
        if child.is_dir():
            files = [
                path.relative_to(series_root).as_posix()
                for path in sorted(child.rglob("*"))
                if path.is_file() and path.suffix.lower() in {".ass", ".ssa", ".srt", ".vtt"}
            ]
            if files:
                categories[child.name] = files
    return {
        "directory": title_dir.relative_to(series_root).as_posix(),
        "subtitle_count": sum(len(items) for items in categories.values()),
        "categories": categories,
    }


def build_index(series_root: Path) -> dict[str, object]:
    titles: dict[str, object] = {}
    for child in sorted(series_root.iterdir()):
        if not child.is_dir() or child.name.startswith("_") or child.name == "research_packs":
            continue
        if child.name.startswith(TITLE_PREFIXES):
            title_id = child.name.split("_", 1)[0].lower()
            titles[title_id] = _title_entry(series_root, child)

    packs_root = series_root / "research_packs"
    packs = [path.name for path in sorted(packs_root.iterdir()) if path.is_dir()] if packs_root.is_dir() else []
    return {
        "schema_version": 1,
        "series_id": series_root.name,
        "title_count": len(titles),
        "titles": titles,
        "research_packs": packs,
        "catalog_files": [
            name
            for name in ("MOVIE_CATALOG.json", "COLLECTION_STATUS.md", "AI_README.md", "VERIFICATION_SUMMARY.md")
            if (series_root / name).is_file()
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("series_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.series_root.resolve()
    if not root.is_dir():
        parser.error(f"series_root does not exist: {root}")
    output = args.output.resolve() if args.output else root / "index.json"
    data = build_index(root)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the existing M01 pilot while persisting its first portable bundle for CI inspection."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_PATH = REPO_ROOT / "tools" / "run_m01_prepare_pilot.py"


def _load_pilot() -> ModuleType:
    spec = importlib.util.spec_from_file_location("subtitleflow_m01_prepare_pilot", PILOT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load M01 pilot: {PILOT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assert_portable_text_files_do_not_leak_paths(bundle_dir: Path) -> None:
    forbidden = (str(REPO_ROOT), str(bundle_dir.parent))
    text_suffixes = {".ass", ".json", ".jsonl", ".md", ".txt"}
    leaks: list[str] = []
    for path in sorted(bundle_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        for prefix in forbidden:
            if prefix in text:
                leaks.append(f"{path.relative_to(bundle_dir)} -> {prefix}")
    if leaks:
        raise RuntimeError("Portable M01 bundle leaked runtime absolute paths: " + "; ".join(leaks))


def main() -> int:
    output_value = os.environ.get("SUBTITLEFLOW_M01_ARTIFACT_DIR", "").strip()
    if not output_value:
        raise RuntimeError("SUBTITLEFLOW_M01_ARTIFACT_DIR is required")
    output_dir = Path(output_value).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pilot = _load_pilot()
    original_builder = pilot.build_portable_release_bundle
    captured = False

    def capturing_builder(*args, **kwargs):
        nonlocal captured
        result = original_builder(*args, **kwargs)
        archive = kwargs.get("archive_path")
        if not captured and archive is not None:
            archive_path = Path(archive)
            bundle_dir = Path(result.bundle_dir)
            if not archive_path.is_file():
                raise RuntimeError(f"M01 portable archive was not created: {archive_path}")
            _assert_portable_text_files_do_not_leak_paths(bundle_dir)
            shutil.copy2(archive_path, output_dir / "SubtitleFlow-M01-JP-ZHCN.zip")
            shutil.copy2(bundle_dir / "manifest.json", output_dir / "manifest.json")
            captured = True
        return result

    pilot.build_portable_release_bundle = capturing_builder
    result = pilot.run_pilot()
    (output_dir / "pilot-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not captured:
        raise RuntimeError("M01 pilot passed without producing a portable bundle artifact")
    return 0 if result.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

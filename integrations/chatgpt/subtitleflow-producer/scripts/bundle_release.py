#!/usr/bin/env python3
"""Create a deterministic SubtitleFlow web release ZIP from an already-built bundle tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument("output_zip", type=Path)
    args = parser.parse_args()

    root = args.bundle_dir.resolve()
    if not root.is_dir():
        parser.error(f"bundle_dir does not exist: {root}")
    manifest = root / "manifest.json"
    if not manifest.is_file():
        parser.error("bundle_dir must contain manifest.json")
    json.loads(manifest.read_text(encoding="utf-8"))

    files = list(iter_files(root))
    args.output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        args.output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in files:
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())

    print(
        json.dumps(
            {
                "archive": str(args.output_zip),
                "sha256": sha256(args.output_zip),
                "files": len(files),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Sequence

from .errors import SubtitleFlowError


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-.")
    if not value:
        raise SubtitleFlowError("ID must contain at least one ASCII letter or digit")
    return value


def which(name: str) -> str | None:
    return shutil.which(name)


def run_checked(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: int = 120,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(args),
            cwd=cwd,
            text=True,
            capture_output=capture,
            check=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise SubtitleFlowError(f"Required executable not found: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SubtitleFlowError(f"Command timed out after {timeout}s: {' '.join(args)}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise SubtitleFlowError(
            f"Command failed ({exc.returncode}): {' '.join(args)}\n{detail}"
        ) from exc


def chunks(items: Sequence[object], size: int) -> Iterable[Sequence[object]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]

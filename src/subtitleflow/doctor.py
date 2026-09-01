from __future__ import annotations

import platform
import subprocess
import sys
from typing import Any

from .text import TraditionalToSimplified
from .util import which


def _ffmpeg_has_libass() -> bool:
    executable = which("ffmpeg")
    if not executable:
        return False
    try:
        proc = subprocess.run(
            [executable, "-hide_banner", "-filters"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    filters = proc.stdout + "\n" + proc.stderr
    return " ass " in filters or " subtitles " in filters


def doctor_report() -> dict[str, Any]:
    converter = TraditionalToSimplified("t2s")
    ffmpeg = which("ffmpeg")
    ffprobe = which("ffprobe")
    libass = _ffmpeg_has_libass()
    tools = {
        "git": which("git"),
        "opencode": which("opencode"),
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "ffmpeg_libass": libass,
        "mkvmerge": which("mkvmerge"),
        "opencc": converter.backend,
    }
    return {
        "python": sys.version.split()[0],
        "python_ok": sys.version_info >= (3, 11),
        "platform": platform.platform(),
        "tools": tools,
        "required_for_core": {"python": sys.version_info >= (3, 11)},
        "required_for_visual": {
            "ffmpeg": bool(ffmpeg),
            "ffprobe": bool(ffprobe),
            "libass_filter": libass,
        },
        "required_for_remux": {"mkvmerge": bool(tools["mkvmerge"])},
        "required_for_tw_conversion": {"opencc": bool(tools["opencc"])},
    }

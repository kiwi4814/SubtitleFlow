from __future__ import annotations

import platform
import sys
from typing import Any

from .text import TraditionalToSimplified
from .util import ffmpeg_has_libass, which


def _fonttools_available() -> bool:
    try:
        import fontTools  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return False
    return True


def doctor_report() -> dict[str, Any]:
    converter = TraditionalToSimplified("t2s")
    ffmpeg = which("ffmpeg")
    ffprobe = which("ffprobe")
    libass = ffmpeg_has_libass()
    tools = {
        "git": which("git"),
        "opencode": which("opencode"),
        "ffmpeg": ffmpeg,
        "ffprobe": ffprobe,
        "ffmpeg_libass": libass,
        "mkvmerge": which("mkvmerge"),
        "mkvextract": which("mkvextract"),
        "opencc": converter.backend,
        "fonttools": _fonttools_available(),
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
        "recommended_for_attachment_collision_verification": {
            "mkvextract": bool(tools["mkvextract"])
        },
        "recommended_for_font_autodiscovery": {"fonttools": bool(tools["fonttools"])},
        "required_for_tw_conversion": {"opencc": bool(tools["opencc"])},
    }

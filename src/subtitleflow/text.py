from __future__ import annotations

import re
import subprocess

from .util import which

_TAG_RE = re.compile(r"\{[^{}]*\}")
_WS_RE = re.compile(r"[ \t\u3000]+")


def strip_ass_tags(text: str) -> str:
    text = _TAG_RE.sub("", text)
    return text.replace(r"\N", "\n").replace(r"\n", "\n").replace(r"\h", " ")


def normalize_dialogue_text(text: str) -> str:
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        cleaned = _WS_RE.sub(" ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def ass_text(text: str) -> str:
    # Japanese evidence uses ➡ as a continuation marker. WQY supports →,
    # but not ➡, so preserve the marker meaning without system fallback.
    normalized = normalize_dialogue_text(text).replace("➡", "→")
    return normalized.replace("\n", r"\N")


class TraditionalToSimplified:
    """Use OpenCC when available; never silently pretend conversion happened."""

    def __init__(self, profile: str = "t2s") -> None:
        self.profile = profile
        self._python = None
        try:
            from opencc import OpenCC  # type: ignore[import-not-found]

            self._python = OpenCC(profile)
        except ModuleNotFoundError:
            self._python = None

    @property
    def available(self) -> bool:
        return self._python is not None or which("opencc") is not None

    @property
    def backend(self) -> str | None:
        if self._python is not None:
            return "python-opencc"
        if which("opencc"):
            return "opencc-cli"
        return None

    def convert(self, text: str) -> str:
        if self._python is not None:
            return str(self._python.convert(text))
        executable = which("opencc")
        if executable:
            proc = subprocess.run(
                [executable, "-c", self.profile],
                input=text,
                text=True,
                capture_output=True,
                check=True,
                timeout=20,
            )
            return proc.stdout.rstrip("\n")
        raise RuntimeError(
            "Traditional-to-Simplified conversion requested, but OpenCC is unavailable. "
            "Install the 'opencc' extra or the opencc CLI."
        )

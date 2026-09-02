from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

SemanticRole = Literal[
    "dialogue",
    "song-op",
    "song-ed",
    "song-insert",
    "screen-text",
    "title",
    "episode-title",
    "next-episode-title",
    "annotation",
    "staff-credit",
    "protected-fx",
    "document",
    "prop",
]
PositionIntent = Literal["preserve", "top", "center", "bottom", "manual"]

_URL_RE = re.compile(r"(?:https?://|www\.|(?:discord|telegram|twitter|weibo)\s*[:\uFF1A])", re.I)
_CREDIT_RE = re.compile(
    r"(?:字幕(?:组|制作|翻译|校对)|translator|translation|subbed\s+by|timing\s+by|fansub|译制|听写)",
    re.I,
)


@dataclass(frozen=True, slots=True)
class RoleClassification:
    role: SemanticRole
    position_intent: PositionIntent = "preserve"
    include_by_default: bool = True
    confidence: float = 1.0
    basis: str = "default-dialogue"


def _style_token(style: str) -> str:
    return re.sub(r"[\s_-]+", " ", style.strip().casefold())


def classify_event_role(
    *,
    style: str,
    text: str,
    protected_reason: str | None = None,
) -> RoleClassification:
    """Classify semantic purpose. Source style is evidence, never a position command."""
    value = _style_token(style)
    plain = text.strip()
    if _URL_RE.search(plain) or _CREDIT_RE.search(plain):
        return RoleClassification(
            "staff-credit", include_by_default=False, confidence=0.96, basis="credit-text"
        )
    if protected_reason and "drawing" in protected_reason.casefold():
        return RoleClassification("protected-fx", confidence=0.98, basis="ass-drawing")

    if value in {"op", "opening", "op lyrics", "opening lyrics"} or value.startswith("op "):
        return RoleClassification("song-op", confidence=0.9, basis="style-evidence")
    if value in {"ed", "ending", "ed lyrics", "ending lyrics"} or value.startswith("ed "):
        return RoleClassification("song-ed", confidence=0.9, basis="style-evidence")
    if value in {"song", "lyrics", "insert", "insert song", "歌词"}:
        return RoleClassification("song-insert", confidence=0.82, basis="style-evidence")
    if value in {"screen", "sign", "screen text", "screentext", "screen_text", "画面字"}:
        return RoleClassification(
            "screen-text", position_intent="preserve", confidence=0.82, basis="style-evidence"
        )
    if value in {"episode title", "episodetitle", "集标题"}:
        return RoleClassification("episode-title", confidence=0.9, basis="style-evidence")
    if value in {"next episode", "next episode title", "preview title", "下集预告"}:
        return RoleClassification("next-episode-title", confidence=0.9, basis="style-evidence")
    if value in {"title", "标题", "movie title"}:
        return RoleClassification("title", confidence=0.85, basis="style-evidence")
    if value in {"note", "notes", "annotation", "注释"}:
        return RoleClassification("annotation", confidence=0.82, basis="style-evidence")
    if value in {"document", "newspaper", "letter"}:
        return RoleClassification("document", confidence=0.82, basis="style-evidence")
    if value in {"prop", "wantedposter", "formal", "formalscreentext"}:
        return RoleClassification("prop", confidence=0.82, basis="style-evidence")

    # Numeric/generic source names such as Style2 are deliberately not interpreted as signs.
    return RoleClassification("dialogue")


def is_release_dialogue_role(role: str) -> bool:
    return role in {"dialogue", "song-op", "song-ed", "song-insert"}

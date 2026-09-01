from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BlockGeometry:
    play_res_x: int
    play_res_y: int
    target_x: int
    target_y: int
    source_x: int | None
    source_y: int | None
    target_rows: int
    source_rows: int
    target_height: float
    source_height: float
    gap: float
    mode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def visual_rows(text: str | None) -> int:
    if not text:
        return 0
    return max(1, len(text.replace(r"\N", "\n").split("\n")))


def _number(values: dict[str, str], key: str, default: float) -> float:
    try:
        return float(values.get(key, default))
    except (TypeError, ValueError):
        return default


def _line_height(style: dict[str, str], layout: dict[str, Any], prefix: str) -> float:
    size = _number(style, "Fontsize", 48.0)
    scale = _number(style, "ScaleY", 100.0) / 100.0
    factor = float(layout.get(f"{prefix}_line_height_em", 1.12))
    outline = _number(style, "Outline", 2.0)
    return size * scale * factor + outline * 2.0


def block_geometry(
    *,
    play_res_x: int,
    play_res_y: int,
    target_style: dict[str, str],
    source_style: dict[str, str] | None,
    layout: dict[str, Any],
    target_text: str,
    source_text: str | None = None,
    mode: str,
    semantic_role: str = "dialogue",
) -> BlockGeometry:
    """Calculate explicit bottom-center anchors for generated subtitle blocks.

    The profile supplies dimensionless safe-area/spacing intent. Row counts and style metrics
    determine actual coordinates, so no title- or row-combination-specific pixel constants are
    embedded in Python. Explicit \an2/\pos anchors keep libass collision avoidance from
    reordering the language block.
    """
    target_rows = visual_rows(target_text)
    source_rows = visual_rows(source_text)
    target_line = _line_height(target_style, layout, "target")
    source_line = _line_height(source_style or target_style, layout, "source")
    target_height = target_line * target_rows
    source_height = source_line * source_rows
    role_prefix = "song" if semantic_role.startswith("song-") else mode
    bottom_ratio = float(
        layout.get(
            f"{role_prefix}_bottom_anchor_ratio",
            layout.get(f"{mode}_bottom_anchor_ratio", 0.955 if mode == "bilingual" else 0.94),
        )
    )
    safe_padding_ratio = float(layout.get("safe_padding_ratio", 0.0))
    bottom_y = round(play_res_y * bottom_ratio - play_res_y * safe_padding_ratio)
    x = round(play_res_x * float(layout.get("horizontal_anchor_ratio", 0.5)))
    gap_em = float(layout.get("inter_language_gap_em", 0.25))
    gap = max(target_line, source_line) * gap_em

    if mode == "clean" or not source_rows:
        return BlockGeometry(
            play_res_x=play_res_x,
            play_res_y=play_res_y,
            target_x=x,
            target_y=bottom_y,
            source_x=None,
            source_y=None,
            target_rows=target_rows,
            source_rows=0,
            target_height=target_height,
            source_height=0.0,
            gap=0.0,
            mode=mode,
        )

    source_y = bottom_y
    target_y = round(source_y - source_height - gap)
    return BlockGeometry(
        play_res_x=play_res_x,
        play_res_y=play_res_y,
        target_x=x,
        target_y=target_y,
        source_x=x,
        source_y=source_y,
        target_rows=target_rows,
        source_rows=source_rows,
        target_height=target_height,
        source_height=source_height,
        gap=gap,
        mode=mode,
    )


def positioned_override(base: str | None, x: int, y: int) -> str:
    prefix = (base or "").strip()
    return prefix + rf"\an2\pos({x},{y})"

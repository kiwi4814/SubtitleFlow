# Configuration

Every title has `projects/<project>/titles/<title>/title.json`. Generated JSON is intentionally explicit and can be committed to Git.

## Evidence roles

- `A`: Timing Master; defines the common video time coordinate.
- `B`: existing Chinese translation for Japanese audio.
- `C`: Japanese source subtitle/evidence.
- `D`: Taiwan-dub transcript/subtitle.

Disable a branch if a title intentionally does not produce that product. Do not reassign role meanings per title.

## Alignment

```json
{
  "alignment": {
    "max_group": 3,
    "unmatched_penalty": 3.0,
    "review_confidence_below": 0.72
  }
}
```

`max_group` controls deterministic N:M grouping breadth. Low-confidence groups are review targets, not automatic proof of an error.

## TW branch

```json
{
  "tw_branch": {
    "enabled": true,
    "language_source": "D",
    "timing_source": "A",
    "traditional_to_simplified": true,
    "opencc_profile": "t2s"
  }
}
```

When conversion is enabled, OpenCC is required. SubtitleFlow will fail rather than silently claim a conversion happened.

## JP bilingual branch

```json
{
  "jp_branch": {
    "enabled": true,
    "translation_source": "B",
    "japanese_source": "C",
    "timing_source": "A"
  }
}
```

C controls source meaning; B is only the Chinese editing seed.

## ASS typography

Defaults target a 1920×1080 collector-style local playback layout:

```json
{
  "ass": {
    "target_font": "Noto Sans CJK SC",
    "target_size": 48,
    "target_margin_v": 52,
    "source_font": "Noto Sans CJK JP",
    "source_size": 38,
    "source_margin_v": 106,
    "single_line_preferred": true,
    "max_visual_rows_warning": 4
  }
}
```

Font files are not bundled. Use family names installed on the playback/render machine and validate actual frames.

## Quality gates

Production defaults are deliberately strict:

```json
{
  "quality_gates": {
    "require_research": true,
    "require_semantic_qa": true,
    "require_visual_qa": true
  }
}
```

A production release requires:

- non-empty `research/context.md` and `research/sources.md`;
- non-empty `qa/semantic-review.md` and a passed semantic-QA stage;
- rendered preview PNGs plus explicit visual approval for every enabled branch;
- a current deterministic QA snapshot.

For a mechanical/headless test only, gates may be explicitly disabled in `title.json`. Do not disable them merely to get a real release through.

## Media

```json
{
  "media": {
    "video": "${MEDIA_ROOT}/movie.mkv",
    "output_mkv": "${MEDIA_OUT}/movie.final.mkv",
    "preserve_existing_tracks": true
  }
}
```

Environment variables and `~` are expanded at runtime. Large media should stay outside Git.

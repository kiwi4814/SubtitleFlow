# Configuration

Each title has `projects/<project>/titles/<title>/title.json`.

## Workflow profile

```json
{
  "workflow": {"profile": "single"}
}
```

Valid values: `auto`, `single`, `source-assisted`, `dub`, `bilingual`, `full`.

Role meanings never change per title:

- S: self-contained target subtitle; own timing + editable text.
- A: Timing Master.
- B: existing Chinese translation seed for Japanese audio.
- C: source-language/Japanese semantic evidence.
- D: Taiwan-dub transcript.

## Clean branch

```json
{
  "clean_branch": {
    "enabled": true,
    "language_source": "S",
    "timing_source": "S",
    "source_evidence": "C",
    "source_assisted": "auto",
    "traditional_to_simplified": false,
    "opencc_profile": "t2s"
  }
}
```

`single` never requires C. `source-assisted` always requires C. C adds evidence only; S timing remains untouched.

## Multi-source branches

TW uses A + D. JP bilingual uses A + B + C. `full` enables both; `auto` derives whichever branch requirements are satisfied.

## Style profile

```json
{
  "style": {
    "profile": "kiwi-collector-v1",
    "mode": "hybrid",
    "overrides": {}
  }
}
```

The bundled profile lives at `styles/kiwi-collector-v1.json`. A repo-local profile wins over the packaged fallback.

### Final ordinary dialogue values

`SF-ZH`:

```json
{
  "Fontname": "文泉驿微米黑",
  "Fontsize": "60",
  "PrimaryColour": "&H00D2D2D2",
  "Bold": "-1",
  "ScaleY": "105",
  "Outline": "2",
  "Shadow": "0",
  "Alignment": "2",
  "MarginV": "103"
}
```

`SF-JA`:

```json
{
  "Fontname": "文泉驿微米黑",
  "Fontsize": "50",
  "PrimaryColour": "&H000E95CE",
  "Bold": "0",
  "ScaleY": "100",
  "Outline": "2",
  "Shadow": "0",
  "Alignment": "2",
  "MarginV": "45"
}
```

Both generated dialogue styles receive event-level `\blur2`.

Hybrid special-style preservation can be overridden through `style.overrides.source_preservation`. The default is deliberately conservative.

## Font configuration

```json
{
  "fonts": {
    "attach_to_mkv": true,
    "require_for_release": true,
    "require_all_referenced": true,
    "directories": ["fonts/local"],
    "map_file": "fonts/font-map.json",
    "aliases": {}
  }
}
```

`fonts/font-map.json` is local-only and git-ignored. Example:

```json
{
  "schema_version": 1,
  "families": {
    "文泉驿微米黑": ["local/wqy-microhei.ttf"],
    "思源黑体 CN Heavy": ["/absolute/or/env/expandable/path/font.otf"]
  }
}
```

If FontTools is installed, SubtitleFlow can match font name-table metadata when scanning `fonts.directories`; explicit mapping remains the most deterministic option.

Actual font requirements come from the compiled ASS, not from a hard-coded global list. Special title fonts are therefore required only for titles that actually reference them.

## Media and Remux

```json
{
  "media": {
    "video": "/path/to/input.mkv",
    "output_mkv": "/path/to/output.mkv",
    "preserve_existing_tracks": true,
    "preserve_existing_attachments": true
  }
}
```

Font attachments are controlled separately by `fonts.attach_to_mkv`. Existing attachments are preserved unless explicitly disabled.

## Quality gates

```json
{
  "quality_gates": {
    "require_research": true,
    "require_semantic_qa": true,
    "require_visual_qa": true,
    "require_fonts": true
  }
}
```

Relax a gate only as an explicit project decision. Default production behavior is strict.

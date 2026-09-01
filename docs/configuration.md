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

## Research / SRP policy

New v0.4 titles default to:

```json
{
  "research": {
    "mode": "off",
    "branch_map": {}
  }
}
```

Modes:

- `off`: ignore SRP; local canon continues to work.
- `advisory`: resolve bound SRP into model/QA context, but SRP completeness is not a release-blocking gate.
- `enforce`: require a bound, conflict-free, explicitly approved SRP snapshot before semantic editing/release.

`branch_map` maps SubtitleFlow output branches (`clean`, `tw`, `jp`) to producer-defined SRP branch IDs such as `jp-zh-cn` or `tw-dub-zh-cn`. Pack bindings are managed in `research/bindings.json` through the CLI rather than handwritten in `title.json`. See [`research.md`](research.md).

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
  "Fontname": "WenQuanYi Micro Hei",
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
  "Fontname": "WenQuanYi Micro Hei",
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
    "registry_file": "fonts/font-registry.json",
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
    "Project-Specific Font": ["local/project-specific.ttf"]
  }
}
```

`fonts/font-registry.json` is version-controlled repository evidence. For each registered font it defines canonical ASS family, aliases, canonical attachment filename, exact SHA-256, expected size/version, and logical roles. Run `subflow fonts install SOURCE` to populate ignored `fonts/local/` from a user-provided file/directory/ZIP, then `subflow fonts verify` to verify the complete registry.

`fonts/font-map.json` remains a local-only escape hatch for project-specific fonts not governed by the default registry. If FontTools is installed, SubtitleFlow parses Name Table metadata for scanned/mapped/registered fonts and checks that an ASS family or approved alias can really match the bytes. Without FontTools, bytes can still be hashed but internal-name verification is unavailable; strict production environments should install the `fonts`/`full` extra. Different payloads are never allowed to freeze under the same final MKV attachment filename.

Actual release requirements still come from the compiled ASS, not from a hard-coded global list. A registered title font is therefore attached only when the final ASS references it. Registry changes participate in QA snapshot invalidation.

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

Font attachments are controlled separately by `fonts.attach_to_mkv`. Existing attachments are preserved unless explicitly disabled. When visual QA is required, Release freezes the selected video's current identity (path, size and nanosecond mtime) from render evidence and Remux rejects a different input. This identity is a pragmatic large-media check, not a cryptographic video hash; projects requiring adversarial-grade media provenance should add a full/content hash policy.

## Quality gates

```json
{
  "quality_gates": {
    "require_semantic_qa": true,
    "require_visual_qa": true,
    "require_fonts": true
  }
}
```

Research gating is controlled by `research.mode`, not by `quality_gates.require_research` for v0.4-native titles. The old `require_research` flag is read only as a compatibility shim when a v0.3 title has no `research` object.

Relax a gate only as an explicit project decision. Research remains optional by default; semantic, visual, and font release gates remain strict.

# SubtitleFlow 0.2.0

**Evidence-driven subtitle polishing, ASS collector styling, font-safe release, and MKV remux workflow for OpenCode.**

SubtitleFlow separates source evidence, deterministic transformations, AI judgment, human approval, ASS presentation, font packaging, QA, and Remux. It works for a single already-aligned subtitle as well as full multi-source movie projects.

## Evidence is optional, not fabricated

| Role | Meaning | Typical use |
|---|---|---|
| **S** | Self-contained subtitle: timing + editable target text are already correct | simple polish / source-assisted polish |
| **A** | Timing Master | multi-source timing coordinate |
| **B** | existing Chinese translation for Japanese audio | JP Chinese editing seed |
| **C** | source-language/Japanese subtitle | semantic evidence |
| **D** | Taiwan-dub transcript | dub wording evidence |

Workflow profiles:

- `single`: S → clean Simplified-Chinese release.
- `source-assisted`: S + C → keep S timing, use C only as semantic evidence.
- `dub`: A + D → Simplified-Chinese dub release.
- `bilingual`: A + B + C → Simplified-Chinese + Japanese release.
- `full`: A + B + C + D → dub + bilingual releases.
- `auto`: derive every valid branch from available evidence.

No profile requires fake duplicate roles.

## Kiwi Collector v1 — final bundled style profile

Ordinary generated dialogue uses a fixed 1920×1080 collector profile:

| Role | Font | Size | Colour | Weight | Outline | Shadow | MarginV |
|---|---|---:|---|---|---:|---:|---:|
| Chinese `SF-ZH` | **文泉驿微米黑** | 60, ScaleY 105% | `#D2D2D2` | Bold | 2 px | 0 | 103 |
| Japanese `SF-JA` | **文泉驿微米黑** | 50 | warm gold (`ASS &H000E95CE`) | Regular | 2 px | 0 | 45 |

Both generated dialogue roles receive `\blur2` at event level. The profile is versioned at `styles/kiwi-collector-v1.json`.

### Hybrid preservation

SubtitleFlow does **not** regenerate risky authored typesetting by default. Existing complex events and common special styles such as Note/注释, Title/标题, Song/歌词, Screen/Sign, Ruby, Staff and OP/ED are preserved from the source. This lets ordinary dialogue be standardized without flattening existing screen text, songs or title work.

## Font policy and MKV attachments

Font files are intentionally **not included** in this repository. Put legally obtained local font files under `fonts/local/` or map them in the ignored local file `fonts/font-map.json`.

The Doraemon-derived collector font roles are:

- 文泉驿微米黑 — Chinese and Japanese ordinary dialogue.
- 思源黑体 CN Heavy — notes when present in source typesetting.
- 锐字云字库综艺体1.0 — movie title when present.
- 方正粗圆_GBK — lyrics, gadget names and screen text when present. `@方正粗圆_GBK` is normalized to the same family.
- 思源宋体 CN — special screen text when present.

`subflow fonts audit` scans the **compiled ASS actually being released**, including Style declarations and inline `\fn` overrides. Therefore title-specific fonts are required only when the release truly references them. Resolved files are recorded with SHA-256 and MIME metadata.

At Remux time SubtitleFlow:

1. re-checks frozen font hashes;
2. preserves existing MKV attachments by default;
3. if the input MKV already contains a same-name font attachment, extracts it with `mkvextract` and reuses it only when SHA-256 is byte-identical; a collision with different content blocks Remux;
4. attaches missing fonts with `font/ttf`, `font/otf`, or `font/collection` metadata;
5. runs `mkvmerge -J` on the output and verifies required attachments exist.

Video and audio are never transcoded by SubtitleFlow.

## Quick starts

### One subtitle that is already aligned

```bash
subflow project init movies --name "Movies"
subflow title init movies title-01 --name "Title 01" --profile single
subflow source add movies title-01 S /path/to/subtitle.ass
subflow prepare movies title-01
subflow compile movies title-01
subflow qa movies title-01
subflow fonts audit movies title-01
```

### Chinese subtitle + Japanese source evidence

```bash
subflow title init movies title-02 --name "Title 02" --profile source-assisted
subflow source add movies title-02 S /path/to/zh.ass
subflow source add movies title-02 C /path/to/ja.ass
subflow prepare movies title-02
```

S timing is never replaced by C.

### Full A/B/C/D workflow

```bash
subflow title init doraemon movie-01 --name "Movie 01" --profile full
subflow source add doraemon movie-01 A A.ass
subflow source add doraemon movie-01 B B.ass
subflow source add doraemon movie-01 C C.ass
subflow source add doraemon movie-01 D D.ass
subflow prepare doraemon movie-01
```

## OpenCode

Run `opencode` in the repository root. The project includes:

- `AGENTS.md`
- `opencode.jsonc`
- `.opencode/agents/`
- `.opencode/skills/`
- `.opencode/commands/subtitle/`

Useful commands include `/subtitle/run`, `/subtitle/review`, `/subtitle/style`, `/subtitle/fonts`, `/subtitle/semantic-qa`, `/subtitle/visual-review`, `/subtitle/release`, and `/subtitle/remux`.

## Quality guarantees

- source SHA-256 baseline and immutable source copies;
- ASS/SSA/SRT normalized before semantic editing;
- N:M alignment only when evidence needs alignment;
- Minimal Editorial Intervention;
- semantic changes require durable human review;
- protected complex/special ASS events survive compilation;
- QA snapshots become stale after upstream changes;
- font fallback does not count as a font/visual pass;
- real FFmpeg/libass rendering is separate from visual approval;
- frozen release and font hashes are rechecked before Remux.

Start with [`START_HERE.md`](START_HERE.md). See [`docs/workflow.md`](docs/workflow.md), [`docs/configuration.md`](docs/configuration.md), and [`docs/testing.md`](docs/testing.md).

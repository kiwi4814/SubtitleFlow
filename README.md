# SubtitleFlow 0.4.1

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

## Identity model

SubtitleFlow keeps three identities separate:

- `project_id`: local production workspace/collection identity;
- `title_id`: work/title identity inside that project;
- `series_id`: canonical/SRP content-series identity.

New titles default to `series_id = project_id`. Set a distinct series explicitly:

```bash
subflow title init doraemon m01 --name "M01" --profile source-assisted --series-id doraemon-theatrical
subflow title set-series doraemon m01 doraemon-theatrical
```

Older v0.4 title files without `series_id` automatically fall back to their `project_id`. A project may store SRP packs for multiple series; compatibility is checked when a pack is bound to a title and revalidated when resolving, not during project-level import.

## Kiwi Collector v1 — final bundled style profile

Kiwi Collector v1 numeric style values are authored for a 1920×1080 reference canvas. SubtitleFlow currently preserves the source ASS `PlayResX/PlayResY` instead of force-rewriting it, because changing script coordinates can corrupt protected `\pos`, `\move`, `\clip`, drawing and other authored typesetting. For non-1920×1080 source scripts, visual QA is therefore mandatory and automatic coordinate-safe profile scaling remains a known limitation.

Ordinary generated dialogue uses:

| Role | Font | Size | Colour | Weight | Outline | Shadow | MarginV |
|---|---|---:|---|---|---:|---:|---:|
| Chinese `SF-ZH` | **WenQuanYi Micro Hei** | 60, ScaleY 105% | `#D2D2D2` | Bold | 2 px | 0 | 103 |
| Japanese `SF-JA` | **WenQuanYi Micro Hei** | 50 | warm gold (`ASS &H000E95CE`) | Regular | 2 px | 0 | 45 |

Both generated dialogue roles receive `\blur2` at event level. The profile is versioned at `styles/kiwi-collector-v1.json`.

### Hybrid preservation

SubtitleFlow does **not** regenerate risky authored typesetting by default. Existing complex events and common special styles such as Note/注释, Title/标题, Song/歌词, Screen/Sign, Ruby, Staff and OP/ED are preserved from the source. This lets ordinary dialogue be standardized without flattening existing screen text, songs or title work.

## Font registry and MKV attachments

SubtitleFlow 0.4.1 keeps `fonts/font-registry.json` the authoritative registry for the five verified Kiwi Collector font roles. The registry freezes canonical ASS family names, aliases, canonical attachment filenames, exact SHA-256 identities, versions and intended roles. **For out-of-the-box personal use, the five pre-verified font binaries are included in `fonts/local/`.**

| Role | Canonical ASS family | Canonical local/attachment file |
|---|---|---|
| Chinese/Japanese dialogue | `WenQuanYi Micro Hei` | `wqy-microhei.ttc` |
| Annotation | `Source Han Sans CN Heavy` | `SourceHanSansCN-Heavy.otf` |
| Movie title | `CloudZongYiGBK` | `Reeji-CloudZongYiGBK.ttf` |
| Lyrics/prop/screen text | `方正粗圆_GBK` | `FZY4K.TTF` |
| Formal/wanted-poster text | `Source Han Serif CN` | `SourceHanSerifCN-Regular.otf` |

Legacy/internal aliases such as `文泉驿微米黑`, `思源黑体 CN Heavy`, `锐字云字库综艺体1.0`, `FZCuYuan-M03`, `@方正粗圆_GBK`, and `思源宋体 CN` resolve through the registry; `@` vertical-font prefixes normalize to the same family.

The repository comes with the verified font binaries pre-installed under `fonts/local/`. You can also re-import or update them anytime:

```bash
subflow fonts install /path/to/fonts.zip
subflow fonts verify
```

The installer matches **exact registry SHA-256**, not filenames, and writes canonical filenames under `fonts/local/`. This lets a strangely named source file still become a deterministic MKV attachment without changing its internal font names. `subflow fonts audit PROJECT TITLE` then scans the **compiled ASS actually being released**, including Style declarations and inline `\fn` overrides, validates the requested family against the font Name Table when FontTools is available, and freezes the exact local bytes.

At Remux time SubtitleFlow:

1. re-checks frozen font hashes;
2. preserves existing MKV attachments by default;
3. if the input MKV already contains a same-name font attachment, extracts it with `mkvextract` and reuses it only when SHA-256 is byte-identical; a collision with different content blocks Remux;
4. uses canonical `--attachment-name` values while leaving attachment MIME detection to current MKVToolNix by default;
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

## Optional research knowledge — SRP/1.0

Research is **not required** in SubtitleFlow 0.4.1. New titles default to:

```json
{"research":{"mode":"off","branch_map":{}}}
```

If you have a Subtitle Research Pack produced by a web model, local model, human editor, or another tool, SubtitleFlow can validate and consume it entirely offline:

```bash
subflow research validate-pack Doraemon-Research-Pack.zip
subflow research import doraemon Doraemon-Research-Pack.zip --dry-run
subflow research import doraemon Doraemon-Research-Pack.zip
subflow research bind doraemon movie-01 doraemon-canon@1.0.0
subflow research set-mode doraemon movie-01 advisory
subflow research map-branch doraemon movie-01 jp jp-zh-cn
subflow research map-branch doraemon movie-01 tw tw-dub-zh-cn
subflow research resolve doraemon movie-01
```

For collection-grade strict use, choose `enforce`, resolve/diff the Effective Knowledge, then explicitly approve it before semantic editing:

```bash
subflow research set-mode doraemon movie-01 enforce
subflow research resolve doraemon movie-01
subflow research diff doraemon movie-01
subflow research approve doraemon movie-01
```

SRP resolution is deterministic: title+branch > series+branch > title > series, with local human canon winning at the same scope. The resolver uses the title's effective `series_id`, while `project_id` remains the workspace identity. `locked` SRP canon does not enable blind string replacement. See [`docs/research.md`](docs/research.md) and the bundled [`SRP/1.0 protocol`](docs/protocols/srp-v1.md).

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
- QA snapshots bind workfiles, compiled ASS, canon, proposal files, the font registry/font-map inputs, and other deterministic evidence;
- unimported AI proposal files block Release instead of remaining invisible to the gate;
- approved semantic changes must still be materialized in the current workfile;
- optional SRP research uses immutable pack bindings, deterministic Effective Knowledge, separate semantic/provenance digests, and evidence-bound approval in `enforce` mode;
- legacy v0.3 research gates remain readable for existing titles, while new titles default to research `off`;
- semantic-QA and visual approvals carry evidence snapshots and become stale when their inputs change;
- font fallback does not count as a font/visual pass: render uses the exact audited local font files through libass `fontsdir`;
- frozen release, gate evidence, selected visual-QA media identity and font hashes are rechecked before Remux.

Start with [`START_HERE.md`](START_HERE.md). See [`docs/research.md`](docs/research.md), [`docs/fonts.md`](docs/fonts.md), [`docs/workflow.md`](docs/workflow.md), [`docs/configuration.md`](docs/configuration.md), [`docs/testing.md`](docs/testing.md), and the prioritized [`docs/roadmap.md`](docs/roadmap.md).

## Evidence-driven release policies (v0.5)

SubtitleFlow now separates **translation provenance**, **translation trust**, and **editing policy**. A human/official source is never automatically treated as high-trust. The JP branch supports `preserve`, `proofread`, `retranslate`, and assessment-first `auto`; alignment is separated from bilingual reconciliation (`exact-pair`, `source-split`, `source-merge`, `SOURCE_GAP`), and generated bilingual blocks use deterministic ZH-above-JA layout verified by FFmpeg/libass when available. Semantic releases generate first-class change/provenance/alignment/coverage/QA audit artifacts. See [`docs/evidence-driven-release.md`](docs/evidence-driven-release.md).

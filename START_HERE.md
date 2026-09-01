# START HERE — SubtitleFlow 0.4.1

SubtitleFlow is a generic subtitle production repository. Pick the evidence you actually have; do not manufacture A/B/C/D just to satisfy a workflow.

## 1. Install

Python 3.11+ is required.

```bash
python -m venv .venv
# macOS/Linux
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[full]'
subflow doctor
```

Recommended external tools:

- a current OpenCode release for optional AI orchestration/proposals/semantic QA (the executable name can vary by installed release/channel);
- OpenCC for Traditional→Simplified conversion when enabled;
- FFmpeg/ffprobe with libass for real visual preview;
- MKVToolNix (`mkvmerge`) for final Remux.

## 2. Choose the workflow profile

| What you have | Profile | Import |
|---|---|---|
| one subtitle; timing already correct | `single` | S |
| correct target subtitle + source-language subtitle | `source-assisted` | S + C |
| timing master + Taiwan-dub transcript | `dub` | A + D |
| timing + JP Chinese + Japanese source | `bilingual` | A + B + C |
| all sources | `full` | A + B + C + D |
| mixed/unknown, let engine derive branches | `auto` | whatever is real |

Example:

```bash
subflow project init movies --name "Movies"
subflow title init movies film-01 --name "Film 01" --profile single
subflow source add movies film-01 S /path/to/film.ass
subflow prepare movies film-01
```

## 2.1 Keep project, title, and series identities separate

- `project_id` is the local production workspace identity.
- `title_id` identifies a work inside the project.
- `series_id` identifies the canonical/SRP content series.

New titles default to `series_id = project_id`. Use `--series-id` for a title that belongs to another series, or update an existing title with:

```bash
subflow title init doraemon m01 --name "M01" --profile source-assisted --series-id doraemon-theatrical
subflow title set-series doraemon m01 doraemon-theatrical
```

Old v0.4 title files without `series_id` fall back automatically to `project_id`. One project can store SRP packs for multiple series; import stores the immutable pack, while bind/resolve enforce title-series compatibility.

## 3. Kiwi Collector v1 style

Default ordinary dialogue:

- Chinese: `WenQuanYi Micro Hei`, 60, ScaleY 105%, Bold, `#D2D2D2`, 2 px black outline, MarginV 103.
- Japanese: `WenQuanYi Micro Hei`, 50, Regular, warm gold `ASS &H000E95CE`, 2 px black outline, MarginV 45.
- Both: event-level `\blur2`, no style shadow.

Hybrid mode keeps risky source typesetting instead of recreating it. Existing Note/Title/Song/Screen/Sign/OP/ED/Staff/Ruby and complex positioned/drawing/karaoke events are preserved by default.

## 4. Supply and verify local fonts

`fonts/font-registry.json` freezes the verified SubtitleFlow font identities. For personal out-of-the-box usage, the five verified canonical font binaries are pre-installed in `fonts/local/`. You can also re-import or update them anytime from a directory, file, or ZIP:

```bash
subflow fonts install /path/to/fonts.zip
subflow fonts verify
```
The installer ignores source filenames as identity. It matches exact SHA-256 values, verifies internal Name Table data when FontTools is installed, and writes canonical filenames under the git-ignored `fonts/local/` directory. The five canonical mappings are:

```text
WenQuanYi Micro Hei       -> wqy-microhei.ttc
Source Han Sans CN Heavy  -> SourceHanSansCN-Heavy.otf
CloudZongYiGBK             -> Reeji-CloudZongYiGBK.ttf
方正粗圆_GBK                -> FZY4K.TTF
Source Han Serif CN        -> SourceHanSerifCN-Regular.otf
```

Old/internal family aliases remain supported through the registry. For project-specific fonts outside this default set, use the ignored `fonts/font-map.json`.

After compiling a title, audit the fonts actually referenced by the final ASS:

```bash
subflow fonts audit movies film-01
```

A production release blocks when a referenced font cannot be resolved to verified local bytes. See [`docs/fonts.md`](docs/fonts.md) for the exact hashes and MKV attachment policy.

## 5. Optional research knowledge

New titles use `research.mode=off`; you do **not** need web research or SRP to use SubtitleFlow.

If you have an SRP/1.0 directory or ZIP from any producer:

```bash
subflow research validate-pack /path/to/pack.zip
subflow research import movies /path/to/pack.zip
subflow research bind movies film-01 PACK_ID@VERSION
subflow research set-mode movies film-01 advisory
subflow research resolve movies film-01
```

Use `enforce` only when you want research canon to become a release gate. In that mode, explicitly approve the current resolved snapshot before `prepare`:

```bash
subflow research set-mode movies film-01 enforce
subflow research resolve movies film-01
subflow research approve movies film-01
```

See [`docs/research.md`](docs/research.md).

## 6. OpenCode

Start in the repository root:

```bash
opencode
```

Daily entry points:

```text
/subtitle/research PROJECT TITLE
/subtitle/prepare PROJECT TITLE
/subtitle/run PROJECT TITLE
/subtitle/review PROJECT TITLE
/subtitle/style PROJECT TITLE
/subtitle/fonts PROJECT TITLE
/subtitle/semantic-qa PROJECT TITLE
/subtitle/visual-review PROJECT TITLE
/subtitle/release PROJECT TITLE
/subtitle/remux PROJECT TITLE
/subtitle/status PROJECT TITLE
```

`/subtitle/run` is the OpenCode orchestration entry point: it reads persisted repository state and is instructed to advance only as far as the next mandatory human gate. The Python engine does not yet expose a standalone deterministic `advance` planner; OpenCode must therefore follow the persisted gate/status files rather than treating `/subtitle/run` as permission for autonomous completion.

## 7. Final MKV font attachment

After `subflow release`, the release manifest freezes final ASS and resolved font hashes. `subflow remux` preserves existing MKV attachments by default. A same-name existing font is first extracted with `mkvextract` and SHA-compared; only an identical file is reused. Missing frozen fonts are attached, then the output is checked with `mkvmerge -J`.

Never treat a local font fallback as a successful release. The goal is a self-contained MKV whose ASS looks the same after moving to another machine/player that supports Matroska ASS font attachments.

Read `docs/workflow.md` next.

## 8. Choose the editorial policy before semantic editing

New titles persist an `editorial` context in `title.json`. `preserve` is the conservative default; use `proofread` when B is only a translation seed that must be checked line-by-line against C, `retranslate` when B is merely reference material, or `auto` when quality is unknown and a structured Translation Quality Assessment should select a recommendation first. Provenance (`official`, `human-fansub`, etc.) never implies trust. See `docs/evidence-driven-release.md`.

For JP, rerun `subflow prepare` after upgrading an older title so the work directory gains first-class reconciliation and bilingual-coverage artifacts before compile.

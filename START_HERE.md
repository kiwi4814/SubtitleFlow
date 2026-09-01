# START HERE — SubtitleFlow 0.2.0

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

- OpenCode V2 for AI orchestration/research/proposals/semantic QA;
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

## 3. Kiwi Collector v1 style

Default ordinary dialogue:

- Chinese: 文泉驿微米黑, 60, ScaleY 105%, Bold, `#D2D2D2`, 2 px black outline, MarginV 103.
- Japanese: 文泉驿微米黑, 50, Regular, warm gold `ASS &H000E95CE`, 2 px black outline, MarginV 45.
- Both: event-level `\blur2`, no style shadow.

Hybrid mode keeps risky source typesetting instead of recreating it. Existing Note/Title/Song/Screen/Sign/OP/ED/Staff/Ruby and complex positioned/drawing/karaoke events are preserved by default.

## 4. Supply local fonts

Font binaries are not included. Place your legal copies under:

```text
fonts/local/
```

or copy `fonts/font-map.example.json` to the ignored local file:

```text
fonts/font-map.json
```

and map ASS family names to local files.

For the Doraemon-derived profile/source typesetting you may see these families:

- 文泉驿微米黑
- 思源黑体 CN Heavy
- 锐字云字库综艺体1.0
- 方正粗圆_GBK
- 思源宋体 CN

Audit after compile:

```bash
subflow fonts audit movies film-01
```

A production release blocks when the compiled ASS actually references an unresolved font.

## 5. OpenCode

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

`/subtitle/run` advances only as far as the next mandatory human gate.

## 6. Final MKV font attachment

After `subflow release`, the release manifest freezes final ASS and resolved font hashes. `subflow remux` preserves existing MKV attachments by default. A same-name existing font is first extracted with `mkvextract` and SHA-compared; only an identical file is reused. Missing frozen fonts are attached, then the output is checked with `mkvmerge -J`.

Never treat a local font fallback as a successful release. The goal is a self-contained MKV whose ASS looks the same after moving to another machine/player that supports Matroska ASS font attachments.

Read `docs/workflow.md` next.

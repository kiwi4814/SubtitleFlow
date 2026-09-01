# SubtitleFlow v0.2.0 Verification

Verification date: 2026-08-31

## Release verdict

**PASS for source distribution and local use, with environment-limited exceptions explicitly listed below.**

The final repository passes the automated test suite, Python bytecode compilation, package build, clean-venv installation, source-integrity stress tests, Hybrid ASS preservation checks, real FFmpeg/libass render mechanics, and real Doraemon ASS font/style analysis.

The current verification container does **not** provide `mkvmerge`, `mkvextract`, OpenCC, or OpenCode. Therefore actual MKV remux, real attachment extraction, Traditional-to-Simplified conversion, and a live OpenCode session were not executed here. Those paths have deterministic/unit coverage and `subflow doctor` reports their availability at runtime.

## Final automated checks

- Python: **3.13.5**
- `python -m compileall -q src tests tools`: **PASS**
- `python -m pytest -q`: **42 / 42 PASS**
- Coverage: **78% statements** (`2161 / 2761` statements covered; 600 missed)
- Wheel build: **PASS**
- Wheel: `dist/subtitleflow-0.2.0-py3-none-any.whl`
- Wheel SHA-256: `df3d79b1e033a9882007a36f07b3a01d51dd64ad27bc558ad6fa54ecb3bd12af`
- Fresh virtualenv installation: **PASS**
- Installed package version: **0.2.0**
- Installed CLI entry point `subflow`: **PASS**
- Installed bundled style resource `kiwi-collector-v1`: **PASS**
- `pip check`: **PASS**
- Repository font binaries (`*.ttf`, `*.otf`, `*.ttc`, `*.otc`): **0**

Ruff was not completed because Ruff is not installed in the container and the environment cannot reach the package/interpreter download endpoints required by the attempted `uv run` invocation. This is reported as an environment limitation, not as a lint pass.

## v0.2 workflow coverage

Regression tests cover the following workflow shapes:

1. `single` — self-contained S subtitle; timing and target text come from S.
2. `source-assisted` — S remains the timing/target master; C is semantic evidence only.
3. `dub` — A timing + D dub wording.
4. `bilingual` — A timing + B translated Chinese + C source-language evidence.
5. `full` — A+B+C+D, producing TW and JP branches.
6. `auto` — derives valid branches from the available evidence roles.

The single-source route deliberately performs no artificial A/B/C/D duplication.

## Final Kiwi Collector v1 style

Profile: `styles/kiwi-collector-v1.json`

### Generated Simplified Chinese dialogue (`SF-ZH`)

- Font: `文泉驿微米黑`
- Size: 60
- ScaleY: 105%
- Bold: yes
- Primary color: `&H00D2D2D2` (grey-white)
- Outline: 2 px black
- Shadow: 0
- Alignment: bottom-center
- MarginV: 103
- Event override: `\blur2`

### Generated Japanese dialogue (`SF-JA`)

- Font: `文泉驿微米黑`
- Size: 50
- ScaleY: 100%
- Bold: no
- Primary color: `&H000E95CE` (warm Doraemon-derived gold)
- Outline: 2 px black
- Shadow: 0
- Alignment: bottom-center
- MarginV: 45
- Event override: `\blur2`

### Hybrid preservation

The profile preserves complex authored events and common special styles such as notes, titles, songs, screens/signs, ruby, staff, effects, karaoke, and OP/ED/IN-prefixed styles. Special source typesetting is kept instead of being flattened into `SF-ZH` / `SF-JA`.

Profile SHA-256: `e0195beb1dc039de9def1a2c763e5074fec6aeb0118a2fb662ddd01337d61837`

## Font policy and MKV attachment safety

SubtitleFlow v0.2.0 intentionally ships **no font binary files**. Users place their legally held fonts under `fonts/local/` or provide `fonts/font-map.json` based on `fonts/font-map.example.json`.

The selected Doraemon style family set is:

- `文泉驿微米黑` — Chinese/Japanese ordinary dialogue
- `思源黑体 CN Heavy` — notes
- `锐字云字库综艺体1.0` — movie title
- `方正粗圆_GBK` — songs, gadget names, screen text
- `思源宋体 CN` — special wanted-poster screen text

The font audit scans fonts actually referenced by the final ASS, including inline `\fn` tags. A leading `@` used for vertical Windows/ASS fonts is normalized, so `@方正粗圆_GBK` and `方正粗圆_GBK` resolve to the same family.

For each resolved font file, the release freezes:

- family name
- local file path
- attachment filename
- MIME type
- file size
- SHA-256
- reason(s) it is required by the final ASS

Before remux, SubtitleFlow rechecks the frozen font hash and size. Missing or changed font files block production remux.

If the input MKV already contains an attachment with the same filename, v0.2.0 does not trust filename/size alone: it uses `mkvextract` when available to extract the existing attachment and compares SHA-256. Identical content is reused; a same-name/different-hash collision blocks remux. If such a collision must be resolved but `mkvextract` is unavailable, remux blocks rather than guessing.

Missing fonts are attached with `mkvmerge` using modern attachment options and font MIME types. The output MKV is identified again after remux to verify expected attachment names/sizes are present.

## Real Doraemon 2023 ASS analysis

Source:

`哆啦A梦：大雄与天空的理想乡 (2023) - 1080p.BluRay Remux.H.264.DTS-HD TrueHD Dolby Atmos MA 7.1.chs.ass`

Observed:

- Total events: **3435**
- CN ordinary dialogue: **1678**
- JP ordinary dialogue: **1678**
- Title: **1**
- Notes: **12**
- Songs: **66**
- Hybrid-preserved special-style events: **79 / 79**
- Unique referenced font families: **5**
- `@方正粗圆_GBK` correctly normalized to `方正粗圆_GBK`
- Source SHA before/after analysis: `9f788f4275ed43fd49fcc185517ca22f195ff1b4d3bed0e8c80470d0f084c678`
- Source unchanged: **PASS**

Machine-readable evidence: `verification/doraemon-2023-style-check.json`.

## Legacy Doraemon stress tests

### 1980 large ASS

- Parsed events: **824**
- Normalize: **PASS**
- Alignment/workfile generation: **PASS**
- TW compile: **PASS**
- JP compile: **PASS**
- Deterministic QA: **PASS**
- Mechanical release path: **PASS**
- Source SHA before/after: `cc2ea32bb92ed59928fb06d150934b543af5436970d61a5c7e58a6c60101e08b`
- Source unchanged: **PASS**

The stress harness disables production-only research/semantic/visual/font gates because its purpose is parser/workfile/compiler round-trip verification, not to declare that historical subtitle final.

### 2008 complex ASS

- Protected events detected: **7363**
- Protected events retained after round-trip: **7363**
- Result: **7363 / 7363 PASS**

Machine-readable evidence: `verification/verification-results-v020.json`.

## FFmpeg/libass render verification

- FFmpeg: **7.1.5**
- `ffprobe`: available
- libass subtitle filter: available
- Synthetic 1920x1080 H.264 test video: generated successfully
- `examples/kiwi-collector-style-specimen.ass`: rendered successfully
- Non-empty output PNG: **PASS**

This verifies the ASS is renderable and the render path works. It does **not** certify the exact final typography because the selected user fonts are not installed in this verification container; libass therefore uses fallback fonts here. Exact-font visual approval must be performed on the user's machine after the selected font files are available.

Machine-readable evidence: `verification/render-v020.json`.

## Environment-limited checks

The following tools were absent from the verification container:

- `mkvmerge`: **not installed** — actual final MKV remux was not executed.
- `mkvextract`: **not installed** — real existing-attachment SHA extraction was not executed; collision logic is covered by tests.
- OpenCC: **not installed** — real `t2s` conversion was not executed.
- OpenCode: **not installed** — `.opencode/` assets were statically validated, but no live OpenCode session was started.

Available:

- Git
- FFmpeg / ffprobe / libass
- FontTools in the development verification environment

See `verification/environment-v020.json`.

## Final artifact acceptance criteria

Before the ZIP is delivered, the release procedure additionally requires:

1. remove caches/build scratch data;
2. keep the built wheel and verification evidence;
3. create the ZIP;
4. verify the ZIP contains no font binaries;
5. extract the ZIP into a separate temporary directory;
6. run all 42 tests from the extracted artifact;
7. install the wheel from the extracted artifact into another clean virtualenv;
8. confirm version, CLI entry point, and bundled style resource;
9. record the final ZIP SHA-256.

The final response reports the results of those artifact-level checks.

## Artifact-level verification result

The distribution ZIP was built and tested as an independent artifact:

- ZIP contained font binaries: **0**
- ZIP extracted to a separate temporary directory: **PASS**
- Test suite executed from extracted ZIP: **42 / 42 PASS**
- `compileall` executed from extracted ZIP: **PASS**
- Included wheel installed into a second clean virtualenv: **PASS**
- `pip check` in that virtualenv: **PASS**
- Installed package version: **0.2.0**
- Installed `kiwi-collector-v1` package resource: **PASS**
- Installed dialogue profile check: Chinese `文泉驿微米黑` 60; Japanese `文泉驿微米黑` 50: **PASS**
- Installed `subflow doctor` starts successfully: **PASS**

The final ZIP SHA-256 is reported alongside the download link because embedding a ZIP's own hash inside itself would change the archive hash.

# SubtitleFlow v0.3.0 Verification

Date: 2026-08-31

This file records the v0.3.0 release verification after the v0.2 audit-hardening cycle and the verified-font registry integration. Historical v0.2 audit evidence remains under `verification/AUDIT-20260831.md` and the `*-v020.json` records.

## Result summary

The v0.3.0 working tree passes the complete automated suite, bytecode compilation, wheel build, clean non-editable wheel installation and installed CLI smoke checks. The five user-supplied Kiwi Collector fonts were independently hashed and parsed with FontTools, imported by exact registry SHA, audited through a real compiled ASS that referenced all five roles, and rendered through FFmpeg/libass with the exact audited local font directory.

The source release intentionally contains **zero font binaries**. `fonts/font-registry.json` contains only font identity/policy metadata; locally supplied bytes live under ignored `fonts/local/`.

## Automated checks actually executed

Environment:

- Python: 3.13.5
- platform: Linux x86_64
- FFmpeg / ffprobe: available
- FFmpeg libass filter: available
- FontTools: available in the development environment (4.63.0)
- MKVToolNix `mkvmerge` / `mkvextract`: not installed
- Ruff: not installed in the execution environment
- OpenCC: not installed
- OpenCode: not installed

Executed checks:

```text
python -m pytest --collect-only     -> 68 tests collected
python -m pytest -q                 -> 68/68 PASS
pytest + coverage                   -> 81% statement coverage
python -m compileall -q src tools tests -> PASS
pip wheel --no-deps --no-build-isolation -> PASS
clean venv wheel install            -> PASS
pip check                            -> PASS
installed package version           -> 0.3.0
installed subflow doctor            -> PASS
packaged kiwi-collector-v1 resource -> present
wheel font binaries                 -> 0
```

The clean wheel installation intentionally omitted optional dependencies. `subflow fonts verify` still succeeded there by exact registry SHA, demonstrating that registry byte identity does not require FontTools. Name Table verification remains an additional stricter check when the `fonts`/`full` extra is installed.

## Verified default font registry

Registry id: `subtitleflow-default-fonts-v1`

Registry SHA-256:

```text
aa4e30bcafb77dda1565c86e72c93e98fd35c2c021518b8f40be9b685d3e313d
```

The actual uploaded font set was verified as:

| Role | Canonical family | Canonical file | SHA-256 | FontTools metadata |
|---|---|---|---|---|
| dialogue | `WenQuanYi Micro Hei` | `wqy-microhei.ttc` | `e4bca8df123ce01b104780f576ea1a58b9a5ff1662a91124b6d3180cb6c88212` | PASS |
| annotation | `Source Han Sans CN Heavy` | `SourceHanSansCN-Heavy.otf` | `88c749b0a54a0800124ded6544e399302ed224aa49992ea364b88769f825c54c` | PASS |
| movie title | `CloudZongYiGBK` | `Reeji-CloudZongYiGBK.ttf` | `cdad5e1446c45a472fe085f99a661e2dbaa035cc9c3f5fb80efee8744f92f4d1` | PASS |
| screen text | `方正粗圆_GBK` | `FZY4K.TTF` | `c071e0e91406af290cfbb495c42ae56a36cca7a501c11cb6613893d5adb951c0` | PASS |
| formal screen text | `Source Han Serif CN` | `SourceHanSerifCN-Regular.otf` | `3754ea669c530e2473354f8f6d9f79680a44d7e26ec7d00eeabee4a7e0753c5d` | PASS |

The title font arrived under a non-canonical/mangled source filename. `subflow fonts install` identified it by SHA-256 and stored it as `Reeji-CloudZongYiGBK.ttf`, proving that file naming is not used as font identity.

## Real five-font compile/audit/render verification

A disposable 1920×1080 ASS fixture was created with:

- ordinary dialogue → `WenQuanYi Micro Hei`;
- Note → legacy alias `思源黑体 CN Heavy`;
- Title → legacy alias `锐字云字库综艺体1.0`;
- ScreenText → `方正粗圆_GBK`;
- WantedPoster → legacy alias `思源宋体 CN`.

The fixture was processed through a real `single` SubtitleFlow title. Hybrid compilation retained the authored special roles while generated dialogue used the canonical Kiwi Collector family. Font audit resolved **5/5** attachments with their exact registered SHA values.

A real FFmpeg/libass render then selected:

```text
WenQuanYi Micro Hei      -> WenQuanYiMicroHei
思源黑体 CN Heavy         -> SourceHanSansCN-Heavy
锐字云字库综艺体1.0       -> CloudZongYiGBK
方正粗圆_GBK              -> FZY4K--GBK1-0
思源宋体 CN               -> SourceHanSerifCN-Regular
```

The resulting PNG was opened and visually inspected. All five roles rendered visibly. The frame SHA-256 was:

```text
bea5326baf0ba10ad5534b5195ad39193d45e339958eefd169c5c5c1b66cc447
```

Machine-readable sanitized evidence is stored in `verification/font-registry-v030-real.json`.

## MKV attachment behavior verified in code/tests

v0.3.0 no longer forces `--attachment-mime-type` by default. It keeps canonical `--attachment-name` and `--attach-file`, allowing current MKVToolNix to auto-detect MIME. Audit/release evidence still records MIME metadata.

Regression tests verify command construction, frozen font hash re-checks, same-name/different-SHA collision blocking, and input/output path safety. However **a real MKVToolNix Remux was not executed in this environment** because `mkvmerge`/`mkvextract` are not installed. Therefore no claim of real Remux success is made.

## Known remaining gaps

The highest-priority post-0.3.0 gaps remain:

1. low-confidence Alignment has no durable `Approve / Adjust / Defer` review ledger;
2. Timing QA does not yet provide complete real-video range/drift/extreme-duration coverage;
3. font QA does not yet prove per-character `cmap` coverage;
4. libass `fontselect` output is not yet persisted as a formal no-fallback gate by the engine;
5. output MKV attachments are structurally post-identified but are not yet re-extracted and SHA-compared end-to-end;
6. Python 3.11/3.12 and Windows/macOS remain declared/reviewed targets rather than executed CI matrix evidence;
7. wheel/source builds are not yet configured for reproducible byte-identical artifacts.

See `docs/roadmap.md` for the prioritized implementation order.

## Artifact-from-ZIP verification

A release candidate archive was created with the built 0.3.0 wheel but without local font binaries, unpacked into a fresh directory, and verified from the unpacked bytes:

```text
pytest collection                         -> 68 tests
pytest                                   -> 68/68 PASS
compileall src/tools/tests                -> PASS
wheel rebuild from extracted source       -> PASS
ZIP-contained wheel clean-venv install    -> PASS
pip check                                 -> PASS
installed version                         -> 0.3.0
installed subflow --help / doctor          -> PASS
font binaries in ZIP                      -> 0
cache/build/egg-info pollution in ZIP     -> 0
font registry entries                     -> 5
```

The first release wheel and the wheel rebuilt from extracted source were functionally equivalent but had different SHA-256 values (`b3b5a4b4...` versus `254b30f6...`), confirming the already documented reproducible-build gap. No claim of byte-reproducible packaging is made for 0.3.0.

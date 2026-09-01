# SubtitleFlow 0.3.0 font and MKV attachment policy

This document defines the verified Kiwi Collector font identities used by SubtitleFlow 0.3.0 and the boundary between repository metadata, user-local font bytes, ASS matching, visual QA, and Matroska attachments.

## 1. Architecture

Font handling is deliberately split into two layers:

```text
fonts/font-registry.json       committed identity/policy evidence
        ↓
user-supplied file/dir/ZIP
        ↓  exact SHA-256 match
fonts/local/                   ignored local binary store
        ↓
compiled ASS font scan
        ↓
Name Table + SHA audit
        ↓
FFmpeg/libass exact fontsdir render
        ↓
frozen Release Manifest
        ↓
MKV attachment + post-identification
```

The repository never infers an ASS family from a filename. The font's internal Name Table and the registry define identity; filenames are only stable asset/attachment names.

## 2. Verified default registry

| Role | Canonical ASS family | Canonical file | SHA-256 | Version |
|---|---|---|---|---|
| Chinese/Japanese dialogue | `WenQuanYi Micro Hei` | `wqy-microhei.ttc` | `e4bca8df123ce01b104780f576ea1a58b9a5ff1662a91124b6d3180cb6c88212` | `0.2.0-beta` |
| Annotation | `Source Han Sans CN Heavy` | `SourceHanSansCN-Heavy.otf` | `88c749b0a54a0800124ded6544e399302ed224aa49992ea364b88769f825c54c` | `2.005` |
| Movie title | `CloudZongYiGBK` | `Reeji-CloudZongYiGBK.ttf` | `cdad5e1446c45a472fe085f99a661e2dbaa035cc9c3f5fb80efee8744f92f4d1` | `GBK 1.0.0.0` |
| Lyrics/prop/screen text | `方正粗圆_GBK` | `FZY4K.TTF` | `c071e0e91406af290cfbb495c42ae56a36cca7a501c11cb6613893d5adb951c0` | `5.32` |
| Formal/wanted-poster text | `Source Han Serif CN` | `SourceHanSerifCN-Regular.otf` | `3754ea669c530e2473354f8f6d9f79680a44d7e26ec7d00eeabee4a7e0753c5d` | `2.003` |

These hashes are the authoritative identities for this registry revision. A same filename with different bytes is not equivalent.

### Accepted aliases

- `文泉驿微米黑` → `WenQuanYi Micro Hei`
- `思源黑体 CN Heavy` → `Source Han Sans CN Heavy`
- `CloudZongYiGBK1.0`, `锐字云字库综艺体1.0`, `锐字云字库综艺体GBK` → `CloudZongYiGBK`
- `FZCuYuan-M03`, `FZY4K--GBK1-0` → `方正粗圆_GBK`
- `思源宋体 CN` → `Source Han Serif CN`
- a leading ASS vertical-font marker such as `@方正粗圆_GBK` normalizes to the same non-`@` family.

The WenQuanYi TTC also contains a Mono face. SubtitleFlow dialogue intentionally requests the non-Mono `WenQuanYi Micro Hei` face.

## 3. Roles

```text
DialogueZH / DialogueJP
→ WenQuanYi Micro Hei
→ wqy-microhei.ttc

Annotation
→ Source Han Sans CN Heavy
→ SourceHanSansCN-Heavy.otf

MovieTitle
→ CloudZongYiGBK
→ Reeji-CloudZongYiGBK.ttf

ScreenText / lyric / prop
→ 方正粗圆_GBK
→ FZY4K.TTF

WantedPoster / document / newspaper / formal screen text
→ Source Han Serif CN
→ SourceHanSerifCN-Regular.otf
```

These are defaults for the Kiwi Collector system, not a prohibition on project-specific fonts. A title may still map extra fonts through its local `font-map.json`; the final attachment set is derived from the compiled ASS actually being released.

## 4. Supplying fonts locally

Font binaries are not source-controlled. Import user-provided/local-licensed assets with:

```bash
subflow fonts install /path/to/fonts.zip
subflow fonts verify
```

The source can be a file, directory, or ZIP. Incoming filenames are not trusted as identity. SubtitleFlow hashes each candidate and copies a matching font to its canonical `fonts/local/` name. Existing conflicting local bytes are rejected unless replacement is explicitly requested.

`subflow fonts verify` checks every registered local file for exact SHA-256 and size, and, when FontTools is available, reparses the Name Table. This is a repository-local reproducibility check; it does not change the internal names of the font.

## 5. Font licensing boundary

The registry can record open-font and proprietary/local-license metadata, but SubtitleFlow does not treat that metadata as permission to redistribute binaries.

- `fonts/local/` is ignored.
- public/source release ZIPs must exclude all font binaries.
- the user supplies fonts they are permitted to use locally.
- final personal MKV attachment policy remains a user/project licensing decision.

This boundary is especially important for the Founder and Reeji fonts.

## 6. ASS matching and QA

After compilation:

```bash
subflow fonts audit PROJECT TITLE
```

The audit scans:

- every Style actually referenced by events;
- inline `\fn` overrides;
- normalized vertical `@Family` references.

For registry-managed families, success requires the exact registered bytes. With FontTools installed, the requested canonical family or approved alias must also be exposed by the font Name Table. Audit evidence records parsed family/full/PostScript names, versions, weights/fsType where available, MIME metadata, size and SHA-256.

Release is blocked when a required family is unresolved, has the wrong registered hash, maps to the wrong internal font, or would collide with a same attachment name backed by different bytes. Silent fallback is not a pass.

## 7. FFmpeg/libass visual QA

External ASS rendering and Matroska playback are different environments. For visual preview, SubtitleFlow does not assume fonts installed in Windows/Linux are authoritative. The render path stages the **exact files from the successful font audit** into a dedicated libass `fontsdir` and records the font SHA set in render evidence.

A successful FFmpeg render only means frames were produced. Human or visual-model review is still required to confirm that the intended family was selected, no fallback occurred, and text did not clip/collide.

## 8. MKV attachments

The Release Manifest freezes the exact font attachment filenames, local paths, sizes, MIME metadata and SHA-256 values. At Remux time SubtitleFlow revalidates the frozen bytes.

If the input MKV already contains a same-name attachment, SubtitleFlow uses `mkvextract` to extract it and compares SHA-256:

- identical → reuse existing attachment;
- different → block Remux;
- `mkvextract` unavailable while comparison is required → block instead of guessing.

For new attachments SubtitleFlow passes the canonical attachment filename but leaves MIME detection to current MKVToolNix by default. The audited MIME remains evidence; it is not forced onto `mkvmerge` unless a future compatibility policy explicitly requires that behavior. Legacy font MIME mode is not the default.

After muxing, `mkvmerge -J` is used to confirm required attachment names/sizes are present. A future archival-hardening step can additionally re-extract every output font and compare SHA-256.

## 9. Windows and Debian

System installation is useful for Aegisub/Subtitle Edit/manual preview, but final SubtitleFlow release correctness is based on local audited files and MKV attachments, not on a workstation's fallback configuration.

Debian users who also want system-wide preview can install copies under `~/.local/share/fonts/SubtitleFlow/`, run `fc-cache -fv`, and inspect `fc-match`, but that remains an editor convenience rather than release evidence.

## 10. Current limitations / next font QA work

0.3.0 verifies file identity and Name Table matching. It does not yet prove that every character used by the final ASS exists in the selected face's `cmap`, nor does it parse libass font-selection diagnostics into a formal no-fallback gate. Those are deliberate next hardening targets rather than claims of 0.3.0.

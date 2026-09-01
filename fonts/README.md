# SubtitleFlow local font assets

SubtitleFlow 0.3.0 separates **font identity/policy** from **font bytes**.

- `font-registry.json` is committed and authoritative for the five verified Kiwi Collector roles.
- `local/` is git-ignored and contains user-provided/local-licensed binaries only.
- `font-map.json` is git-ignored and remains available for project-specific fonts outside the default registry.

Import and verify a user-provided directory/file/ZIP:

```bash
subflow fonts install /path/to/fonts.zip
subflow fonts verify
```

The importer identifies registered fonts by exact SHA-256, not by the incoming filename, then stores them under canonical names:

| Role | ASS family | Canonical file |
|---|---|---|
| Dialogue ZH/JP | `WenQuanYi Micro Hei` | `wqy-microhei.ttc` |
| Annotation | `Source Han Sans CN Heavy` | `SourceHanSansCN-Heavy.otf` |
| Movie title | `CloudZongYiGBK` | `Reeji-CloudZongYiGBK.ttf` |
| Lyrics/prop/screen | `方正粗圆_GBK` | `FZY4K.TTF` |
| Formal/wanted poster | `Source Han Serif CN` | `SourceHanSerifCN-Regular.otf` |

After compilation, run:

```bash
subflow fonts audit PROJECT TITLE
```

The audit resolves only fonts actually referenced by the compiled ASS, checks registry SHA/name-table identity when possible, freezes MIME/size/SHA metadata, and blocks ambiguous same-name/different-byte attachments. Final source distributions must not contain `.ttf`, `.otf`, `.ttc`, or `.otc` binaries.

See [`../docs/fonts.md`](../docs/fonts.md) for exact hashes, aliases and MKV policy.

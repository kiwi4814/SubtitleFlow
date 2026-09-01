# Local font assets

SubtitleFlow does **not** bundle or redistribute fonts. Put locally licensed font files under
`fonts/local/` or create `fonts/font-map.json` from `font-map.example.json`.

The default `Kiwi Collector v1` profile uses `文泉驿微米黑` for both Chinese and Japanese
dialogue. Preserved source effects may additionally reference `思源黑体 CN Heavy`,
`锐字云字库综艺体1.0`, `方正粗圆_GBK`, and `思源宋体 CN` when the source ASS uses them.

Run:

```bash
subflow fonts audit PROJECT TITLE
```

The audit extracts the fonts actually referenced by the compiled ASS, resolves local font files,
records SHA-256 hashes, and blocks release/remux if a required family is unresolved.

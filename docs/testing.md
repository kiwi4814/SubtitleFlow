# Testing and verification

## Required code checks

```bash
python -m compileall -q src
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

## v0.2-specific regression areas

Tests must cover:

- S-only `single` workflow preserving S timings;
- `source-assisted` attaching C semantics without retiming S;
- missing-role profile gates;
- Hybrid preservation of plain special Style events even without complex tags;
- final Kiwi Collector SF-ZH/SF-JA values and `\blur2` event override;
- vertical ASS font name normalization (`@Font` → `Font`);
- real font-file metadata/hash audit;
- release freeze of font attachments;
- modern MKV attachment option construction;
- stale font hash rejection.

## Real-source stress checks

Do not commit copyrighted subtitle fixtures. When available locally, use representative large/complex ASS files for manual release verification:

1. record source SHA-256;
2. normalize/compile using a disposable project;
3. verify source SHA remains unchanged;
4. count protected source events before/after;
5. scan actual font family references;
6. render real/synthetic video with FFmpeg/libass when available.

For the Doraemon 2023 style source used during v0.2 development, the expected referenced family set is five unique families: 文泉驿微米黑, 思源黑体 CN Heavy, 锐字云字库综艺体1.0, 方正粗圆_GBK, 思源宋体 CN. The source file itself is not included in the package.

## Packaging checks

Before delivery:

1. build a wheel;
2. install it into a fresh virtual environment;
3. run the installed `subflow doctor`;
4. confirm packaged `kiwi-collector-v1` data is available;
5. create the final ZIP;
6. unpack that ZIP into another directory;
7. rerun the test suite and a fresh wheel/install smoke test from the extracted artifact;
8. verify the ZIP contains no `.ttf`, `.otf`, `.ttc`, or `.otc` files.

`mkvmerge` success may be claimed only when the binary is installed and a real Remux was executed. If unavailable, record command construction and postcondition logic as tested but real mux execution as unverified.

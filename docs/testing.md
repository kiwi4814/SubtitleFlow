# Testing and verification

## Required code checks

```bash
python -m compileall -q src tools tests
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

## v0.4 regression areas

Tests must cover:

- SRP/1.0 structural + semantic validation, including `series_branch` scope and pack containment;
- safe ZIP/directory intake, path traversal/symlink rejection, strict UTF-8 and duplicate-key rejection;
- immutable/idempotent SRP imports and exact digest bindings;
- new-title research default `off`, advisory non-blocking behavior, enforce approval/blocking behavior, and v0.3 legacy compatibility;
- deterministic scope precedence (title+branch > series+branch > title > series) plus same-scope local human override;
- cross-pack value and alias-policy conflicts;
- semantic vs provenance digest invalidation, with provenance-only changes preserving deterministic/visual QA where appropriate;
- Release Manifest freezing compact SRP identities/digests;
- S-only `single` workflow preserving S timings;
- `source-assisted` attaching C semantics without retiming S;
- missing-role profile gates;
- Hybrid preservation of plain special Style events even without complex tags;
- final Kiwi Collector SF-ZH/SF-JA values and `\blur2` event override;
- vertical ASS font name normalization (`@Font` → `Font`);
- exact registry SHA import/verification plus real font-file metadata audit;
- release freeze of font attachments;
- registry/font-map internal-family validation, canonical attachment naming, and same-name/different-SHA attachment collisions;
- stale proposal/source/canon/research/semantic/visual evidence rejection;
- approved semantic changes remaining materialized after workfile regeneration;
- render use of exact audited `fontsdir` assets and failure invalidation;
- visual-QA media binding through Release/Remux;
- transactional style configuration updates;
- modern MKV attachment construction using MKVToolNix MIME auto-detection;
- stale font hash rejection;
- OpenCode permissions not blanket-allowing human-impacting `subflow` commands.

## Real-source stress checks

Do not commit copyrighted subtitle fixtures. When available locally, use representative large/complex ASS files for manual release verification:

1. record source SHA-256;
2. normalize/compile using a disposable project;
3. verify source SHA remains unchanged;
4. count protected source events before/after;
5. scan actual font family references;
6. render real/synthetic video with FFmpeg/libass when available.

For the five-font Kiwi Collector fixture, the canonical family set is: `WenQuanYi Micro Hei`, `Source Han Sans CN Heavy`, `CloudZongYiGBK`, `方正粗圆_GBK`, and `Source Han Serif CN`. Legacy/internal aliases may appear in historical ASS and must resolve to these identities without changing source evidence.

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

## v0.5 release-system regressions

The release-system suite covers human preserve/proofread/retranslate behavior, explicit-user-policy priority over Auto, evidence conflict grading, 1:N split provenance, N:1 merge provenance, SOURCE_GAP/fabrication guards, alignment semantic-risk signals, clean-vs-bilingual geometry, ZH1+JA2 collision inversion, OP bilingual layout, Style2 classification, translator-credit exclusion, style-profile drift, release audit fields, and a real FFmpeg/libass synthetic render smoke test. `tests/fixtures/release-system/` is the durable real-world specimen for 1+1, 1+2, screen-text overlap, OP, source gap, human proofread and primary-vs-secondary evidence conflict.

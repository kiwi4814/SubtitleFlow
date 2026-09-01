# Doraemon Subtitle Evidence Library — AI README

> **This is an immutable evidence library, not an edited subtitle release.**

## 1. Purpose

This library organizes the uploaded `字幕原始素材.zip` into stable, provenance-aware evidence for the long-running **哆啦A梦剧场版全收藏字幕工程** and later SubtitleFlow intake. The subtitle payloads were **not translated, normalized, re-serialized, retimed, restyled, converted between Simplified/Traditional Chinese, merged, split, or otherwise rewritten**.

The only permitted operation on subtitle payloads was archive decompression followed by filesystem-level binary copy/rename.

## 2. Integrity contract

- Source subtitle files scanned: **135**
- High-confidence classifications: **61**
- Medium-confidence classifications: **74**
- Unresolved subtitle files: **0**
- `content_modified_files = 0`
- Every inventory row contains `sha256_before`, `sha256_after`, and `byte_identical`.
- `byte_identical` is `true` for every organized subtitle.
- `_RAW_PACKS/` stores the uploaded master ZIP and all four inner original archives byte-for-byte; see `RAW_PACKS_MANIFEST.json`.

## 3. Stable Movie IDs

Mainline theatrical movies use `M01`…`M44`. Movie ID is the primary identity; year/title are descriptive labels.

Important exceptions:

- No mainline movie in **2005**.
- `M41` uses theatrical release year **2022**; its official Japanese title remains `のび太の宇宙小戦争 2021`.
- `STAND BY ME ドラえもん` is never inserted into the M sequence. It uses `SBM01` (2014), while `STAND BY ME ドラえもん 2` uses `SBM02` (2020).
- The source P03 compilation internally numbers the 2014 STAND BY ME film as item 35. That local pack index is **not** treated as a Movie ID.

Full mapping: `MOVIE_CATALOG.json`.

## 4. Directory semantics

Each movie contains:

- `01_JA_SOURCE/` — Japanese source subtitles: WOWOW, Netflix ja[cc], JPTV, NBN, etc.
- `02_ZH_JP_AUDIO/` — Chinese translation-seed / Japanese-audio-oriented subtitle evidence. This includes the explicit WOWOW-retimed Simplified Chinese pack and the 1980–2016 Chinese draft compilation.
- `03_ZH_TW_OFFICIAL/` — Taiwan official release subtitles **only when provenance proves that status**.
- `04_ZH_TW_DUB/` — Taiwan Mandarin dub transcript wording **only when evidence proves audio-line correspondence**.
- `05_ZH_CN_OFFICIAL/` — Mainland China official theatrical/streaming/release subtitles.
- `06_BILINGUAL/` — Original files that already contain two language layers; files are never split for archiving.
- `80_OTHER/` — other understood evidence outside the main categories.
- `90_UNCLASSIFIED/` — genuinely unresolved evidence. It is empty in v1 because current files could be safely classified without asserting unproven official/dub status.

## 5. Critical provenance rules

1. **`zh-TW official != TW dub`.** A Taiwan official subtitle is not automatically a Taiwan-dub transcript.
2. **Traditional Chinese != Taiwan provenance.** In P03, `.tc.ass` is recorded as `zh-TW` only as the source branch/script label. It does **not** prove Taiwan origin, official release status, or Taiwan-dub wording.
3. **`zh-CN != automatically JP-audio`.** Category 02 is used only where the source-pack context supports a translation-seed/Japanese-audio role. P03 is marked **medium confidence** because it is a Chinese draft/fansub compilation without direct audio-track provenance.
4. `source` and `download_provider` are separate. Example: the modern Japanese pack was downloaded via **Jimaku**, while its subtitle sources are Netflix/WOWOW/NBN/JPTV.
5. P02 uses `source = WOWOWCN` to mean **Chinese subtitle evidence retimed for WOWOW video**. It does not claim WOWOW authored the Chinese translation.
6. `creator` uses explicit metadata only. P02/P03 ASS `Original Script` credits are retained; where absent, creator is `Unknown`. No creator is guessed.

## 6. Original filenames and paths

`inventory.json` and `inventory.csv` retain provenance fields:

- `original_pack`
- `original_path`
- `original_filename`
- `archive_member_filename`
- `archive_member_name_raw`

For the modern Jimaku-derived pack, `original_filename` comes from that pack's own upstream inventory, so names such as `[Fumi-Raws] ... .ass` survive even though the inner ZIP had already standardized its stored member name.

For P03, the legacy ZIP stored GBK filenames without the UTF-8 flag. `archive_member_name_raw` preserves the decoder-visible legacy form, while `original_path` records the recovered intended Chinese filename. **Subtitle file bytes are unaffected by filename recovery.**

## 7. Duplicate policy

See `duplicates.json`.

- SHA-256 equality => `byte-identical` duplicate group.
- Same-movie/same-language high cue-text + timing similarity => `possible-duplicate` analytical relationship.
- No subtitle is deleted, merged, or preferred automatically.
- SC/TC variants are retained independently and are not collapsed merely because they may be Simplified/Traditional counterparts.

## 8. How SubtitleFlow should consume this library

Recommended later workflow:

1. Read `inventory.json` first; select by `movie_id`.
2. Prefer **objective evidence properties** (`language`, `evidence_type`, `source`, provenance) instead of pre-assigning workflow roles.
3. Verify `sha256_after` before use.
4. Use `01_JA_SOURCE` as candidate source-semantics evidence.
5. Use `02_ZH_JP_AUDIO` as candidate editable/translation-seed evidence; review medium-confidence records before elevating them.
6. Only use `03/04/05` for official/dub wording when those categories actually contain proven evidence.
7. Assign SubtitleFlow roles such as timing/editable_text/source_semantics/dub_wording/official_localization **during intake**, not inside this archive.

This library intentionally does **not** hard-code old A/B/C/D workflow roles.

## 9. Current source-pack reality

The modern `Doraemon-JP-2006-2025.zip` contains actual Japanese subtitle payloads for 11 movies only. Its internal inventory records failed/missing acquisition attempts for other years. v1 ingests only files physically present in the uploaded evidence and does not silently download replacements.

The P02 note explicitly documents that its 25 Simplified Chinese subtitles were adjusted to the WOWOW HD timing. The P03 compilation contributes Simplified/Traditional Chinese branches through 2016 plus `SBM01`.

## 10. Catalog references

The stable catalog was cross-checked against official Doraemon movie history pages:

- https://doraeiga.com/link/
- https://dora-world.com/contents/4261
- https://dora-world.com/contents/1712

These URLs validate series sequencing/special branches; they are not provenance claims for any individual subtitle payload.

# M01 regression fixtures — Doraemon: Nobita's Dinosaur

Use these as known failure classes, not as a substitute for full-title review. Keep only minimal/synthetic snippets in public repositories; the complete M01 Golden ASS may remain private.

| Time / sample | Failure class | Expected lesson |
|---|---|---|
| 01:33 | source fragment split | `これ 本物？` and `もちろんさ` must not be swallowed into one target line. |
| 02:33 `一个恐龙爪子…` | component-prefix loss | component parsing must not consume semantic leading `一`; round-trip source text after component extraction. |
| single component labeled `split` | false split accounting | one meaningful component + one final ref is not a split; verify all split dispositions structurally. |
| 02:50 | source notation leakage | `《...》` is delivery metadata in this source family; hide marker while preserving provenance. |
| 03:04–03:08 | cross-cue notation | narration/source-notation span crosses cue boundaries; per-line regex is insufficient. |
| 04:39–04:48 | literal quotation | Japanese quotation marks used for read/quoted text must not be stripped as generic metadata. |
| 06:49–06:59 | source over-assembly + layout | do not pull multiple continuation fragments into one severe-compression line. |
| 17:21 | deterministic layout | bilingual spacing must be release-profile driven. |
| clean monolingual Chinese at y=430 | presentation-mode leakage | bundled 640x480 `clean` Chinese must project to y=453; y=430 is the bilingual Chinese row. Scan all cues, not one. |
| 24:12 | sequential presentation split | split a coarse multi-clause bilingual cue sequentially rather than use `fscx83` or two-line JA. |
| ~25:45 `那只恐龙我们要定了吗？` | plausible-Han OCR particle | challenge `吗/嘛`; context/source evidence supports assertive `那只恐龙我们要定了嘛！`. |
| ~34:38 dub `哆啦A梦！` vs JA `目が回る！` | dub divergence anti-overwrite | Taiwan hard-sub independently supports the dub wording; Japanese mismatch is challenge evidence, not replacement authority. |
| readable dub cue `行礼` without JA counterpart | dub-only source authenticity | absence from the Japanese track is not deletion evidence; preserve readable dub hard-sub text and defer audio-exact verification. |
| `偶雨 / 阏 / 量倒 / 程快` | plausible-looking OCR glyph errors | do not stop at garbage detection; scan valid-Han confusables with semantics/context. |
| `是……` vs corroborated affirmative `はっ！ / 是！` | short-reply punctuation OCR | short affirmative delivery can be corrupted into ellipsis; restore `是！` when evidence is strong. |
| ~1:19:10 `在那边` vs `こっちだ / 在这边` | deictic OCR reversal | explicitly challenge `这/那`, direction and proximal/distal meaning across the full release. |
| 34:00 | source ownership leakage | `ちょ… ちょっと` must not leak into another speaker's pair. |
| 39:15–39:20 | continuation ownership + sequential split | keep each clause with the correct source fragment. |
| 48:03–48:11 | continuation ownership + sequential split | distinguish continuation prefix from final Take-copter clause. |
| 1:00:31 | narration + sequential split | preserve narration provenance and split coarse multi-clause presentation. |
| 1:04:05–1:04:29 | cascade reconciliation + layout | severe compression can signal over-assembly; restore source-fragment sequence. |
| `タイムパトロールだ 観念しろ` | partial source-event fake closure | a ref covering only the first fragment must leave the second unresolved. |
| `目が回る！` | meaningful short source falsely omitted | short independent speech is not automatically expendable. |
| repeated `ふ～ん / うん / あっ` | duplicate short-fragment matching | exact text alone must not bind source refs. |
| simultaneous `ドラえもん！` | simultaneous identical call | preserve independent source identities/final refs. |
| target seed without JP source | unsupported seed expansion | do not fabricate Japanese solely to preserve visual 1:1. |
| `露营舱` vs `露营胶囊` | anti-overedit / Canon boundary | do not normalize a valid unfrozen term from popularity. |
| `タイムふろしき -> 时光布` | pinned Canon enforcement | enforce a locked Mainland-modern value when that profile is active. |
| 09:10 / 25:54 / 51:37 / 1:00:41 | seed ellipsis inertia | semantic delivery outranks inherited seed ellipsis. |
| 17:14 | target accounting | narrative content must never silently disappear. |
| 30:34 | Canon gate | scan obsolete aliases across the whole release. |
| 33:20 | exclamatory question | `何だって！` may naturally require Chinese `？！`; do not mirror mechanically. |
| 37:08 | speaker cleanup + spoken fragment | speaker metadata removal must not delete adjacent speech. |
| 47:00–47:20 | redundant target expansion | fold only with explicit ledger reason. |
| 52:04 | parallel-speaker false merge | time overlap does not justify merging simultaneous speakers. |
| 58:23 / 1:27:28 | mismatch may be valid | punctuation/wording mismatch itself is a review signal, not auto-failure. |

When a failure matching one of these classes is found, scan the full release for the same class.

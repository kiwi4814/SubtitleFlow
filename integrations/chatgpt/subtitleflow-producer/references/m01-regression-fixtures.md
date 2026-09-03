# M01 regression fixtures — Doraemon: Nobita's Dinosaur

Use these as known failure classes, not as a substitute for full-title review. Keep only minimal/synthetic snippets in public repositories; the complete M01 Golden ASS may remain private.

| Time / sample | Failure class | Expected lesson |
|---|---|---|
| 01:33 | source fragment split | `これ 本物？` and `もちろんさ` must not be swallowed into one target line. |
| 02:50 | source notation leakage | `《...》` is delivery metadata in this source family; hide marker while preserving inner-voice/narration provenance. |
| 03:04–03:08 | cross-cue notation | narration/source-notation span crosses cue boundaries; per-line regex is insufficient. |
| 04:39–04:48 | literal quotation | Japanese quotation marks used for read/quoted text must not be stripped as generic metadata. |
| 06:49–06:59 | source over-assembly + layout | do not pull multiple continuation fragments into one `fscx67` line; re-audit fragment order/speaker ownership. |
| 24:12 | sequential presentation split | do not use `fscx83` or two-line JA; split the coarse source cue at the real clause boundary into two sequential one-line bilingual events and mark inferred sub-timing when no raw internal timestamp exists. |
| 34:00 | source ownership leakage | `ちょ… ちょっと` must not leak into the pair for `むちゃだよ そんな 定員オーバーだ 降りてくれ`, or vice versa. |
| 39:15–39:20 | continuation ownership + sequential split | keep each camping clause with the correct semantic fragment and project the long 39:15 cue as sequential one-line bilingual events, not `fscx77` or stacked JA. |
| 48:03–48:11 | continuation ownership + sequential split | distinguish the continuation prefix from the final Take-copter clause; project the 48:03 coarse cue as sequential one-line bilingual events before the 48:07 conclusion. |
| 1:00:31 | narration + sequential split | strip source delivery brackets from presentation, preserve narration provenance, and split the coarse two-clause narration into two sequential one-line bilingual events rather than `fscx78` or two-line JA. |
| 1:04:05–1:04:29 | cascade reconciliation + layout | `fscx59` is a symptom of over-assembly; restore source-fragment sequence and account every moved/folded target unit. |
| `タイムパトロールだ 観念しろ` | partial source-event fake closure | a final ref covering only `タイムパトロールだ` must leave `観念しろ` unresolved; any event-level ref is not full fragment coverage. |
| `目が回る！` | meaningful short source falsely omitted | a short independent spoken sentence is not automatically an expendable reaction; present it when it has valid narrative/presentation space. |
| repeated `ふ～ん / うん / あっ` | duplicate short-fragment matching | exact text must not bind source refs without temporal/order/speaker/adjacency evidence. |
| simultaneous `ドラえもん！` | simultaneous identical call | preserve two independent source identities/final refs when two source fragments/speakers call the same name. |
| target seed without JP source | unsupported seed expansion | do not fabricate `JA_AUX_RECONSTRUCTED` merely to preserve visible 1:1. Default Japanese-audio collector production to source-backed Japanese only. |
| `露营舱` vs `露营胶囊` | anti-overedit / Canon boundary | if `露营舱` is semantically valid and the term is not frozen in pinned Canon, Producer must not replace it merely because an external common translation exists; record a Canon gap if durable research is needed. |
| `タイムふろしき -> 时光布` | pinned Canon enforcement | for the Mainland-modern branch, enforce the pinned locked value `时光布` even when historical subtitles contain a genuine older alias such as `时光包巾`. |
| 09:10 | seed ellipsis inertia | seed `大雄...` must not override emphatic `のび太！`. |
| 17:14 | target accounting | target narrative content must never silently disappear. |
| 17:21 | deterministic layout | bilingual spacing must be release-profile driven. |
| 25:54 | seed ellipsis inertia | `よ～し！` requires speech-act review, not mechanical `... -> ……`. |
| 30:34 | Canon gate | obsolete Mainland alias must be caught across the entire release. |
| 33:20 | exclamatory question | `何だって！` can naturally require Chinese `？！`; do not mirror punctuation mechanically. |
| 37:08 | speaker cleanup + spoken fragment | `(一同)` is metadata, but `あっ？` is spoken and must not disappear silently; call punctuation must be re-evaluated. |
| 47:00–47:20 | redundant target expansion | target count is not narrative-integrity truth; fold only with explicit ledger reason. |
| 48:26 | semantic punctuation + translation | truncated/threatening seed must be checked against full Japanese semantics rather than preserving ellipsis blindly. |
| 51:37 | vocative/exclamation vs ellipsis | object call/name may be emphatic even if seed uses ellipsis. |
| 52:04 | parallel-speaker false merge | time overlap does not justify merging simultaneous speakers. |
| 58:23 | mismatch may be valid | source `が！` can be grammatically elliptical; Chinese may legitimately trail off. Require model context judgment. |
| 1:00:41 | seed punctuation + wording | `許してよ！` should not inherit an unsupported trailing ellipsis. |
| 1:15:22 | repeated call | repeated vocative should preserve emphatic calling delivery without seed-ellipsis inertia. |
| 1:20:05 | call/exclamation | `ドラえもん！` is a high-confidence call, not trailing hesitation. |
| 1:27:28 | anti-overcorrection fixture | `さようなら！` may still be rendered as emotional `再见……` if scene/context justifies it; mismatch is not auto-failure. |

When the user reports a failure matching one of these classes, scan the full release for the same class.

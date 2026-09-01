# Workflow

## Stage 0 — Project canon

Do once per series/franchise, then version it.

Research recurring character names, forms of address, gadgets, locations, organizations, terminology and historical/forbidden aliases. Stable rules live in `projects/<project>/canon/glossary.json`; title-only terms live under the title's `canon/`.

Rules are either deterministic (`auto_replace=true`, `context_sensitive=false`) or context-sensitive (`auto_replace=false`). Context-sensitive aliases are never mass replaced.

## Stage 1 — Intake

Import A/B/C/D with `subflow source add`. The engine copies each file under `source/`, records SHA-256 and makes it read-only on a best-effort basis. Hash verification is authoritative.

A is the video time-coordinate master; B is the Japanese-audio Chinese seed; C is Japanese source evidence; D is Taiwan-dub wording evidence.

## Stage 2 — Title research

OpenCode's `film-researcher` investigates the title before semantic editing. It must produce non-empty `research/context.md` and `research/sources.md` plus any title/project glossary proposals. `subflow research mark-complete` refuses to pass the gate without those evidence files.

## Stage 3 — Normalize

ASS/SSA/SRT become structured JSON. Timing, text, event type, style and protection status are preserved. Complex positioned/drawing/karaoke/effect events are marked protected and are not rewritten by the semantic pipeline.

## Stage 4 — Alignment and branch seeding

- TW: A↔D.
- JP: A↔B creates JP branch units; those units are then aligned against C to attach Japanese evidence.

Dynamic programming allows 1:N / N:1 / N:M groupings and estimates a global time offset. Low-confidence groups are flagged. Do not match by line number.

## Stage 5 — Deterministic normalization

TW can run OpenCC `t2s`, then approved project/title glossary replacements. JP applies approved glossary rules to B-derived Chinese text. Every deterministic change is recorded on the work unit.

## Stage 6 — Semantic analysis

AI reads scene-sized work units plus title context/canon. Default decision is **keep**.

Only clear errors become proposals: negation, omission, wrong subject/object, numbers, names, causality/modality, plot-critical terminology, or unmistakable transcript error. The AI writes proposal JSON; it does not edit `final_text`.

## Stage 7 — Human review

Import proposals into the durable queue. Each proposal is stale-safe: `original_text` must still equal current `final_text` both at import and approval time.

Approve/reject/custom decisions are persisted. Compile is blocked while pending review exists. Any approved/custom edit changes the workfile, making an older QA snapshot stale.

## Stage 8 — Compile

- TW emits `SF-ZH` ASS dialogue.
- JP emits separate `SF-ZH` and `SF-JA` events.
- If one Japanese source group maps to several JP units, its source row spans the combined interval instead of being duplicated.
- Protected A events are carried through unchanged.

Compile and semantic editing are separate: styling changes do not require retranslation.

## Stage 9 — Deterministic QA

`subflow qa` checks:

- source integrity;
- structural timing/text validity;
- pending review;
- missing Japanese evidence;
- forbidden terminology;
- low-confidence alignment warnings;
- static layout width/row screening;
- reparsing compiled ASS.

It also records a SHA-256 snapshot of durable release inputs (`work`, glossary, title config, review state and final ASS). If any of those change afterward, `subflow release` rejects the old QA as stale.

## Stage 10 — Independent semantic QA

A separate `qa-reviewer` prompt audits high-risk semantics and writes `qa/semantic-review.md`. Any new correction must return to the human-review queue. Only a non-empty report with no unresolved finding may be marked complete with `subflow semantic-qa mark-complete`.

## Stage 11 — Render and visual QA

`subflow render` uses actual video plus FFmpeg/libass and marks only `render_<branch>` as passed. Rendering a PNG does **not** equal visual approval.

A human or vision-capable reviewer inspects the real PNGs for clipping, collisions, safe area, font fallback, line count, readability, bilingual hierarchy and protected signs. Only then use `subflow visual-qa mark-complete ... <branch>`.

## Stage 12 — Release

`subflow release` re-verifies:

- current source hashes;
- zero pending human review;
- current QA input snapshot;
- required research evidence;
- independent semantic QA evidence;
- required visual evidence/stages.

It freezes ASS hashes, QA hash/input snapshot, canon version and review counts in `release/release-manifest.json` plus `SHA256SUMS`.

## Stage 13 — Remux

`mkvmerge` attaches approved ASS tracks to the existing MKV without transcoding video/audio. Remux is blocked until a frozen release manifest exists.

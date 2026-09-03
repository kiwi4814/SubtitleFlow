# OCR character-form master / projection policy

Use this policy whenever OCR/hard-sub cleanup produces Chinese subtitles and the source may be Traditional, Simplified, or mixed-script OCR.

## Core authority chain

The production order is mandatory:

`immutable OCR -> cleaned source-form master -> freeze master -> optional Simplified projection`

The **cleaned source-form master is the authoritative final wording artifact**. A Simplified subtitle is a character-form derivative of that frozen master, never an independently edited translation branch.

If the master changes for any semantic/OCR/punctuation/timing/layout reason, regenerate every character-form projection from the master. Never patch the Simplified derivative directly.

## Detect source form from retained dialogue

Determine character form from dialogue that survives OCR cleanup, not from credits, garbage, foreign-script hallucinations, or removed visual text.

- Traditional-dominant Taiwan OCR -> emit a Traditional source-form master plus a Simplified projection.
- Simplified source OCR -> emit only the Simplified source-form master; do not manufacture a redundant Traditional subtitle.
- Mixed OCR with meaningful Traditional content -> preserve source wording, normalize accidental script mixing toward the dominant source script, record the detection result, then decide projections from the normalized master.

Do not infer the source form from the filename alone.

## What may change in the source-form master

Allowed changes are only production corrections already justified by the OCR-clean workflow:

- remove confirmed non-dialogue credits/signs/noise/duplicate frame-state OCR;
- repair verified OCR glyph/word errors;
- repair punctuation/delivery when evidence establishes the speech act;
- reconcile timing, merge/split presentation, and collector layout;
- normalize accidental Simplified/Traditional character-form mixing to the dominant source script when the intended character form is clear.

Do **not** use the source-form pass to:

- paraphrase or smooth wording;
- translate from Japanese;
- replace genuine Taiwan-dub terminology with Mainland Canon;
- regionalize vocabulary merely because another Taiwan/Mainland wording is more common;
- apply phrase-level Simplified/Traditional conversion that changes lexicon.

The rule is: **repair errors and presentation; preserve source wording.**

## Traditional master normalization

A Taiwan Traditional master should be consistently Traditional in character form while preserving the original Taiwan-dub lexicon.

Prefer original OCR Traditional glyphs wherever the surviving wording is trustworthy. When OCR itself mixes obvious Simplified glyphs into an otherwise Traditional subtitle, correct those glyphs contextually.

Do not blindly run a whole-text `Hans->Hant` transform and accept every result. Ambiguous forms require context/source preservation. For example, mechanical conversion must not turn valid `干擾`, `沉不住氣`, `系統`, or source-authentic `宣布` into unrelated variants merely to maximize Traditional-codepoint counts.

Character-form repair is not authorization for Taiwan phrase localization.

## Simplified projection

When a Traditional master exists, generate Simplified Chinese only **after the master is frozen**.

The Simplified projection may perform character-form conversion only. It must preserve exactly:

- wording and word order;
- Taiwan-dub terminology;
- punctuation/delivery;
- segmentation and event count;
- timing;
- styles/effects/layout geometry;
- provenance identity.

Do not run Canon normalization, translation, punctuation editing, or independent semantic cleanup on the Simplified derivative.

For a Taiwan-dub branch, examples such as `時間包巾 -> 时间包巾`, `嗶之助 -> 哔之助`, and `兩光機器人 -> 两光机器人` are character-form projections, not terminology replacements.

Avoid phrase-level conversion modes that can regionalize vocabulary. The projection must change script, not dialect/lexicon.

## Hard projection gates

When both variants are emitted, require:

1. source-form master exists and is frozen first;
2. every Simplified event derives from the corresponding master event;
3. event count/timing/style/effects/geometry are identical between variants;
4. converting the master through the selected Hant->Hans transform reproduces the delivered Simplified ASS exactly;
5. no independent Simplified-only text edits exist;
6. ledgers expose `source_form_text`, `simplified_text`, projection transform, and hashes;
7. reports name the source-form master as authoritative and the Simplified file as derivative.

If any gate fails, the derivative is not release-ready.

## Output contract

Traditional-source example:

```text
subtitles/
  Mxx....zh-TW....ass   # authoritative cleaned source-form master
  Mxx....zh-CN....ass   # deterministic Simplified projection
reports/
  character-form-projection.json
```

Simplified-source example:

```text
subtitles/
  Mxx....zh-CN....ass   # authoritative cleaned source-form master
```

Do not create a `zh-TW` file merely to make the archive symmetrical when the source OCR was already Simplified.

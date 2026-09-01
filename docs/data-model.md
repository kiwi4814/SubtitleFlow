# Data model

## Source roles

`source/manifest.json` records immutable imports and SHA-256 values. Valid roles are A/B/C/D/S. A role is evidence, not a filename convention.

## Normalized subtitle

Each imported role becomes `normalized/<role>.json` with cues containing:

- original timing;
- raw and plain text;
- source Style/event type;
- protected flag and reason;
- raw ASS event when applicable.

The active style profile may additionally protect recognized special source styles during normalization.

## Branch workfile

Workfiles are semantic editing surfaces, never raw ASS replacements.

Common fields include:

- unit id;
- start/end timing;
- timing/source cue ids;
- raw_text;
- normalized_text;
- final_text;
- optional source_text and source evidence ids;
- alignment confidence;
- deterministic changes;
- flags.

Branches:

- `clean`: S-derived; optional C source evidence.
- `tw`: A timing + D wording.
- `jp`: A timing + B Chinese + C Japanese.

## Review candidates

AI proposals store branch, unit id, exact original text, proposed text, reason/type/severity/confidence/evidence and durable status. They cannot apply themselves.

## Style profile

Style is independent project data. `kiwi-collector-v1` defines generated dialogue Styles, layout thresholds, source-preservation policy, font roles and event-level overrides such as `\blur2`.

## Font report

`qa/fonts.json` contains:

- required families inferred from compiled ASS;
- resolution reasons (`style:<name>`, `inline-fn`, release file);
- resolved local attachment files;
- MIME type;
- attachment filename;
- SHA-256 and size;
- missing families.

No font binary is copied into persistent project data by font audit.

## Release manifest

`release/release-manifest.json` freezes active branches, workflow profile, style id, ASS hashes, QA snapshot, review counts and resolved font attachment hashes. Remux must verify this frozen state before creating an MKV.

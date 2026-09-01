# Data model

## Workspace, title, and series identities

- `project_id` is the SubtitleFlow local production workspace/collection identity.
- `title_id` is the work/title identity inside that project.
- `series_id` is the canonical/SRP content-series identity.

New titles write `series_id`, defaulting to `project_id`; `subflow title init PROJECT TITLE --series-id SERIES_ID` may set it explicitly. `subflow title set-series PROJECT TITLE SERIES_ID` updates an existing title. Older v0.4 title files without a `series_id` use `project_id` as their effective series identity.

A project may contain SRP snapshots for multiple series. Project-level import stores validated immutable knowledge without a series compatibility check. Bind and resolve use the title's effective `series_id` to enforce compatibility.

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

## Research Pack and Effective Knowledge

SRP imports are immutable project-level snapshots under `projects/<project>/research/packs/`; title activation is stored separately in `research/bindings.json`. Raw packs are never merged by an LLM. The registry preserves each pack's manifest `scope.series_id`, and title bindings record the compatible series identity.

For v0.4-native titles in `advisory` or `enforce`, the resolver generates `research/effective.json`, `research/snapshot.json`, `research/summary.md`, and branch context files. Effective knowledge contains `project_id`, `title_id`, `series_id`, resolved Terms, Decisions, Entities, Facts, Unresolved items, and any cross-pack conflicts for `clean`/`tw`/`jp`. It freezes the resolver version and separate semantic and provenance digests.

The resolver combines SRP scopes deterministically (title+branch > series+branch > title > series) and overlays existing local project/title canon at the same scope. SRP Sources/Evidence are provenance, not subtitle text.

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

`release/release-manifest.json` freezes `project_id`, `title_id`, and effective `series_id` alongside active branches, workflow profile, style id, ASS hashes, QA snapshot, review counts, resolved font attachment hashes, and compact research mode/binding/digest evidence when SRP is active. Remux must verify this frozen state before creating an MKV.

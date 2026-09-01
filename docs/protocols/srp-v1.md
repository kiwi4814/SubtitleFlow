# Subtitle Research Pack v1.0 — Normative Specification

**Protocol identifier:** `SRP/1.0`  
**Storage:** UTF-8 JSON + JSONL  
**Primary goal:** exchange subtitle semantic/canon knowledge between any producer and an offline consumer such as SubtitleFlow.

> Normative words **MUST**, **MUST NOT**, **SHOULD**, **MAY** are used in their RFC-style sense.

## 1. Architectural boundary

SRP is optional. A subtitle workflow MUST be able to run without SRP unless that specific project explicitly enables an enforcing research policy.

SRP is producer-agnostic. A pack MAY be produced by a human, a local model, a web research model, scripts, a team database, or any combination. A consumer MUST NOT require access to the producer or the Internet in order to import a pack.

SRP contains semantic knowledge and editorial canon. It does **not** define ASS layout, fonts, timing, alignment, OCR, ASR, media tracks, model providers, or API credentials.

## 2. Standard files

Only `manifest.json` is required.

```text
research-pack/
├── manifest.json       REQUIRED
├── entities.jsonl      OPTIONAL
├── facts.jsonl         OPTIONAL
├── terms.jsonl         OPTIONAL
├── decisions.jsonl     OPTIONAL
├── sources.jsonl       OPTIONAL
├── evidence.jsonl      OPTIONAL
├── unresolved.jsonl    OPTIONAL
└── README.md           OPTIONAL / non-authoritative
```

Other files MAY exist but are non-authoritative to SRP/1.0 consumers.

All JSONL files MUST use UTF-8 and one JSON object per non-empty line. Blank JSONL lines are invalid in SRP/1.0. Record order has no semantic meaning.

## 3. Manifest

Required fields:

- `format`: MUST equal `subtitle-research-pack`.
- `schema_version`: MUST equal `1.0`.
- `pack_id`: stable ASCII slug.
- `pack_version`: SemVer-like version string.
- `scope.series_id`: series identifier.

`manifest.scope` expresses the maximum intended application scope of the pack:

```json
{"series_id":"doraemon"}
```

```json
{"series_id":"doraemon","title_id":"steel-troops-1986"}
```

```json
{"series_id":"doraemon","branch_id":"tw-dub-zh-cn"}
```

```json
{"series_id":"doraemon","title_id":"steel-troops-1986","branch_id":"tw-dub-zh-cn"}
```

Pack-scope containment is normative:

- a **series pack** MAY contain series/title/series-branch/title-branch records for that series;
- a **title pack** MAY contain title/title-branch records for that exact title, but MUST NOT introduce series or series-branch records;
- a **series-branch pack** MAY contain that series-branch and title-branch records for the same branch across titles in the series;
- a **title-branch pack** MAY contain only records for that exact title and branch.

This prevents a title-only research import from silently escalating into global series canon.

## 4. Record scope

Scoped records use an explicit `level`:

```json
{"level":"series","series_id":"doraemon"}
```

```json
{"level":"title","series_id":"doraemon","title_id":"steel-troops-1986"}
```

```json
{"level":"series_branch","series_id":"doraemon","branch_id":"tw-dub-zh-cn"}
```

```json
{"level":"branch","series_id":"doraemon","title_id":"steel-troops-1986","branch_id":"tw-dub-zh-cn"}
```

SRP scope precedence is permanently defined as:

```text
branch (title + branch)
> series_branch
> title
> series
```

A consumer MUST NOT ask an LLM to decide this precedence dynamically. A consumer MAY layer explicit local/human overrides on top, but that overlay must itself be deterministic and auditable.

## 5. Global record IDs and semantic keys

Every JSONL record has an `id`. IDs MUST be globally unique inside one pack.

Terms and Decisions additionally have a stable semantic `key`.

Examples:

```text
id  = term:anywhere-door:series
key = gadget.anywhere-door
```

```text
id  = decision:tw-dub-wording
key = policy.tw-dub-wording
```

`id` identifies a record instance. `key` identifies the semantic rule that can be overridden at a narrower scope.

**SRP/1.0 refinement:** `Decision.key` is mandatory. Without it, deterministic Series → Title → Branch policy override is impossible.

## 6. Entity

Entity answers: **what thing/person/place/concept is this?**

Core types:

`character | gadget | location | organization | species | event | work | concept | other`

Entity aliases are identity data, not automatic replacement rules.

## 7. Fact

Fact answers: **what background fact has been established or recorded?**

Facts are context only. A consumer MUST NOT automatically rewrite subtitle text merely because a Fact exists.

`status` is required:

`accepted | provisional | deprecated`

`confidence` is optional:

`high | medium | low`

Evidence is optional.

## 8. Term

Term answers: **for a source form/concept, what target-language form is canonical or preferred in this scope?**

Required fields include:

- `id`
- `key`
- `scope`
- `source.language`
- `source.forms[]`
- `target.language`
- `target.value`
- `enforcement`
- `status`

Target variant semantics:

- `target.value`: canonical output form.
- `accepted_aliases`: permitted alternatives; they are not canon violations.
- `deprecated`: historical/undesired forms; consumers SHOULD surface or normalize them according to local editing policy.
- `forbidden`: forms that MUST be flagged under enforcing policy.

The canonical `target.value` MUST NOT also appear in any alias category. `accepted_aliases`, `deprecated`, and `forbidden` MUST be pairwise disjoint.

`source.forms` are evidence/detection forms. SRP does not imply blind string replacement. Auto-replacement policy belongs to the consumer.

## 9. Decision

Decision answers: **what editorial rule should guide translation/localization behavior?**

Kinds:

`translation | naming | register | honorific | annotation | cultural | branch_policy | continuity | other`

A Decision requires a semantic `key` so narrower-scope policies can override broader ones deterministically.

`applies_to` MAY further filter a decision by:

- `branch_ids`
- `entity_ids`
- `term_keys`
- `languages`

The scope precedence is evaluated only among applicable accepted decisions.

## 10. Enforcement

Three values are normative:

### `locked`

The active rule MUST NOT be silently overridden by an AI/editorial automation. The model MAY challenge it, but disagreement must become review or an explicit local human override.

### `preferred`

The rule SHOULD be followed by default, but context-based divergence is allowed.

### `informational`

The record is context only and imposes no translation constraint.

Status/enforcement constraints:

- `provisional` MUST NOT be `locked`;
- `deprecated` MUST be `informational`.

## 11. Status

For Facts, Terms and Decisions:

- `accepted`: participates in effective current knowledge;
- `provisional`: context/research candidate, not locked canon;
- `deprecated`: historical record, not current effective canon.

Only `accepted` Terms and Decisions participate in deterministic rule resolution.

## 12. Source

A Source identifies the artifact from which evidence was derived.

Core source classes:

- `official_primary`
- `official_localized`
- `licensed_release`
- `first_party_reference`
- `reputable_reference`
- `community`
- `editorial`
- `user_supplied`
- `other`

Source locators support:

`url | local_file | audio | video | book | disc | subtitle | manual | other`

This is intentionally not Web-only. For example, the actual Taiwanese dub audio may be the strongest source for `zh-TW_dub` wording.

`authority_domain` is a string describing what question this source is authoritative for, rather than a universal numeric authority score.

## 13. Evidence

Evidence answers: **what does a Source specifically support, contradict, or contextualize?**

Stances:

`supports | contradicts | contextualizes`

Sources and Evidence are optional. However, when a record contains `evidence_ids`, every referenced Evidence record MUST exist in the same pack; and each Evidence `source_id` MUST resolve to a Source in the same pack.

SRP/1.0 intentionally uses self-contained provenance references. Cross-pack evidence references are outside v1.0 core.

## 14. Unresolved

Unresolved preserves honest ambiguity rather than forcing false certainty.

Severity:

`blocking | review | informational`

Interpretation is project-policy dependent:

- `blocking`: enforcing workflows SHOULD stop for a decision;
- `review`: surface to a reviewer;
- `informational`: retain as known uncertainty.

## 15. Language tags

Language identifiers MUST use BCP-47-style tags, e.g.:

`ja-JP`, `zh-CN`, `zh-TW`, `en-US`.

SRP MUST NOT use ad-hoc language IDs such as `chs`, `cht`, `jp`, or `cn` in language fields.

## 16. Structural and semantic validation

A conforming Full validator performs two layers.

### Structural validation

Validate each object against the corresponding Draft 2020-12 JSON Schema.

### Pack semantic validation

At minimum:

1. record IDs are globally unique;
2. scoped records stay within manifest scope;
3. declared evidence/source/entity references are not dangling;
4. accepted Term uniqueness is `(key, exact scope, target.language)`;
5. accepted Decision uniqueness is `(key, exact scope)`;
6. target alias categories do not conflict;
7. provisional/deprecated enforcement constraints hold.

Warnings and policy checks may be added by consumers, but MUST NOT silently change these meanings.

## 17. Term resolution

Given `(key, series_id, title_id?, branch_id?, target_language)`:

1. discard records not `accepted`;
2. discard different series/key/target language;
3. if exact title+branch (`branch`) record exists, use it;
4. otherwise if exact series+branch (`series_branch`) record exists, use it;
5. otherwise if exact title record exists, use it;
6. otherwise use the series record;
7. otherwise return no SRP canon.

Multiple accepted records at the same exact resolution level are an invalid pack, not an LLM choice.

## 18. Decision resolution

Decision resolution follows the same Branch > Series-Branch > Title > Series order using `Decision.key`, after applying `applies_to` filters relevant to the current context.

## 19. Human authority

A local explicit human override is the final editorial authority, but a consumer SHOULD require that the override be targeted to the effective scope rather than letting a generic series rule accidentally erase a narrower title/branch rule. If it overrides an active `locked` rule, the consumer SHOULD record an auditable event such as `USER_OVERRIDE_OF_LOCKED_CANON`.

## 20. Optional research modes for consumers

SRP itself does not define SubtitleFlow configuration, but a consumer is expected to support policy equivalents to:

- `off`: ignore SRP;
- `advisory`: use SRP as context/guidance without making Research completeness a release blocker;
- `enforce`: honor locked rules, blocking unresolved items, validation state and stale evidence as gates.

The default behavior of a general-purpose SubtitleFlow distribution SHOULD remain usable without SRP.

## 21. Pack digests

A producer is not required to calculate a pack SHA in `manifest.json`.

A consumer MAY calculate:

- a raw source-pack identity digest; and
- a semantic/effective snapshot digest for stale-gate propagation.

The effective snapshot digest SHOULD be computed by the consumer after parsing/validation, so harmless file formatting changes need not be treated as semantic canon changes.

## 22. Extensions

Core objects reject unknown root fields. Vendor/project-specific data belongs under:

```json
{"extensions":{"vendor.example":{"foo":"bar"}}}
```

Consumers MAY ignore unknown extension namespaces.

## 23. Explicitly outside SRP/1.0

- ASS style/layout/font configuration
- subtitle timing and alignment
- cue/workfile storage
- OCR/ASR
- vector databases/embeddings
- web crawler configuration
- LLM prompts/providers/API keys
- MKV track configuration
- automatic term replacement algorithms
- cross-pack dependency/reference protocol

These may be built around SRP without changing SRP's semantic contract.

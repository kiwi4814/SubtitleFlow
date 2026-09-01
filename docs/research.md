# Optional Research / SRP workflow — SubtitleFlow 0.4.1

SubtitleFlow 0.4.1 makes research an **optional knowledge layer**. The core subtitle workflow does not require web search, an AI research agent, or any Subtitle Research Pack (SRP). New titles default to `research.mode=off`.

## Identity boundaries

`project_id` identifies the local production workspace, `title_id` identifies a work inside that project, and `series_id` identifies the canonical/SRP content series. New titles default to `series_id = project_id`; older v0.4 title files without the field use that same fallback. Use `subflow title init PROJECT TITLE --series-id SERIES_ID` or `subflow title set-series PROJECT TITLE SERIES_ID` to set a distinct series.

## Research modes

| Mode | SRP required | Effective Knowledge | Terminology enforcement | Research Gate |
|---|---:|---:|---|---:|
| `off` | no | local canon only | existing local policy | no |
| `advisory` | no | bound SRP + local canon | SRP violations are warnings | no release-blocking Research Gate |
| `enforce` | yes | bound SRP + local canon | locked/forbidden violations can fail QA | explicit approval required |
| `legacy` | old v0.3 titles only | v0.3 Markdown research | old behavior | `context.md` + `sources.md` |

A web/high-end-model Research Skill is only one possible **producer**. Humans, local models, scripts, or other tools may produce the same SRP/1.0 files. Import, resolution, QA, release, and remux are offline.

## Pack lifecycle

Validate without importing:

```bash
subflow research validate-pack /path/to/research-pack.zip
```

Import into the project-level immutable research library. A project can store packs for multiple `series_id` values; import validates and stores the asset but does not decide which title may use it:

```bash
subflow research import doraemon /path/to/research-pack.zip --dry-run
subflow research import doraemon /path/to/research-pack.zip
subflow research list doraemon
```

Importing does **not** activate a pack for a title. Bind the exact imported identity separately; bind requires the pack manifest/registry `scope.series_id` to equal the title's effective `series_id`:

```bash
subflow research bind doraemon steel-troops-1986 doraemon-canon@1.0.0
```

If the same `pack_id@version` exists with more than one digest, the short reference is rejected as ambiguous; use the exact `#sha256:<digest>` reference reported by `research list`.

## Configure title policy

```bash
subflow research set-mode doraemon steel-troops-1986 advisory
subflow research map-branch doraemon steel-troops-1986 jp jp-zh-cn
subflow research map-branch doraemon steel-troops-1986 clean jp-zh-cn
subflow research map-branch doraemon steel-troops-1986 tw tw-dub-zh-cn
```

Resolve deterministic Effective Knowledge:

```bash
subflow research resolve doraemon steel-troops-1986
subflow research status doraemon steel-troops-1986
subflow research diff doraemon steel-troops-1986
```

Generated title-local derived files (including explicit project/title/series identity in Effective Knowledge and its snapshot):

```text
research/
├── bindings.json
├── effective.json
├── snapshot.json
├── summary.md
└── context/
    ├── clean.md
    ├── tw.md
    └── jp.md
```

Downstream models should consume these resolved branch contexts rather than merge raw packs themselves.

## Enforcing workflow

For a collection-grade title:

```bash
subflow research set-mode doraemon steel-troops-1986 enforce
subflow research resolve doraemon steel-troops-1986
subflow research diff doraemon steel-troops-1986
subflow research approve doraemon steel-troops-1986 --note "accepted canon for this release"
subflow prepare doraemon steel-troops-1986
```

`prepare` refuses to enter semantic editing in `enforce` mode until the current resolved snapshot has been approved. Approval is rejected when there is no bound pack, a blocking cross-pack conflict, or a blocking unresolved item.

## Resolution precedence

Within SRP:

```text
title + branch
> series + branch
> title
> series
```

Local/human canon wins at the same scope. SubtitleFlow intentionally uses **scope first, origin second** so a generic local series term cannot silently erase a legitimate title/branch exception. To override a narrower SRP rule, add an equally narrow local rule.

SRP `locked` is a semantic/editing constraint, **not** permission for blind `str.replace`. Deterministic auto-replacement remains controlled by the existing local `auto_replace` + `context_sensitive` policy.

## Stale evidence

Resolution freezes two independent digests:

- `effective_semantic_sha256`: terms, decisions, facts/entities/unresolved knowledge that can affect editing/QA.
- `provenance_sha256`: bound pack/source/evidence provenance.

If effective semantics change, deterministic QA and semantic QA become stale. Changing a title's `series_id` stales its resolved research/approval and dependent editing, QA, semantic, render, visual, release, and remux evidence without deleting source/work/review/release files. If only provenance changes, Research approval/release becomes stale without forcing unrelated visual QA to rerun. Final ASS changes continue to invalidate rendering through the normal compile/render dependency chain.

## Project storage

Imported packs live once at project scope and are immutable:

```text
projects/<project>/research/
├── registry.json
└── packs/<pack_id>/<version>/<digest>/
    ├── pack/
    └── import.json
```

A new version/digest is stored beside the old one. Existing title bindings never silently follow a newly imported pack, and a project may retain packs belonging to different series. Existing title bindings must still match their title's effective series when resolved.

## SRP protocol

See [`protocols/srp-v1.md`](protocols/srp-v1.md). SRP/1.0 supports `series`, `title`, `series_branch`, and title-specific `branch` scopes; Sources/Evidence are optional, and only `manifest.json` is required structurally.

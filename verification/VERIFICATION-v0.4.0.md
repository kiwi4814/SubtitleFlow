# SubtitleFlow v0.4.0 Verification Report

Date: 2026-09-01
Baseline: SubtitleFlow v0.3.0
Target: SubtitleFlow v0.4.0 with optional SRP/1.0 integration

## Release decision

**PASS for source release and wheel packaging.**

The v0.4.0 implementation keeps research optional for new titles, embeds the SRP/1.0 schemas and validator, adds immutable project-level pack import/binding/resolution, integrates Effective Knowledge into QA/gates/release, and preserves the v0.3 research gate as a compatibility path for legacy titles.

## SRP/1.0 protocol verification

The protocol draft was repaired before embedding to add the missing `series_branch` scope. The frozen resolution order is:

```text
branch (title + branch)
> series_branch
> title
> series
```

The standalone SRP conformance suite completed successfully:

```text
41 passed in 0.90s
```

The bundled schemas under `src/subtitleflow/srp/schemas/` are byte-identical to the repaired standalone SRP/1.0 schema set, and `docs/protocols/srp-v1.md` is byte-identical to the repaired protocol specification used by that suite.

## SubtitleFlow automated verification

Full repository test suite:

```text
85 passed in 2.14s
```

Coverage includes legacy v0.3 workflows plus v0.4 SRP import, ZIP hardening, immutable/digest-pinned bindings, `series_branch`, title+branch overrides, local-vs-SRP scope precedence, cross-pack canonical and alias-policy conflicts, advisory/enforce QA behavior, inactive-branch conflict isolation, Research approval, stale propagation, semantic/provenance digest separation, Release freezing, Remux gate compatibility, OpenCode permissions, and CLI integration.

Python bytecode compilation:

```text
python -m compileall -q src tools tests
PASS
```

## Wheel verification

Built artifact:

```text
dist/subtitleflow-0.4.0-py3-none-any.whl
SHA-256: 683b1484c3fa3d92b37ebf536dd12fdc3628d44e85ebbef96298de9b0da789fc
```

The wheel contains all 9 normative SRP schema files:

```text
common.schema.json
decision.schema.json
entity.schema.json
evidence.schema.json
fact.schema.json
manifest.schema.json
source.schema.json
term.schema.json
unresolved.schema.json
```

Installed-wheel smoke verification succeeded for:

```text
subflow --help
subflow --json doctor
subflow --json research validate-pack examples/srp/minimal-manual
```

The validation smoke accepted the minimal manual SRP containing only `manifest.json` + `terms.jsonl`, confirming that web research, Sources, and Evidence are not runtime requirements.

## Runtime capability observed in verification environment

Available:

- Python 3.13.5
- FFmpeg
- ffprobe
- FFmpeg/libass subtitles filter
- FontTools

Unavailable in this environment:

- `mkvmerge`
- `mkvextract`
- OpenCC CLI
- OpenCode CLI

Therefore no real MKVToolNix Remux was performed for this v0.4.0 verification run. Remux behavior, Research revalidation, and attachment/release safety are covered by automated tests, but an actual MKVToolNix production-host smoke test remains recommended before treating a specific host as fully commissioned.

## Tooling limitation

`ruff` is not installed in the execution environment and external package download is unavailable, so the configured Ruff lint job could not be executed here. `compileall` and the complete automated test suite passed. No font binaries are bundled in the repository release.

The installed-wheel smoke used the freshly created venv plus the host's already-installed `jsonschema` package because this environment has no package-network access. `pyproject.toml` declares `jsonschema>=4.25,<5`, so a normal online installation will resolve that runtime dependency conventionally.

## v0.4 P0 implementation checklist

1. **SRP/1.0 repair:** `series_branch` added and protocol revalidated — PASS.
2. **Bundled SRP core:** schemas, strict parser, validator, security guards — PASS.
3. **Immutable project Research Library:** import registry, digest identity, pinned bindings — PASS.
4. **Research modes:** `off | advisory | enforce`, new-title default `off`, v0.3 legacy shim — PASS.
5. **Effective Knowledge resolver:** scope-first/origin-second merge, branch mapping, conflict handling — PASS.
6. **Unified canon/terminology layer:** local `key`/`enforcement`, SRP rules integrated without enabling blind auto-replace — PASS.
7. **QA/Gate integration:** semantic/provenance digests, approval evidence, precise stale propagation — PASS.
8. **Release/Remux integration:** compact SRP identity frozen into release and revalidated on downstream operations — PASS.
9. **OpenCode orchestration/docs/tests:** producer-neutral optional Research flow and non-network assumption — PASS.

## Release boundary

v0.4.0 intentionally does **not** make a web Research Skill mandatory and does not include `research export-request` or chunk-level retrieval as core requirements. Those remain compatible follow-up work on top of the now-stable SRP consumer contract.

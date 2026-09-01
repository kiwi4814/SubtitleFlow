---
description: Verify local registry fonts and audit fonts referenced by compiled ASS files
agent: subtitle-orchestrator
---

First run `subflow fonts verify` to report whether the repository-local registered font assets are complete and byte/name-table correct. Then, for project `$1` title `$2`, run `subflow fonts audit $1 $2` and report requested/canonical families, canonical attachment names, local files, MIME metadata, SHA-256 records, and missing/mismatched families.

The repository bundles the pre-verified default fonts in `fonts/local/`. `subflow fonts install SOURCE` remains available when the user wants to re-import or update local font assets.

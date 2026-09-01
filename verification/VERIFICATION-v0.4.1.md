# SubtitleFlow v0.4.1 Verification Report

Date: 2026-09-01
Target: SubtitleFlow v0.4.1 release hardening for project/series identity provenance

## Release decision

**PASS for the v0.4.1 functional and wheel verification gates, with repository-wide Ruff debt explicitly recorded below.** The full Ruff commands are not reported as passing.

This verification did not modify the Doraemon M01 title, restore Research, or run `prepare`, subtitle editing, release, or Remux.

## SubtitleFlow preflight

The required preflight was run against `doraemon/m01`:

```text
project_id: doraemon
title_id: m01
series_id: doraemon
research: {"mode": "off", "branch_map": {}, "bindings": []}
```

`subflow research status doraemon m01` reported `mode: off`, no bindings, and no snapshot.
`subflow source verify doraemon m01` passed:

```text
C 85fdda9a63cd0b34b76f3e20ac4e3aa43fa57f4a7d6690985a6358f68efb3e96
S d0b568fa45f7ca608ac0f2e39a6ce931fe30de417767662cdb30e632f46fa9e8
```

## Automated verification

The following checks were actually executed and passed:

| Check | Command | Result |
|---|---|---|
| Focused regression tests | `.venv/bin/python -m pytest -q tests/test_series_identity.py tests/test_srp_v040.py` | **25 passed** |
| Full test suite | `.venv/bin/python -m pytest -rA` | **96 passed in 5.20s** |
| Bytecode compilation | `.venv/bin/python -m compileall -q src tools tests` | **PASS** |
| Diff whitespace | `git diff --check` | **PASS** |
| Targeted Ruff lint | `.venv/bin/python -m ruff check` on the four changed Python files | **PASS** |
| Targeted Ruff format | `.venv/bin/python -m ruff format --check` on the four changed Python files | **PASS** |

The targeted Python files were:

```text
src/subtitleflow/__init__.py
src/subtitleflow/release.py
src/subtitleflow/srp/__init__.py
tests/test_series_identity.py
```

## Repository-wide Ruff status

These commands were executed but are **not PASS**:

```text
.venv/bin/python -m ruff check .           -> 75 errors
.venv/bin/python -m ruff format --check .  -> 33 files would be reformatted
```

The failures are pre-existing repository debt outside the v0.4.1 change set. No error was reported for the four targeted changed Python files, and no mass-format cleanup was performed. Reported rule families include `UP035`, `UP037`, `SIM105`, `SIM114`, `SIM117`, `RUF001`, `RUF005`, `RUF043`, `RUF046`, `RUF059`, `I001`, `F841`, and `SIM118`.

Files reported by `ruff check .`:

```text
src/subtitleflow/alignment.py
src/subtitleflow/compile.py
src/subtitleflow/fonts.py
src/subtitleflow/formats/ass.py
src/subtitleflow/gates.py
src/subtitleflow/glossary.py
src/subtitleflow/io.py
src/subtitleflow/media.py
src/subtitleflow/models.py
src/subtitleflow/qa.py
src/subtitleflow/remux.py
src/subtitleflow/review.py
src/subtitleflow/srp/archive.py
src/subtitleflow/state.py
src/subtitleflow/timecode.py
src/subtitleflow/util.py
src/subtitleflow/workfile.py
src/subtitleflow/workflow.py
src/subtitleflow/workspace.py
tests/conftest.py
tests/test_ass.py
tests/test_cli_integration.py
tests/test_compile_qa.py
tests/test_gates.py
tests/test_media.py
tests/test_opencode_assets.py
tests/test_python_compat.py
tests/test_release_gates.py
tests/test_remux.py
tests/test_review.py
tests/test_srp_v040.py
tests/test_state_invalidation.py
tests/test_v020_workflows.py
tests/test_v030_fonts.py
tests/test_workspace.py
tools/verify_release.py
```

Files reported by `ruff format --check .`:

```text
src/subtitleflow/alignment.py
src/subtitleflow/cli.py
src/subtitleflow/compile.py
src/subtitleflow/fonts.py
src/subtitleflow/formats/ass.py
src/subtitleflow/formats/srt.py
src/subtitleflow/gates.py
src/subtitleflow/qa.py
src/subtitleflow/remux.py
src/subtitleflow/review.py
src/subtitleflow/srp/archive.py
src/subtitleflow/srp/context.py
src/subtitleflow/srp/registry.py
src/subtitleflow/srp/resolver.py
src/subtitleflow/srp/validate.py
src/subtitleflow/state.py
src/subtitleflow/style.py
src/subtitleflow/workfile.py
src/subtitleflow/workspace.py
tests/conftest.py
tests/test_ass.py
tests/test_cli_integration.py
tests/test_gates.py
tests/test_media.py
tests/test_packaging_metadata.py
tests/test_release_gates.py
tests/test_remux.py
tests/test_review.py
tests/test_srp_v040.py
tests/test_v020_workflows.py
tests/test_v030_fonts.py
tests/test_workspace.py
tools/verify_release.py
```

## Wheel verification

The wheel was built with the repository toolchain:

```bash
uv build --wheel --out-dir dist --clear
```

Artifact:

```text
dist/subtitleflow-0.4.1-py3-none-any.whl
SHA-256: 24c0b951878df6335cf935d20b5a48d6bf1bfc1645c75377fe076b6b0aa8ecd0
```

The wheel metadata reports `Version: 0.4.1`, contains all 9 bundled SRP schema files, and contains no `.ttf`, `.otf`, `.ttc`, or `.otc` payloads.

## Clean virtual-environment smoke

A fresh Python 3.11 virtual environment was created and the wheel was installed non-editably with offline package resolution. The imported package came from the fresh environment's `site-packages` and reported version `0.4.1`.

Passed smoke checks:

```text
subflow --help                                      PASS
subflow doctor                                      PASS (exit 0)
project init demo                                   PASS
title init demo movie --series-id another-series   PASS
```

The installed CLI reported:

```text
project_id: demo
title_id: movie
series_id: another-series
```

The clean environment had no MKVToolNix, OpenCC, FontTools, or libass filter capability; those optional tools were not required for this identity and packaging smoke.

## M01 recovery boundary

The project/series identity fix is verified, M01 remains unchanged, Research remains `off`, and its immutable C/S source hashes are intact. It is safe to resume the normal M01 Production Run from the identity-fix perspective. The normal SubtitleFlow gates still apply before any subtitle release: source verification, profile-derived preparation, semantic human review, compile, deterministic QA, font audit, independent semantic QA, render/visual approval, and release freeze.

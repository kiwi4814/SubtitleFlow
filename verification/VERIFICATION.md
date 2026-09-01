# SubtitleFlow v0.1.0 Verification Report

Verification date: 2026-08-31.

This report separates checks that actually ran from checks that could not run in the build environment.

## Release verdict

The generic deterministic core, OpenCode project assets, strict release gates, real FFmpeg/libass render path, legacy ASS stress path, and wheel installation path were exercised successfully.

Two optional production capabilities were **not** executable in this container:

- true MKVToolNix remux (`mkvmerge` is not installed);
- real Traditional→Simplified conversion with OpenCC (`opencc` / Python OpenCC is not installed).

The OpenCode executable is also not installed in this container, so OpenCode V2 assets were statically validated against the current official V2 configuration model rather than launched in a live OpenCode session.

## Automated test suite

Executed:

```text
PYTHONPATH=src pytest -q
```

Result: **32/32 passed**.

Coverage run:

```text
PYTHONPATH=src pytest -q --cov=subtitleflow --cov-report=json:verification/coverage.json
```

Result: **80% statement coverage** (1676 / 2101 statements).

High-risk deterministic modules are covered substantially above the package-wide number; external-binary execution branches account for much of the uncovered code.

## Syntax / compatibility gate

Executed:

```text
python -m compileall -q src tests tools
```

Result: **passed** on Python 3.13.5.

The test suite also parses all production Python files with Python 3.11 grammar via `ast.parse(..., feature_version=(3, 11))`; this passed. Actual Python 3.11 and 3.12 runtimes were not installed in this container, so runtime compatibility on those interpreters remains to be exercised in CI/local environments.

## Wheel packaging and clean installation

A packaging failure was found during verification: current setuptools rejected simultaneous PEP 639 `license = "MIT"` metadata and a legacy MIT license classifier. The legacy classifier was removed and a regression test was added.

After the fix, executed:

```text
python -m pip wheel . --no-build-isolation --no-deps -w dist
python -m venv /tmp/subflow-wheel-venv
/tmp/subflow-wheel-venv/bin/python -m pip install --no-index --no-deps dist/subtitleflow-0.1.0-py3-none-any.whl
/tmp/subflow-wheel-venv/bin/subflow --repo /mnt/data/SubtitleFlow --json doctor
/tmp/subflow-wheel-venv/bin/subflow --repo /mnt/data/SubtitleFlow --json status _visualtest demo
```

Result: **passed**.

The wheel is included under `dist/` in the project package.

## Strict synthetic end-to-end release

A copyright-free synthetic A/B/C/D fixture was run through the production-style pipeline:

1. immutable source import + SHA-256 verification;
2. normalize;
3. A↔D and A↔B↔C alignment;
4. deterministic glossary normalization;
5. TW and JP workfile generation;
6. compile;
7. deterministic QA;
8. independent semantic-QA evidence;
9. actual FFmpeg/libass rendering;
10. manual/vision inspection of generated PNGs;
11. explicit visual approval;
12. strict release freeze with all default quality gates enabled.

Result: **passed**.

Evidence retained in this directory:

- `visual-jp.png`
- `visual-tw.png`
- `synthetic-qa-summary.json`
- `synthetic-release-manifest.json`

The visual fixture intentionally includes a protected positioned sign. Inspection confirmed the sign survived and the generated TW / JP bilingual dialogue rendered without collision in the checked frames.

## Real legacy ASS stress tests

External Doraemon subtitle files were used only as local stress inputs; no commercial subtitle text is bundled with SubtitleFlow.

### Large legacy dialogue file

1980 legacy ASS:

- 824 events processed;
- full normalize → workfile → compile → QA → mechanical release path completed;
- source SHA-256 before and after was identical:
  `cc2ea32bb92ed59928fb06d150934b543af5436970d61a5c7e58a6c60101e08b`.

Result: **passed**.

### Complex ASS protection test

2008 complex ASS:

- protected events detected: 7,363;
- protected raw event lines retained after round-trip: 7,363 / 7,363.

Result: **passed**.

Machine-readable counts are in `verification-results.json`.

## Real FFmpeg/libass verification

Environment:

- FFmpeg: 7.1.5
- `ass` filter: available
- `subtitles` filter: available
- ffprobe: available

Actual PNG frames were generated from a synthetic MKV and inspected.

During this verification two rendering bugs were found and fixed:

1. FFmpeg could return success for an out-of-range timestamp without creating a PNG; SubtitleFlow now checks media duration and verifies every output file exists and is non-empty.
2. Input seeking reset timestamps in a way that could produce blank subtitle frames; rendering now preserves timestamps with `-copyts` and selects actual work-unit timestamps when layout candidates are unavailable.

## Release / state invalidation verification

The suite verifies that downstream state cannot remain falsely green after upstream changes. In particular:

- prepare changes invalidate compiled/QA/visual/release state;
- compile changes invalidate QA and later gates;
- QA reruns invalidate semantic and visual approvals;
- semantic proposal import or human decision invalidates compile and all downstream gates;
- rendering invalidates prior visual approval;
- source/canon changes invalidate normalization and downstream state;
- release compares a SHA-256 input snapshot and refuses stale QA;
- remux rechecks the frozen QA snapshot, QA report hash, release ASS hashes, and source hashes.

Result: **passed**.

## OpenCode V2 assets

Static tests verify:

- project `AGENTS.md` exists;
- four custom agents exist with expected primary/subagent modes;
- seven project skills exist under `.opencode/skills/*/SKILL.md`;
- subtitle slash-command templates exist under `.opencode/commands/subtitle/`;
- configuration uses the V2 `permissions` array and V2 action names;
- deprecated V1 field/action names (`permission`, `bash`, `task`) are not present in `opencode.jsonc`.

The OpenCode binary itself was unavailable, so live discovery/invocation is **not claimed**.

## MKVToolNix / Remux

The remux command builder and stale-release protections are unit tested. A dry-run command was also generated from the strict synthetic release using current option names such as `--default-track-flag` and BCP 47 `zh-CN` language tags.

`mkvmerge` was not installed in the build container, so a real MKV output was **not produced and is not claimed as verified**.

## OpenCC

SubtitleFlow deliberately refuses to pretend Traditional→Simplified conversion happened when OpenCC is unavailable. The synthetic tests disable T2S explicitly because their fixture text is already Simplified Chinese.

The OpenCC executable/library was not available in this container; real T2S execution remains a local-environment check.

## Defects found and fixed during verification

- FFmpeg success-without-output false positive.
- FFmpeg timestamp-reset blank-frame behavior.
- Preview fallback choosing timestamps with no active subtitle.
- Render success incorrectly conflated with visual approval.
- QA remaining apparently valid after work/review/canon changes.
- State page retaining stale downstream `passed` values.
- Remux accepting drift after a frozen release.
- Older `mkvmerge --default-track` spelling replaced with current `--default-track-flag`.
- Packaging failure caused by obsolete license classifier under current setuptools.
- ASS drawing protection generalized beyond `\\p1`–`\\p4` and protected zero-duration comment metadata made parse-safe.

## Environment snapshot

See `environment.json` for the exact detected tools used by this verification run.

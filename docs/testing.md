# Verification matrix

## Fast checks

```bash
python -m compileall -q src tests tools
PYTHONPATH=src pytest -q
```

The suite covers timecode parsing, ASS/SRT parsing, protected-event preservation, source mutation detection, 1:1/N:M alignment, global offset handling, glossary rules, stale-safe human review, compilation, deterministic QA, release-gate evidence, stale-QA rejection, OpenCode V2 asset shape, Python-3.11 syntax compatibility, layout logic and remux command construction.

## Synthetic CLI end-to-end

`tests/test_cli_integration.py` creates A/B/C/D fixtures, initializes a workspace, prepares both branches, compiles, runs QA and freezes a mechanical-test release with editorial/visual gates explicitly disabled.

A separate synthetic visual run uses a generated MKV and actual FFmpeg/libass. Research and semantic-QA evidence are written, three representative frames per branch are rendered, frames are visually inspected, visual gates are explicitly marked, then a production-style release manifest is frozen.

## Real-world legacy ASS stress test

`tools/verify_release.py` can take external ASS files without bundling them. Verification for this release used:

- a real 1980 legacy movie ASS with 824 events for full normalize/alignment/compile/QA/release mechanics;
- a complex 2008 ASS with 7,363 protected events to verify exact protected-line roundtrip retention.

Source SHA-256 is checked before and after the stress run.

## Packaging test

Build a wheel and install it into a fresh virtual environment, then execute the installed `subflow` entry point. This catches source-tree-only import mistakes.

## Remux test

The command builder is unit tested against current `mkvmerge` option ordering and current flag names. A true MKVToolNix remux is only claimed when the environment actually has `mkvmerge`; otherwise the limitation is recorded.

## Environment limitations

See `verification/VERIFICATION.md` for checks actually executed for the packaged release, including unavailable tools/runtimes. Proposed commands are never presented as passed checks.

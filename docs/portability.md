# Portability

The runtime engine uses only the Python standard library. Python 3.11+ is the declared target.

Optional components:

- OpenCC Python extra or CLI: required when TW Traditional→Simplified conversion is enabled.
- PyYAML: optional convenience dependency; generated configs are JSON.
- FFmpeg/ffprobe with libass filters: visual rendering and media probing.
- MKVToolNix: final MKV remux.
- OpenCode V2: recommended AI orchestration layer; the deterministic CLI does not depend on it.

The project stores no machine-specific media path by default. `title.json` can use environment variables such as `${MEDIA_ROOT}/movie.mkv`, expanded at runtime.

The packaged repository does not include third-party subtitle corpora, commercial video, font binaries, secrets, tokens, or user-specific absolute paths.

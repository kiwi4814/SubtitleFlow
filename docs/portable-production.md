# Portable Production Pipeline

SubtitleFlow 0.6 remains one engine with multiple runtime adapters. Do not maintain a long-lived Web fork.

## Architecture

```text
                         GitHub SubtitleFlow
        +----------------------+----------------------+
        |                      |                      |
        v                      v                      v
  SubtitleFlow Core       Canon / SRP          Evidence Library
        |                      |
        |            pinned immutable snapshot
        |                      |
        +----------+-----------+
                   v
             Portable Job
                   |
          deterministic prepare
                   |
             Semantic Packet
                   |
         +---------+---------+
         |                   |
         v                   v
   Local/OpenCode       ChatGPT Producer
         |                   |
         +---------+---------+
                   v
           Semantic Proposals
                   |
              Human Review
                   |
           Core QA / Release
```

`src/subtitleflow/` remains authoritative for deterministic engine behavior. Runtime adapters may differ in capabilities, but they must not redefine evidence authority, ASS preservation rules, Human Review, QA semantics, or release truthfulness.

## Runtime capability model

A runtime may advertise:

- FFmpeg availability;
- FFmpeg + libass availability;
- exact audited fonts availability;
- full video availability;
- MKVToolNix availability.

Missing capabilities become explicit deferred checks. They never become false passes.

Typical Web release:

```text
passed   source integrity
passed   semantic/terminology QA
passed   ASS structure QA
passed   synthetic libass render (when available)
deferred full-video timing QA
deferred scene-occlusion review
deferred MKV remux verification
```

A local runtime can later consume the same release/evidence and complete the deferred media checks.

## User-facing abstraction

Internal roles S/A/B/C/D remain valid engine concepts, but are not part of normal user interaction.

The producer accepts natural-language intents such as:

- Japanese audio + Simplified Chinese;
- Taiwan dub + Simplified Chinese;
- Japanese/Simplified-Chinese bilingual;
- polish an existing aligned subtitle.

The runtime adapter classifies uploaded sources internally and records the inferred mapping in the Portable Job.

## Canon Research boundary

`subtitle-canon-research` and `subtitleflow-producer` are complementary:

1. Canon Research authors durable series/title knowledge and evidence-backed terminology.
2. A validated SRP/Canon snapshot is stored in GitHub.
3. A production job pins the exact snapshot path/ref instead of silently following “latest”.
4. Portable prepare imports the snapshot immutably, verifies series compatibility, maps the release branch, resolves Effective Knowledge, and passes the Research Gate before semantic editing.
5. Producer consumes the resulting Semantic Packet for the concrete subtitle production.
6. Producer records newly discovered durable terminology gaps in `canon-gaps.jsonl`.
7. Canon Research can later resolve those gaps and publish a new pack version.

Producer must not silently create permanent Canon rules while producing one subtitle.

## Portable contracts

- `contracts/subtitle-job.schema.json` describes runtime-neutral production intent, inputs, and optional pinned repository research snapshot.
- `contracts/release-bundle.schema.json` describes runtime-neutral outputs and truthful QA statuses.

These contracts are intentionally user-language-first. Internal evidence roles may appear as inferred provenance but are not required from the human caller.

## Portable job runner

`python -m subtitleflow.jobs` materializes a classified Portable Job through the existing deterministic engine:

```text
Portable Job
  -> project/title workspace
  -> immutable source import + SHA manifest
  -> pinned SRP validate/import/bind/resolve/approve (when requested)
  -> normalization
  -> active-branch prepare/alignment
  -> durable state
  -> next-safe-action planner
```

When `requirements.use_repository_evidence=true`, `repository.research_pack_path` is required after the adapter has selected a compatible immutable SRP snapshot. The runner does not guess a moving “latest” pack. Series compatibility is exact, and ambiguous branch selection fails closed.

It intentionally stops at the planner after deterministic prepare. Semantic AI, Human Review, QA, rendering, release, and Remux remain owned by their existing contracts/gates. Runtime adapters must not invent parallel stage transitions.

## Semantic Packet

`python -m subtitleflow.semantic_packet` exports the stable read-only input for one AI semantic editing pass:

```text
Prepared Workfile
+ source-language evidence references
+ alignment confidence / N:M provenance
+ editorial policy
+ pinned Effective Research branch
+ source/workfile/research digests
        |
        v
Semantic Packet
        |
        v
ChatGPT / OpenCode semantic pass
        |
        v
material-change proposals only
        |
        v
existing proposal importer -> Human Review
```

The packet does not mutate the workfile, create review candidates, or approve edits. It carries a deterministic `packet_input_sha256` so proposals can be tied to the exact source/workfile/research snapshot. Every AI change still enters the existing Human Review gate.

## Real M01 example

The repository contains a reproducible job:

```text
examples/jobs/doraemon-m01.jp-audio-zh-cn.json
```

Run it from a SubtitleFlow checkout with:

```bash
uv run python -m subtitleflow.jobs \
  examples/jobs/doraemon-m01.jp-audio-zh-cn.json \
  --workspace /tmp/subtitleflow-m01 \
  --source-root .
```

The job uses the real repository M01 evidence:

- WOWOW-aligned Simplified-Chinese ASS as the editable/timing target;
- WOWOW Japanese ASS as source-language semantic evidence;
- `Doraemon-Theatrical-SRP-v1.0.1` pinned as the Canon/SRP snapshot;
- series identity `doraemon-theatrical` while the workspace project remains `doraemon`;
- internal `clean` branch mapped to SRP branch `jp-audio-zh-cn-modern`.

The Japanese source is a TV-accessibility-style ASS. Positioned dialogue is protected from editing but remains semantic evidence through normalized plain text. Non-verbal accessibility captions and Rubi/furigana reading annotations remain preserved source events but are excluded from semantic-language alignment.

Current real-evidence regression baseline:

```text
Chinese target cues              824
Chinese target matched           824 / 824 = 100%
Japanese raw events              1610
Accessibility SFX                169
Rubi/furigana annotations        6
Japanese semantic evidence       1435
Japanese evidence matched        1361 / 1435 = 94.8432%
Unmatched target cues            0
Unmatched source evidence cues   74
Estimated global offset          0 ms
```

The remaining source-only cues are retained because sampling shows genuine short Japanese dialogue/interjections among them. Low-confidence N:M groups remain review signals rather than being suppressed to inflate metrics.

After preparing the workspace, export the semantic packet with:

```bash
uv run python -m subtitleflow.semantic_packet \
  doraemon m01 clean \
  --repo /tmp/subtitleflow-m01 \
  --output /tmp/m01-semantic-packet.json
```

`tools/run_m01_prepare_pilot.py` runs the same Portable Job through `prepare_portable_job()` in CI and validates the SRP Research Gate, M01 alignment baseline, planner transition to `semantic-edit`, and Semantic Packet contents.

## Planner

`python -m subtitleflow.pipeline PROJECT TITLE` prints the next safe action from durable state plus runtime capabilities and deferred checks.

The planner does not replace existing gates. It centralizes navigation over them so OpenCode, ChatGPT, a future web UI, and direct local callers do not each invent their own state machine.

## Web Skill source

The ChatGPT adapter source belongs under `integrations/chatgpt/subtitleflow-producer/`. Build/package automation should copy only the lightweight adapter and required core snapshot. Large evidence archives and font binaries stay outside the Skill package.

The Skill package must remain under the ChatGPT upload limit and must not become a second manually maintained implementation of SubtitleFlow Core.

## Migration strategy

1. Add contracts and planner without changing 0.5 CLI behavior.
2. Add evidence indexes for narrow GitHub retrieval.
3. Split editable cues from evidence-usable cues; protected ASS presentation must not erase semantic evidence.
4. Add a Portable Job runner around existing engine functions.
5. Bind an exact repository SRP before semantic editing when requested.
6. Export a stable Semantic Packet for model adapters.
7. Tie proposals to the packet/input fingerprint and feed them through existing Human Review.
8. Add deterministic Release Bundle packaging and runtime-specific rendering/remux completion.
9. Run M01, M26, and M28 production pilots before removing or simplifying old OpenCode entrypoints.

The existing `.opencode/` integration remains supported during this migration.

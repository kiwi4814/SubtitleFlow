# Portable Production Pipeline

SubtitleFlow 0.6 should remain one engine with multiple runtime adapters. Do not maintain a long-lived Web fork.

## Architecture

```text
                         GitHub SubtitleFlow
        +----------------------+----------------------+
        |                      |                      |
        v                      v                      v
  SubtitleFlow Core       Canon / SRP          Evidence Library
        |
   +----+-----------------------+
   |                            |
   v                            v
Local runtime              ChatGPT Web runtime
CLI / OpenCode             SubtitleFlow Producer Skill
   |                            |
   +-------------+--------------+
                 v
          Release Bundle Contract
```

`src/subtitleflow/` remains authoritative for deterministic engine behavior. Runtime adapters may differ in capabilities, but they must not redefine evidence authority, ASS preservation rules, QA semantics, or release truthfulness.

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

The adapter classifies uploaded sources internally and records the inferred mapping in provenance metadata.

## Canon Research boundary

`subtitle-canon-research` and `subtitleflow-producer` are complementary:

1. Canon Research authors durable series/title knowledge and evidence-backed terminology.
2. The validated pack is stored in GitHub.
3. Producer consumes that pack for concrete subtitle production.
4. Producer records unresolved durable terminology in `canon-gaps.jsonl`.
5. Canon Research can later resolve those gaps and publish a new pack version.

Producer must not silently create permanent Canon rules while producing one subtitle.

## Portable contracts

- `contracts/subtitle-job.schema.json` describes runtime-neutral production intent and inputs.
- `contracts/release-bundle.schema.json` describes runtime-neutral outputs and truthful QA statuses.

These contracts are intentionally user-language-first. Internal evidence roles may appear as inferred provenance but are not required from the caller.

## Planner

`python -m subtitleflow.pipeline PROJECT TITLE` prints the next safe action from durable state plus runtime capabilities and deferred checks.

The planner does not replace existing gates. It centralizes navigation over them so OpenCode, ChatGPT, a future web UI, and direct local callers do not each invent their own state machine.

## Web Skill source

The ChatGPT adapter source belongs under `integrations/chatgpt/subtitleflow-producer/`. Build/package automation should copy only the lightweight adapter and any required engine snapshot. Large evidence archives and font binaries stay outside the Skill package.

The Skill package must remain under the ChatGPT upload limit and must not become a second manually maintained implementation of SubtitleFlow Core.

## Migration strategy

1. Add contracts and planner without changing 0.5 CLI behavior.
2. Add evidence indexes for narrow GitHub retrieval.
3. Split editable cues from evidence-usable cues; protected ASS presentation must not erase semantic evidence.
4. Add a portable job runner around existing engine functions.
5. Add deterministic Release Bundle packaging.
6. Wire the ChatGPT Skill to the same contracts.
7. Run M01, M26, and M28 production pilots before removing or simplifying old OpenCode entrypoints.

The existing `.opencode/` integration remains supported during this migration.

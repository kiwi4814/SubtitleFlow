---
description: Inspect, import, bind, resolve, or approve optional SRP research knowledge
agent: subtitle-orchestrator
---

For project `$1` title `$2`, begin with `subflow research status $1 $2`.

Research is optional and producer-neutral. Never assume web access or require `film-researcher`.

- `mode=off`: explain that SRP is disabled; do not create a Research Gate unless the user explicitly enables advisory/enforce.
- `mode=advisory`: if packs are bound, run `subflow research resolve $1 $2` and expose the generated branch context to downstream editors. If no pack is bound, continue normally.
- `mode=enforce`: require at least one valid bound SRP, run resolve, inspect conflicts/blocking unresolved items, and STOP for human resolution when blocked. Only after the user accepts the resolved knowledge run `subflow research approve $1 $2`.

If the user supplies an SRP directory/ZIP, validate it first with `subflow research validate-pack`, import it with `subflow research import`, then bind the exact immutable pack reference. Importing does not activate a pack by itself.

If the user explicitly asks for local research, `film-researcher` may create research notes or SRP-compatible staging data. A web/high-end-model Research Skill is a separate optional producer and is never required by SubtitleFlow core.

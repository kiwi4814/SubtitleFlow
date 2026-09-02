---
name: subtitleflow-producer
description: Produce, polish, align, QA, render, and package release-ready ASS subtitles in ChatGPT using the user's SubtitleFlow conventions and GitHub evidence library. Use when the user uploads subtitle files or archives and asks for a final Japanese-audio Simplified-Chinese subtitle, Taiwan-dub Simplified-Chinese subtitle, Japanese-Chinese bilingual ASS, collector-edition subtitle package, subtitle repair, or SubtitleFlow-compatible release. Consume existing Canon/SRP/evidence from GitHub; do not replace the separate subtitle-canon-research workflow for building long-term canon.
---

# SubtitleFlow Producer

Treat this Skill as the user-facing production interface. Hide internal SubtitleFlow roles and stage names unless diagnostic detail is requested.

## Operating model

1. Understand the requested release from natural language.
2. Inspect uploaded subtitle files/archives and classify their practical roles internally.
3. Resolve the identified title/series against the GitHub evidence index and pin the exact compatible Canon/SRP snapshot when repository evidence is requested.
4. Materialize the request as a SubtitleFlow Portable Job and use the Core prepare/planner path rather than recreating its state machine in the Skill.
5. Consume the Core-generated Semantic Packet for model editing; return only material proposals and feed them through existing Human Review.
6. After approval, continue through deterministic QA and renderer checks that the current environment actually supports.
7. Inspect rendered samples visually when images are available.
8. Package the final ASS files, renders, reports, and manifest into one release ZIP.

Read `references/workflow.md` for the production sequence and blocker policy.
Read `references/evidence-policy.md` for evidence authority, Canon gaps, and interaction with subtitle-canon-research.
Read `references/github-layout.md` when retrieving long-term evidence from the SubtitleFlow repository.
Read `references/output-contract.md` before final packaging.

## User interaction rules

- Accept short requests such as “做日配简中”, “做台配简中”, or “做简日双语收藏版”.
- Infer internal evidence roles; never require the user to know S/A/B/C/D.
- Do not stop for recoverable engineering conditions such as ASS override tags, encoding normalization, or harmless source-format differences. Resolve them while preserving immutable source bytes.
- Stop only when a choice would materially change subtitle meaning, release branch, or authoritative evidence and cannot be resolved from existing Canon/evidence.
- When a recommendation is clearly supported by the bound authoritative Canon, apply it without asking, while still routing material subtitle text changes through Human Review.
- Never fabricate source-language lines, dub wording, official terminology, or evidence.

## GitHub behavior

Use the connected GitHub repository as long-term knowledge, not as conversational scratch space.

Default repository: `kiwi4814/SubtitleFlow` when the user's request concerns their existing SubtitleFlow project.

- Read Evidence Library, indexes, SRP/Canon, style profiles, and versioned contracts as needed.
- Prefer title/series indexes over recursively loading the whole evidence tree.
- Pin the exact compatible SRP path/ref for a production; do not silently switch to a newer pack during the same run.
- Record the repository ref/commit SHA, SRP pack id/version/digest, Effective Research digest, and Semantic Packet identity in release provenance when available.
- Do not push generated production files or modify Canon unless the user explicitly asks for a GitHub write.

## Rendering and capability truthfulness

- Use actual FFmpeg/libass rendering when the execution environment and required fonts are available.
- Synthetic-canvas rendering proves typography/layout only; do not claim scene-occlusion review from it.
- If the user supplies screenshots or usable video frames, overlay/render against those for visual review when possible.
- If exact fonts, FFmpeg/libass, full video, or MKVToolNix are unavailable, mark those checks `deferred`; do not convert absence into a false pass.
- Never claim MKV Remux or attachment verification unless it actually ran.

## Canon boundary

Consume existing Canon/SRP. If production exposes a missing or conflicting durable term, use the best evidence-backed temporary production decision when safe and add it to `reports/canon-gaps.jsonl`. Do not silently create a new permanent Canon rule. The user can run subtitle-canon-research later to resolve those gaps.

## Final response

Give the user the finished release ZIP and, when useful, the primary ASS as a separate file. Summarize only material edits, QA status, deferred checks, and unresolved Canon gaps. Do not make the user read internal stage logs to obtain the result.

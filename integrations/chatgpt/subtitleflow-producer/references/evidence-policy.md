# Evidence and Canon policy

`subtitle-canon-research` authors durable knowledge. `subtitleflow-producer` consumes durable knowledge for a concrete Web production.

Preferred lifecycle:

1. Produce/version Canon/SRP separately when a series needs long-term terminology research.
2. Store validated knowledge/evidence in GitHub.
3. During a Web production, selectively resolve the exact compatible title/series/branch snapshot and pin its path/ref/digest when available.
4. Use the pinned knowledge as evidence; do not silently follow a moving `latest` during the same production.
5. Record newly discovered durable gaps in `reports/canon-gaps.jsonl`; do not silently rewrite permanent Canon from one production.

Keep provenance, trust, editing policy, and Canon separate. `official` does not automatically mean semantically correct for every branch. Taiwan-dub wording and Japanese-audio Chinese translation are distinct intents.

For Japanese-audio Chinese, source-language semantics is the semantic authority; the existing Chinese subtitle remains a translation seed. For Taiwan-dub Chinese whose goal is exact spoken fidelity, authority is ordered: clear same-cut Taiwan-dub audio first; reliable same-dub transcript or directly readable original hard-sub next; corroborated OCR after that. Japanese and Japanese-audio Chinese are challenge/context evidence, not Taiwan-dub wording authority. Dubbing may legitimately adapt the Japanese for performance, lip-sync, rhythm, humor, characterization, or localization.

## Canon boundary

Producer consumes Canon; Producer does not create Canon.

- pinned `locked` / authoritative preferred values for the active release profile: enforce them;
- accepted aliases: follow the bound scope/policy rather than treating every alias as globally equivalent;
- unresolved or absent long-tail term: keep an already semantically valid target unless there is a material line-level error, record a `canon_gap`, and route durable normalization to `subtitle-canon-research`;
- external evidence that another translation is common does not authorize Producer to replace a valid unfrozen term.

A temporary production choice is not a permanent Canon update. Record its context, observed variants, temporary choice, confidence, evidence identifiers, reason, and `needs_canon_research: true` when the issue should return to long-term research.

## Primary source challenge

Treat the pinned primary Japanese source as high-confidence semantic authority, not an unchallengeable absolute truth. Use independent challenge evidence only when a case is disputed/high-risk or the primary source itself appears suspect. Do not make ordinary production research every line online.

For Taiwan-dub speech-exact work, Japanese is never the wording authority for the dub. A Japanese/Taiwan-dub mismatch may represent legitimate dubbing adaptation rather than an OCR defect.

When challenged, compare provenance/version/context and semantic fit; do not use simple majority voting across subtitle files.

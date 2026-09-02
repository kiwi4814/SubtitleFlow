# Evidence and Canon policy

`subtitle-canon-research` authors durable knowledge. `subtitleflow-producer` consumes durable knowledge during a concrete production.

Preferred lifecycle:

1. New series: run subtitle-canon-research.
2. Store validated SRP/Canon and evidence in GitHub.
3. Run subtitleflow-producer for individual movies/episodes.
4. Producer records newly discovered durable gaps in `reports/canon-gaps.jsonl`.
5. Periodically feed those gaps back into subtitle-canon-research and publish a new Canon/SRP version.

Keep provenance, trust, editing policy, and Canon as separate concepts. “Official” does not automatically mean semantically correct for every release branch. Taiwan-dub wording and Japanese-audio Chinese translation are distinct intents.

When a durable term is absent or conflicting, record a JSONL item containing the source term, context, observed variants, temporary production choice, confidence, evidence identifiers, reason, and `needs_canon_research: true`.

A temporary production choice is not a permanent Canon update.

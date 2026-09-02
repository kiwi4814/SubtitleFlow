# Evidence and Canon policy

`subtitle-canon-research` authors durable knowledge. `subtitleflow-producer` consumes durable knowledge during a concrete production.

Preferred lifecycle:

1. Run subtitle-canon-research for a new series or material Canon revision.
2. Store the validated SRP/Canon snapshot and source evidence in GitHub.
3. For a concrete production, identify the exact compatible snapshot and pin its repository path/ref in the Portable Job.
4. Let SubtitleFlow validate series identity, import the snapshot immutably, map the requested release branch, bind the exact pack digest, resolve Effective Knowledge, and pass the Research Gate.
5. Consume the resulting Semantic Packet during AI editing; do not reread an unpinned “latest” Canon midway through the same semantic pass.
6. Submit only material proposals to the existing Human Review gate.
7. Record newly discovered durable gaps in `reports/canon-gaps.jsonl`.
8. Periodically feed those gaps back into subtitle-canon-research and publish a new Canon/SRP version.

Keep provenance, trust, editing policy, and Canon as separate concepts. “Official” does not automatically mean semantically correct for every release branch. Taiwan-dub wording and Japanese-audio Chinese translation are distinct intents.

Never relax a `series_id` mismatch merely to make a pack bind. For example, a general workspace project may be `doraemon` while the theatrical Canon series identity is `doraemon-theatrical`; preserve that distinction.

A production may temporarily resolve a missing term only when existing evidence is sufficient for that concrete line. Record a JSONL gap containing the source term, context, observed variants, temporary choice, confidence, evidence identifiers, reason, and `needs_canon_research: true`.

A temporary production choice is not a permanent Canon update. A Semantic Packet is also not Canon: it is a reproducible snapshot of workfile + evidence + editorial policy + Effective Research for one editing pass.

# Research policy

Research is optional in SubtitleFlow 0.4. The core workflow must remain usable with `research.mode=off`. When research is used, SRP/1.0 is the structured offline interchange format; the producer may be a human, local model, web/high-end model, script, or other tool.

For evidence-backed packs, preferred source order depends on the question rather than one global score:

1. official publisher/studio/original-language material for source canon;
2. licensed localized releases for regional official naming;
3. actual dub audio/transcript for what a dub version literally says;
4. first-party reference books/databases;
5. reputable reference sources;
6. community material for discovery, gaps, historical fan translations, or disputed usage.

Record what each source supports. Separate current official naming from historical dub/fansub naming. A historical alias can be useful evidence without being accepted as release canon. Evidence/Sources are optional in SRP, but any claimed `evidence_ids` must resolve correctly.

Never promote a title-only finding to series-wide canon merely because a model recommends it. Use explicit scope (`series`, `title`, `series_branch`, `branch`) and human review. See [`research.md`](research.md) and [`protocols/srp-v1.md`](protocols/srp-v1.md).

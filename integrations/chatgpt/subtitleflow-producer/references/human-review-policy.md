# OCR human-review policy

Use this policy for OCR/hard-sub cleanup whenever a small number of cases cannot be resolved safely without the user checking the actual dub audio/video.

## Purpose

`human-review.md` is an exception queue, not a QA dump. Its job is to reduce a full-film audit to the few moments where human listening materially improves exact subtitle-to-dub fidelity.

For OCR cleanup, emit `reports/human-review.md` even when the queue is empty. If empty, keep it short and state that no manual confirmation is recommended.

## Taiwan-dub wording authority

When the release goal is subtitles that match the Taiwan dub as spoken, use this wording authority order unless the user explicitly requests literal hard-sub transcription instead:

1. clear actual Taiwan-dub audio for the same cut;
2. reliable same-dub transcript or directly readable original hard-sub text;
3. high-confidence OCR reading corroborated by adjacent/repeated hard-sub frames;
4. nearby Taiwan-dub OCR context;
5. Japanese source and Japanese-audio Chinese as semantic/challenge evidence only;
6. model inference.

Dub scripts may adapt, shorten, expand, localize, or otherwise differ from the Japanese line for performance, lip-sync, rhythm, humor, characterization, or localization. A Japanese mismatch never automatically authorizes rewriting a credible Taiwan-dub line.

If clear dub audio conflicts with the hard-sub wording and the user's goal is exact spoken fidelity, follow the audio and record a `dub_audio_override` change. Do not preserve a subtitle-editor wording that the actor did not actually say merely because it appeared in the source hard-sub.

## Confirmed vs ambiguous dub divergence

Do not send every Japanese/Taiwan-dub mismatch to the user.

- `confirmed_dub_divergence`: readable/repeated dub-source evidence is coherent and the line can reasonably be accepted as a real localization change. Preserve it and do not create a human-review item solely because Japanese differs.
- `ambiguous_dub_divergence`: the difference is material and the available evidence cannot distinguish a genuine dub rewrite from OCR corruption, omission, wrong binding, or an inaccurate hard-sub transcription. This is a valid human-review candidate.

A divergence becomes more review-worthy when it changes polarity, direction/deixis, quantity, entity/name, causal meaning, plot fact, command/question/assertion, or other speech-act content.

## Review-budget rule

Human review is an exception path.

Default target per feature film:

- 3-8 total actionable items;
- fewer is better when evidence supports automatic closure;
- more than 10 requires a second filtering pass before delivery;
- exceed 10 only when the source is genuinely poor, and explain why the review budget could not be met.

Do not offload uncertainty to the user merely because the model can imagine alternatives.

## Include an item only when

At least one of these is true and the case is materially useful to confirm:

- issue confidence is high but exact repair confidence is not high enough for an automatic change;
- multiple plausible OCR recoveries remain and actual dub audio would choose among them;
- a material `ambiguous_dub_divergence` remains;
- a short reply, particle, name, direction, negation, number, or other high-information word materially changes what was spoken;
- a readable hard-sub phrase may differ from actual dub audio and exact spoken fidelity matters;
- a timing boundary cannot be trusted without hearing the dub and the ambiguity affects subtitle-to-speech matching.

## Do not include

- deterministic OCR errors that strong evidence already resolves safely;
- stylistic alternatives, smoother wording, or preferences about how a line 'should sound';
- pure layout/spacing issues that Producer can validate itself;
- low-impact punctuation or wording doubts with weak evidence of an actual error;
- clear, coherent `confirmed_dub_divergence` supported by the dub hard-sub;
- every Japanese/dub mismatch by default;
- items whose only reason is that dub audio was unavailable, when the source-form wording itself is already high confidence and not materially challenged.

## Confidence model

Use two independent confidence dimensions plus impact:

- `issue_confidence`: confidence that the current source-form master is wrong or materially suspect;
- `repair_confidence`: confidence that Producer knows the exact spoken replacement without human listening;
- `impact`: `high`, `medium`, or `low` consequence if left wrong.

Prefer labels `very-high`, `high`, `medium`, `low`. An optional 0-100 heuristic score may be shown as a convenience, but state that it is a model heuristic, not a statistical probability.

The classic human-review case is `issue_confidence=high/very-high` plus `repair_confidence=low/medium`.

## Priority

- `MUST_CONFIRM`: likely material error or material ambiguous divergence where exact spoken wording cannot be recovered safely.
- `OPTIONAL_LISTEN`: low/medium-impact ambiguity worth checking only if the user is already near that scene.
- everything else stays out of the user-facing queue and remains in internal QA/ledger evidence if useful.

## Item format

Each actionable item should contain:

- stable ID such as `HR-001`;
- compact listen window, normally 3-6 seconds;
- current source-form master text;
- category, e.g. `ocr_recovery_ambiguous`, `ambiguous_dub_divergence`, `exact_dub_wording`, `short_reply_delivery`;
- why Producer is asking the user rather than auto-fixing;
- concise supporting/conflicting evidence;
- issue confidence, repair confidence, and impact;
- one neutral listening question;
- a terse reply pattern such as `HR-001: <heard wording>` or `HR-001: KEEP`.

Do not bias the user with aesthetic prompts such as 'which version sounds more forceful' or 'use the more natural line'. Ask what was actually spoken. Offer candidate readings only when they are grounded alternatives, and always allow `OTHER: ...`.

## Report structure

Recommended `human-review.md` structure:

1. one-line workload summary;
2. `MUST_CONFIRM` items;
3. `OPTIONAL_LISTEN` items;
4. concise 'not sent for review' note explaining that deterministic fixes, styling, and confirmed dub divergences were already closed automatically;
5. reply instructions.

Avoid repeating full version history or every fixed OCR error. Those belong in `change-report.md` / ledgers.

## After the user replies

Treat user listening results as primary Taiwan-dub evidence for the specified cue.

1. update the authoritative source-form master only;
2. record the HR decision and evidence status;
3. regenerate every character-form derivative from the master;
4. rerun semantic, accounting, punctuation, layout, projection, and reference gates;
5. scan the whole release for the same newly confirmed bug class when applicable;
6. issue a new RC/final package and close the resolved HR item.

Never patch only the Simplified derivative.

## Completion semantics

If `MUST_CONFIRM > 0`, do not claim the release is fully verified against Taiwan-dub speech. It may still be Golden for a narrower automated Web scope when explicitly stated, but the dub-audio-faithful release status remains `pending-human-review`.

An audio-faithful final requires all mandatory HR items resolved or explicitly waived by the user.

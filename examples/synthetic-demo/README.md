# Synthetic demo

All lines in this directory are invented and safe to use as tests.

## Single-subtitle workflow

```bash
subflow project init demo --name "Demo"
subflow title init demo single --name "Single" --profile single
subflow source add demo single S examples/synthetic-demo/S.ass
subflow prepare demo single
subflow compile demo single
subflow qa demo single
```

The plain `Note` event demonstrates Hybrid special-style preservation even without a complex ASS override tag.

## Full A/B/C/D workflow

```bash
subflow title init demo full --name "Full" --profile full
subflow source add demo full A examples/synthetic-demo/A.ass
subflow source add demo full B examples/synthetic-demo/B.ass
subflow source add demo full C examples/synthetic-demo/C.srt
subflow source add demo full D examples/synthetic-demo/D.ass
subflow prepare demo full --allow-no-opencc
```

The synthetic full fixture demonstrates multi-source branch construction without using commercial subtitle text.

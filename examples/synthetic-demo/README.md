# Synthetic demo

These are invented lines used only to exercise the workflow. They are not copied from a commercial subtitle.

Example:

```bash
subflow project init demo
subflow title init demo sample
subflow source add demo sample A examples/synthetic-demo/A.ass
subflow source add demo sample B examples/synthetic-demo/B.ass
subflow source add demo sample C examples/synthetic-demo/C.srt
subflow source add demo sample D examples/synthetic-demo/D.ass
```

Add deterministic names with `subflow canon add-term`, disable T2S for this already-Simplified fixture if OpenCC is not installed, then run `subflow prepare`.

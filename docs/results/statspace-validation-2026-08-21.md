# StatSpace benchmark validation — 2026-08-21

## Scope

The sports profile was run once per model on the same Apple Silicon 24 GiB host, sequentially,
with normal memory pressure. The validated contracts were `statspace-slate-v4`,
`statspace-explanations-v2`, and `statspace-ledger-v3` with
`statspace-ledger-partial-v3`. Raw JSONL and Markdown reports remain in the ignored
`benchmarks/results/` directory.

## Results

| Model alias | Sports profile | Slate | Explanations | Ledger |
|---|---:|---:|---:|---:|
| `qwen` | 9.38/10 | 98.2% | 100% | 100% |
| `gemma` | 6.72/10 | 60.0% | 0% | 100% |
| `gptoss-final` | 8.12/10 | 78.2% | 100% | 25.0% |

Artifacts:

- `20260821-140926-qwen-sports.{jsonl,md}`
- `20260821-140429-gemma-sports.{jsonl,md}`
- `20260821-140553-gptoss-final-sports.{jsonl,md}`

## Review notes

- Qwen and GPT-OSS returned all 11 slate decisions but treated the exact edge/expected-value
  boundary as `watchlist` instead of the required inclusive-threshold `recommended` status.
- Qwen was otherwise perfect across the new StatSpace metrics.
- Gemma classified all slate candidates correctly, but omitted the second superseded ID and the
  optional missing-injury issue. Its explanation response padded fields with repeated newlines and
  exhausted the output budget before completing valid JSON, so strict schema scoring correctly
  assigned zero.
- GPT-OSS preserved all explanation statuses, gates, and missing-information fields. Its ledger had
  correct settlement counts but incorrect net units, settled stake, and ROI.

These are single observations, not reliability estimates. Repeat trials are required before using
small score differences as stable routing evidence.

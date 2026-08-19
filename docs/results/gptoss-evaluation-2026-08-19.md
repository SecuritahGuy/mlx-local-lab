# GPT-OSS evaluation snapshot — 2026-08-19

## Configuration

- Model: `mlx-community/gpt-oss-20b-MXFP4-Q8`
- Runtime: `mlx-lm`
- Recommended alias: `gptoss-final`
- Host: Apple M5, 24 GiB, macOS 26.6.1
- Capability boundary: text-only; no `/v1/responses` endpoint

`gptoss-final` forces the Harmony final channel and injects JSON schemas because the installed
`mlx-lm` server does not parse GPT-OSS Harmony channels or enforce `response_format`. API
compatibility is tracked separately from model quality.

## Observed results

| Suite | Result | Key limitation |
|---|---|---|
| Core 2K | 21/21 requests; 90.1% mean quality | reasoning cases remained partially scored |
| Executable coding | 100% apply, targeted tests, full tests, and no-change safety | 60% minimal-change score |
| Realistic RAG 2K | 100.0% quality and grounding | peak system use approximately 17.5 GiB |
| Realistic RAG 8K | 86.5% quality; 96.0% grounding | mid-context quality dip |
| Realistic RAG 16K | 95.8% quality; 83.1% grounding | grounding weakened; 6.3 tok/s median |
| Practical full | 7.3/10 overall | hallucination resistance 2.5/10 |

The latest executable validation returned the correct no-change structure—`change_required: false`
and an empty change list—and passed all fixture tests without regressions. Hard and security cases
still replaced more lines than the configured minimality thresholds allow.

The practical profile scored agentic 10.0/10, repository 9.67/10, sports 8.8/10, speed 10.0/10,
and memory efficiency 2.85/10. It made unsupported claims in the absent-quarterback and
absent-firmware cases. Vision and camera rows were capability-skipped and not scored as model
failures.

## Prompt tuning after this snapshot

- `executable-v2` retains the explicit no-change invariant and adds a strict instruction to preserve
  formatting, comments, names, and structure while prohibiting style-only additions and refactors.
- `hallucination-v2` defines absent fields as unknown, prohibits inference from general knowledge,
  and requires the `INSUFFICIENT_EVIDENCE` marker for unsupported answers.
- Future JSONL rows carry `prompt_version` for these suites. The results above predate that field, so
  reruns measure the effect of the new contracts and are not silent continuations of the baseline.

## Next validation

```bash
make model MODEL=gptoss-final
make bench-executable MODEL=gptoss-final
make bench-hallucination MODEL=gptoss-final
make stop
```

Run representative cases three times before treating prompt-sensitive changes as stable.

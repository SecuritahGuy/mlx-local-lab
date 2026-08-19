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
| Executable coding v2 | 100% apply, tests, minimality, and no-change safety | adversarial analysis term score was partial |
| Realistic RAG 2K | 100.0% quality and grounding | peak system use approximately 17.5 GiB |
| Realistic RAG 8K | 86.5% quality; 96.0% grounding | mid-context quality dip |
| Realistic RAG 16K | 95.8% quality; 83.1% grounding | grounding weakened; 6.3 tok/s median |
| Practical full, pre-v2 | 7.3/10 overall | hallucination resistance 2.5/10 |
| Hallucination v2 | 3/3 supported text cases abstained correctly | image case was incorrectly attempted before skip fix |

The `executable-v2` validation returned the correct no-change structure—`change_required: false`
and an empty change list—and passed all fixture tests without regressions. All five cases met their
configured minimality thresholds, improving the minimal-change score from 60% to 100%.

The practical profile scored agentic 10.0/10, repository 9.67/10, sports 8.8/10, speed 10.0/10,
and memory efficiency 2.85/10. It made unsupported claims in the absent-quarterback and
absent-firmware cases. Vision and camera rows were capability-skipped and not scored as model
failures.

## Versioned prompt validation

- `executable-v2` retained the explicit no-change invariant and added a strict instruction to
  preserve formatting, comments, names, and structure while prohibiting style-only additions and
  refactors. Patch application, targeted/full tests, minimality, and no-change safety were all 100%.
- `hallucination-v2` defines absent fields as unknown, prohibits inference from general knowledge,
  and requires the `INSUFFICIENT_EVIDENCE` marker for unsupported answers. GPT-OSS complied in all
  three supported text cases, improving supported-case abstention from 1/3 to 3/3.
- The first v2 hallucination report displayed 7.5/10 because it attempted the image-based easy case
  on a text-only model. The harness now capability-skips that case; a report-only rerun remains.
- The run increased swap from 0.40 GiB before model load to 2.38 GiB while memory pressure remained
  normal. Swap was still 2.37 GiB after shutdown, so future 24 GiB runs should continue sequentially.

## Next validation

```bash
make model MODEL=gptoss-final
make bench-hallucination MODEL=gptoss-final
make stop
```

Run representative cases three times before treating these prompt-sensitive improvements as stable.

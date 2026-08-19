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
| Hallucination v2 | 10.0/10; 3/3 supported text cases abstained correctly | image case capability-skipped |

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
  three supported text cases, improving supported-case abstention from 1/3 to 3/3 and the normalized
  category score from 2.5/10 to 10.0/10.
- The corrected report recorded zero failures, zero unsupported claims, and one capability-aware
  skip for the image-based easy case. Its displayed overall score was 6.56/10 because speed and
  system-wide memory efficiency remain included as separate categories.
- The first supported request had 2.822-second TTFT and 4.707 tok/s; the next two had
  0.378/0.362-second TTFT and 21.711/31.124 tok/s, consistent with a colder first inference.
- The run increased swap from 0.40 GiB before model load to 2.38 GiB while memory pressure remained
  normal. The final rerun began and ended at 2.33 GiB swap, so future 24 GiB runs should continue
  sequentially.

## Next validation

```bash
make model MODEL=gptoss-final
# Repeat representative executable and hallucination cases three times.
make stop
```

Run representative cases three times before treating these prompt-sensitive improvements as stable.

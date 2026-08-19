# GPT-OSS benchmark readiness

`gptoss` is registered as the text-only `mlx-community/gpt-oss-20b-MXFP4-Q8` model served by
`mlx-lm`. The model is downloaded and has completed core, executable, realistic-RAG, and practical
full runs. Use `gptoss-final` for structured requests; it uses the same cached weights with a
final-channel Harmony template and explicit JSON-schema injection.

## Capability behavior

| Workload | Harness behavior |
|---|---|
| Vision, camera, mixed JSON/text/image | Capability-skipped because `multimodal: false`; not scored as failure |
| Executable coding and no-change safety | Runs through disposable fixture repositories |
| Cybersecurity, reasoning, instruction following, RAG, structured output | Runs through the core benchmark suite |
| Sports, hallucination, REST text workflows, repository reasoning | Runs through the practical full profile |
| Realistic 2K/8K/16K RAG | Runs through the natural-corpus benchmark |
| Responses API | Recorded as unavailable (`responses_api: false`), not as model-quality failure |

The chat-completions benchmark path is independent of `/v1/responses`. A missing
Responses endpoint affects direct Codex-provider compatibility only; it must not
be interpreted as an intelligence result.

## Completed validation

On 2026-08-19, `gptoss-final` completed all 21 core requests with 90.1% mean deterministic quality.
The latest executable run applied 5/5 decisions, passed 5/5 targeted and full suites, produced no
regressions, and correctly avoided the adversarial no-change edit. Realistic RAG scored 100.0% at
2K, 86.5% at 8K, and 95.8% at 16K. The practical full profile scored 7.3/10 overall; its strongest
quality categories were agentic (10.0), repository (9.67), and sports (8.8), while hallucination
resistance was the primary weakness (2.5).

See [`docs/results/gptoss-evaluation-2026-08-19.md`](results/gptoss-evaluation-2026-08-19.md) for
the detailed snapshot and result provenance.

## Next-round commands

```bash
# Run from the local-mlx-lab repository root.
make model MODEL=gptoss-final
make health
make bench-executable MODEL=gptoss-final
make bench-hallucination MODEL=gptoss-final
make stop
```

These reruns validate the new `executable-v2` minimal-edit language and `hallucination-v2` evidence
contract. Do not compare their scores directly with unversioned rows without noting the prompt
change. Photographic, camera, and vision workloads remain capability-skipped for this text-only
model.

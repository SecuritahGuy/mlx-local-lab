# LOCAL MLX LAB — RELIABILITY AND EXECUTABLE CODING HANDOFF

> Historical handoff: the GPT-OSS readiness statements below describe the state before the
> 2026-08-19 GPT-OSS runs. See
> [`gptoss-evaluation-2026-08-19.md`](gptoss-evaluation-2026-08-19.md) for current results.

## System

- Apple M5, 24 GiB unified memory, macOS 26.6.1 (25G76), arm64.
- Python 3.12.10, uv 0.11.30, MLX 0.32.1, mlx-vlm 0.6.15, mlx-lm 0.31.3,
  OpenAI Python 3.3.0.
- Qwen: `mlx-community/Qwen3.5-9B-4bit`; Gemma:
  `mlx-community/gemma-4-12B-it-4bit`; localhost-only `mlx-vlm` serving.

## Changes made

- Added latest-three-trial reliability aggregation with raw trial values, latency/throughput
  distributions, schema success, quality-change flags, memory, and swap.
- Added `gemma-default` and `gemma-strict` profiles without output repair.
- Added five disposable executable-coding repositories and targeted/full pytest evaluation.
- Added natural 2K/8K/16K RAG corpora and grounding/citation/abstention evaluation.
- Added eight attributed photographic fixtures, deterministic labels, and a separate score.
- Added margin-based routing, GPT-OSS capability/readiness documentation, CLI/Make targets, and tests.

## Repeated-trial results

| Metric | Qwen | Gemma |
|---|---:|---:|
| TTFT mean / median / SD / range | 2.730 / 0.910 / 7.964 / 0.202–47.611 s | 4.020 / 0.910 / 9.483 / 0.341–46.307 s |
| Throughput mean / median / SD / range | 14.964 / 17.708 / 7.174 / 0.084–25.144 tok/s | 11.055 / 13.506 / 5.395 / 0.086–15.937 tok/s |
| Output tokens mean / range | 203.4 / 4–492 | 306.8 / 4–800 |
| Schema success where applicable | 15/15 (100%) | 6/15 (40%) |
| Peak system memory / swap | 16.80 / 0.40 GB | 16.50 / 0.40 GB |
| `coding/implement_function` quality | .750 / .750 / .750 | .750 / .750 / .750 |
| `reasoning/architecture_tradeoffs` | .667 / .667 / .667 | 1.000 / 1.000 / 1.000 |
| `repository/architecture-navigation` | 1.000 / 1.000 / 1.000 | .000 / .000 / .000 |
| Selected hallucination cases | 1.000 in all six observations | .000 in all six observations |
| Hard snow / adversarial sports | .750 / 1.000 in every trial | .000 / .000 in every trial |

None of the 13 selected cases changed quality across its three trials. Qwen's earlier
`implement_function` .75 is stable. Gemma repository quality failure is stable, while its TTFT is
warm-sensitive: architecture navigation fell from 13.066 s to 2.579/2.187 s. Both models' first
RAG observations had extreme cold-path latency, preserved in the ranges rather than discarded.

## Gemma template investigation

Gemma's template emits a thought-channel generation prefix; channel tokens 100/101 are not EOS.
The strict profile passes `enable_thinking=false` through `extra_body`, applies -100 bias to those
two channel tokens, and requests unfenced raw output. It does not strip markers or repair JSON.
Repeated channel markers disappeared, but benchmark quality did not improve: hallucination stayed
5.0/10, repository fell 8.0→7.0/10, and executable full-suite pass fell 80%→60%. Sports/API
abstention, architecture schema validity, hard executable output, and security correctness remained
failures. Strict serving cleans the symptom but does not materially improve Gemma.

## Executable coding results

| Metric | Qwen | Gemma | Winner |
|---|---:|---:|---|
| Patch apply rate | 100% | 100% | No meaningful difference |
| Targeted test pass rate | 100% | 80% | Qwen |
| Full-suite pass rate | 100% | 80% | Qwen |
| Regression rate | 0% | 0% | No meaningful difference |
| Minimal-change score | 80% | 80% | No meaningful difference |
| Appropriate no-change rate | 100% | 100% | No meaningful difference |

Easy, medium, hard, and adversarial/no-change outcomes matched. The models differed only on the
security redirect case: Qwen passed targeted/full tests but changed 21 lines and lost minimality;
Gemma changed two lines but still accepted the unsafe `/\\evil.example` form and failed both test
runs. Per-case runtime and prompt/output tokens are retained in raw JSONL.

## Realistic long-context results

| Context | Qwen TTFT / tok/s / quality / grounding / peak GB | Gemma TTFT / tok/s / quality / grounding / peak GB |
|---:|---:|---:|
| ~2K | 3.949 / 11.255 / 100% / 100% / 15.57 | 6.025 / 7.258 / 97.9% / 91.5% / 15.82 |
| ~8K | 11.226 / 10.843 / 99.8% / 99.3% / 16.84 | 18.825 / 6.078 / 87.0% / 97.9% / 16.34 |
| ~16K | 21.899 / 4.305 / 100% / 100% / 17.39 | 36.754 / 2.622 / 100% / 100% / 16.77 |

Qwen's natural-context latency advantage persists. The first natural 16K Qwen run raised macOS
swap from 0 to 0.40 GB; subsequent Qwen and Gemma runs did not increase it, and pressure stayed
normal. This supersedes the earlier zero-swap snapshot.

## Photographic camera results

| Score | Qwen | Gemma |
|---|---:|---:|
| Synthetic camera (three full runs) | 96.0% | 89.0% |
| Licensed photographic fixtures | 86.9% | 93.1% |

Gemma leads the real-photo set by 6.25 points; Qwen leads synthetic scenes by 7 points. Both were
perfect on night, vehicles, snow, and the ambiguous-object uncertainty case. The synthetic Qwen
camera lead therefore does not cleanly generalize to photographs. No model generated imagery.

## Updated routing recommendation

| Workload | Recommendation | Evidence |
|---|---|---|
| Default | Qwen | Wins most reliability-sensitive routes and is faster overall |
| Coding | Qwen | 100% versus 80% executable full-suite pass |
| Reasoning | Gemma | 100% versus 83.3% on repeated selected reasoning |
| Repository | Qwen | 100% versus 50% on repeated selected repository cases |
| Vision | Qwen | Existing mixed/diagram vision plus photographs; photographic-only leader is Gemma |
| Camera | No meaningful difference | 96/86.9 synthetic/photo Qwen versus 89/93.1 Gemma |
| RAG answer quality | No meaningful difference | 99.9% versus 95.0%; below five-point margin |
| Long-context performance | Qwen | Equal 16K quality, 21.899 s versus 36.754 s TTFT |
| Sports | Qwen | Adversarial case 3/3 valid/pass versus 0/3 |
| Hallucination-sensitive | Qwen | Selected abstention cases 6/6 versus 0/6 |

## GPT-OSS readiness

The harness is ready and GPT-OSS remains uncached. Text-only capability skips cover vision, camera,
and mixed image/text without quality penalties. Core, executable, realistic-RAG, and practical-full
profiles cover all requested text workloads. `responses_api: false` records API incompatibility,
not intelligence failure. Exact deferred commands:

```bash
# Run from the local-mlx-lab repository root.
make download MODEL=gptoss
make model MODEL=gptoss
make health
make bench MODEL=gptoss CONTEXT=2048
make bench-executable MODEL=gptoss
make bench-realistic-rag MODEL=gptoss
make bench-full MODEL=gptoss
make bench-photographic MODEL=gptoss
make stop
```

## Current final state

- Qwen running: no.
- Gemma running: no.
- Port 8080: closed.
- Swap: 0.40 GB; memory pressure: normal.
- Post-validation system memory: approximately 7.91 GB used / 12.92 GB available.
- Model caches and all raw benchmark outputs are preserved; GPT-OSS is not cached.

## Paste-ready summary

Local MLX reliability phase completed on Apple M5 / 24 GiB / macOS 26.6.1.
Qwen3.5-9B-4bit and Gemma 4 12B ran one at a time through mlx-vlm.
The representative subset has three preserved trials per model and case.
Qwen TTFT mean/median/SD was 2.730/0.910/7.964 s; Gemma was 4.020/0.910/9.483 s.
Qwen throughput mean/median/SD was 14.964/17.708/7.174 tok/s.
Gemma throughput mean/median/SD was 11.055/13.506/5.395 tok/s.
Applicable schema success was Qwen 15/15 (100%) and Gemma 6/15 (40%).
No selected case changed quality across its three trials.
Qwen implement_function stayed .75 in all trials, so the old outlier is stable.
Gemma architecture-navigation stayed 0, while TTFT improved 13.066→2.579/2.187 s warm.
Gemma channel markers were serving-controllable with enable_thinking=false and token bias.
Strict Gemma did not improve quality: hallucination 5/10, repository 7/10, executable 60%.
Executable patch apply was 100% for both models.
Targeted/full executable pass was Qwen 100%/100%, Gemma 80%/80%.
Both had 0% regression, 80% minimal-change, and 100% no-change safety.
Only security differed: Qwen passed but over-edited; Gemma's minimal patch failed the backslash case.
Natural 2K RAG quality was Qwen 100% and Gemma 97.9%.
Natural 8K RAG quality was Qwen 99.8% and Gemma 87.0%.
Natural 16K RAG quality was 100% for both.
At 16K, Qwen TTFT/tok-s was 21.899/4.305 versus Gemma 36.754/2.622.
Synthetic camera was Qwen 96.0% versus Gemma 89.0%.
Licensed photographic accuracy reversed: Qwen 86.9% versus Gemma 93.1%.
No local model generated images; all photographs have provenance and permissive/public licenses.
Routing: Qwen default/coding/repository/long-context/sports/hallucination-sensitive.
Routing: Gemma reasoning; photographic-only vision also favors Gemma.
Overall camera and RAG quality have no meaningful difference at a five-point margin.
GPT-OSS remains undownloaded and uncached; the harness capability-skips all image workloads.
Missing GPT-OSS Responses API is represented as an API limitation, not model failure.
The first natural 16K Qwen run raised swap to 0.40 GB; later runs did not increase it.
Final memory pressure is normal, Qwen and Gemma are stopped, and port 8080 is closed.

# Repeated-trial reliability

Each case retains up to its latest three valid, prompt-version-compatible trials. Standard deviation is sample standard deviation; incomplete coverage is reported as N/A.
Historical `hallucination/*` rows used the strict `hallucination-v2` evidence contract. New runs record natural and guardrailed tracks separately.

## Qwen (`qwen`)

- Coverage: 39/39 trials across 13/13 cases; 13/13 cases have three trials
- TTFT: mean 2.730s; median 0.910s; SD 7.964s; range 0.202–47.611s
- Throughput: mean 14.964 tok/s; median 17.708 tok/s; SD 7.174 tok/s; range 0.084–25.144 tok/s
- Output tokens: mean 203.4; median 123.0; SD 168.1; range 4.0–492.0
- Schema success where applicable: 15/15 (100.0%)
- Peak system memory: 16.80 GB; peak swap: 0.40 GB

| Case | Coverage | Quality trials | TTFT trials (s) | Throughput trials (tok/s) | Changed? |
|---|---:|---:|---:|---:|---:|
| coding/implement_function | 3/3 | 0.750 / 0.750 / 0.750 | 3.742 / 0.910 / 0.480 | 2.036 / 15.630 / 21.747 | no |
| coding/code_review | 3/3 | 0.667 / 0.667 / 0.667 | 2.339 / 0.300 / 0.205 | 2.092 / 15.948 / 21.224 | no |
| reasoning/architecture_tradeoffs | 3/3 | 0.667 / 0.667 / 0.667 | 0.202 / 0.304 / 0.308 | 24.258 / 15.912 / 17.909 | no |
| reasoning/incomplete_debugging | 3/3 | 1.000 / 1.000 / 1.000 | 0.202 / 0.297 / 0.231 | 25.144 / 15.907 / 22.892 | no |
| repository/architecture-navigation | 3/3 | 1.000 / 1.000 / 1.000 | 1.132 / 1.628 / 1.132 | 22.726 / 14.999 / 22.219 | no |
| repository/appropriate-no-change | 3/3 | 1.000 / 1.000 / 1.000 | 1.314 / 1.345 / 1.358 | 18.727 / 18.716 / 18.683 | no |
| hallucination/sports-absent-quarterback | 3/3 | 1.000 / 1.000 / 1.000 | 0.445 / 0.683 / 0.455 | 18.440 / 12.034 / 18.298 | no |
| hallucination/api-absent-firmware | 3/3 | 1.000 / 1.000 / 1.000 | 0.210 / 0.306 / 0.211 | 17.708 / 11.664 / 17.680 | no |
| camera/snow | 3/3 | 0.750 / 0.750 / 0.750 | 1.068 / 0.820 / 0.621 | 13.863 / 18.518 / 19.042 | no |
| camera/lookalike-object | 3/3 | 0.950 / 0.950 / 0.950 | 1.111 / 0.838 / 0.612 | 13.869 / 18.366 / 19.226 | no |
| sports/nfl-adversarial-noisy-upset | 3/3 | 1.000 / 1.000 / 1.000 | 2.025 / 1.091 / 1.211 | 14.162 / 19.525 / 19.270 | no |
| rag/direct_answer | 3/3 | 1.000 / 1.000 / 1.000 | 19.003 / 2.556 / 2.622 | 1.008 / 5.749 / 5.637 | no |
| rag/unanswerable | 3/3 | 1.000 / 1.000 / 1.000 | 47.611 / 3.056 / 2.493 | 0.084 / 1.203 / 1.494 | no |

## Gemma (`gemma`)

- Coverage: 39/39 trials across 13/13 cases; 13/13 cases have three trials
- TTFT: mean 4.020s; median 0.910s; SD 9.483s; range 0.341–46.307s
- Throughput: mean 11.055 tok/s; median 13.506 tok/s; SD 5.395 tok/s; range 0.086–15.937 tok/s
- Output tokens: mean 306.8; median 300.0; SD 249.1; range 4.0–800.0
- Schema success where applicable: 6/15 (40.0%)
- Peak system memory: 16.50 GB; peak swap: 0.40 GB

| Case | Coverage | Quality trials | TTFT trials (s) | Throughput trials (tok/s) | Changed? |
|---|---:|---:|---:|---:|---:|
| coding/implement_function | 3/3 | 0.750 / 0.750 / 0.750 | 0.835 / 0.971 / 0.610 | 14.442 / 11.238 / 14.039 | no |
| coding/code_review | 3/3 | 1.000 / 1.000 / 1.000 | 0.368 / 0.398 / 0.370 | 15.044 / 15.717 / 15.314 | no |
| reasoning/architecture_tradeoffs | 3/3 | 1.000 / 1.000 / 1.000 | 0.358 / 0.352 / 0.387 | 15.937 / 15.754 / 13.862 | no |
| reasoning/incomplete_debugging | 3/3 | 1.000 / 1.000 / 1.000 | 0.358 / 0.557 / 0.341 | 15.350 / 10.026 / 15.439 | no |
| repository/architecture-navigation | 3/3 | 0.000 / 0.000 / 0.000 | 13.066 / 2.579 / 2.187 | 2.765 / 13.506 / 13.930 | no |
| repository/appropriate-no-change | 3/3 | 1.000 / 1.000 / 1.000 | 12.597 / 2.358 / 2.301 | 1.378 / 11.534 / 10.588 | no |
| hallucination/sports-absent-quarterback | 3/3 | 0.000 / 0.000 / 0.000 | 0.914 / 1.459 / 1.005 | 15.075 / 9.604 / 13.328 | no |
| hallucination/api-absent-firmware | 3/3 | 0.000 / 0.000 / 0.000 | 0.570 / 0.897 / 0.639 | 15.852 / 10.027 / 13.467 | no |
| camera/snow | 3/3 | 0.000 / 0.000 / 0.000 | 0.817 / 0.910 / 0.837 | 15.558 / 14.631 / 15.373 | no |
| camera/lookalike-object | 3/3 | 1.000 / 1.000 / 1.000 | 0.819 / 0.826 / 0.813 | 14.825 / 14.635 / 14.571 | no |
| sports/nfl-adversarial-noisy-upset | 3/3 | 0.000 / 0.000 / 0.000 | 1.540 / 1.733 / 1.665 | 3.340 / 13.352 / 12.164 | no |
| rag/direct_answer | 3/3 | 1.000 / 1.000 / 1.000 | 38.323 / 3.998 / 4.024 | 0.497 / 3.498 / 3.461 | no |
| rag/unanswerable | 3/3 | 1.000 / 1.000 / 1.000 | 46.307 / 3.813 / 3.891 | 0.086 / 0.983 / 0.968 | no |

## GPT-OSS (`gptoss-final`)

- Coverage: 13/39 trials across 11/13 cases; 0/13 cases have three trials
- TTFT: mean 0.897s; median 0.672s; SD 0.702s; range 0.330–2.821s
- Throughput: mean 22.739 tok/s; median 21.711 tok/s; SD 12.034 tok/s; range 2.926–36.665 tok/s
- Output tokens: mean 158.3; median 42.0; SD 159.9; range 4.0–400.0
- Schema success where applicable: 3/3 (100.0%)
- Peak system memory: 18.49 GB; peak swap: 2.37 GB

| Case | Coverage | Quality trials | TTFT trials (s) | Throughput trials (tok/s) | Changed? |
|---|---:|---:|---:|---:|---:|
| coding/implement_function | 1/3 | 1.000 | 0.672 | 35.666 | no |
| coding/code_review | 1/3 | 1.000 | 0.330 | 36.665 | no |
| reasoning/architecture_tradeoffs | 1/3 | 1.000 | 0.457 | 30.923 | no |
| reasoning/incomplete_debugging | 1/3 | 0.500 | 0.384 | 28.995 | no |
| repository/architecture-navigation | 1/3 | 1.000 | 1.054 | 33.463 | no |
| repository/appropriate-no-change | 1/3 | 1.000 | 1.109 | 19.276 | no |
| hallucination/sports-absent-quarterback | 2/3 | 1.000 / 1.000 | 0.511 / 2.821 | 16.863 / 4.707 | no |
| hallucination/api-absent-firmware | 2/3 | 1.000 / 1.000 | 0.381 / 0.378 | 21.549 / 21.711 | no |
| camera/snow | 0/3 | N/A | N/A | N/A | N/A |
| camera/lookalike-object | 0/3 | N/A | N/A | N/A | N/A |
| sports/nfl-adversarial-noisy-upset | 1/3 | 1.000 | 0.739 | 35.316 | no |
| rag/direct_answer | 1/3 | 1.000 | 1.607 | 7.544 | no |
| rag/unanswerable | 1/3 | 1.000 | 1.216 | 2.926 | no |

## Deterministic routing

A five-percentage-point margin is required; executable full-suite pass rate drives coding. N/A means the required benchmark data is unavailable.

| Workload | Qwen | Gemma | GPT-OSS | Recommendation |
|---|---:|---:|---:|---|
| coding | 100.0% | 80.0% | 100.0% | No meaningful difference |
| reasoning | 83.3% | 100.0% | N/A | Gemma |
| repository | 100.0% | 50.0% | N/A | Qwen |
| multimodal | 93.4% | 84.1% | N/A | Qwen |
| vision | 93.4% | 84.1% | N/A | Qwen |
| camera | 91.4% | 91.1% | N/A | No meaningful difference |
| rag | 99.9% | 95.0% | 94.1% | No meaningful difference |
| sports | 100.0% | 0.0% | N/A | Qwen |
| hallucination | 100.0% | 0.0% | N/A | Qwen |
| long_context | 68.3% | 41.6% | 100.0% | GPT-OSS |
| default | 50.0% | 10.0% | N/A | Qwen |

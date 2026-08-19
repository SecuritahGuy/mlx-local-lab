# Repeated-trial reliability

Each case retains its latest three valid trials. Standard deviation is sample standard deviation.

## qwen

- TTFT: mean 2.730s; median 0.910s; SD 7.964s; range 0.202–47.611s
- Throughput: mean 14.964; median 17.708; SD 7.174; range 0.084–25.144 tok/s
- Output tokens: mean 203.4; range 4–492
- Schema success where applicable: 15/15 (100.0%)
- Peak system memory: 16.80 GB; peak swap: 0.40 GB

| Case | Quality trials | TTFT trials (s) | Throughput trials (tok/s) | Changed? |
|---|---:|---:|---:|---:|
| coding/implement_function | 0.750 / 0.750 / 0.750 | 3.742 / 0.910 / 0.480 | 2.036 / 15.630 / 21.747 | no |
| coding/code_review | 0.667 / 0.667 / 0.667 | 2.339 / 0.300 / 0.205 | 2.092 / 15.948 / 21.224 | no |
| reasoning/architecture_tradeoffs | 0.667 / 0.667 / 0.667 | 0.202 / 0.304 / 0.308 | 24.258 / 15.912 / 17.909 | no |
| reasoning/incomplete_debugging | 1.000 / 1.000 / 1.000 | 0.202 / 0.297 / 0.231 | 25.144 / 15.907 / 22.892 | no |
| repository/architecture-navigation | 1.000 / 1.000 / 1.000 | 1.132 / 1.628 / 1.132 | 22.726 / 14.999 / 22.219 | no |
| repository/appropriate-no-change | 1.000 / 1.000 / 1.000 | 1.314 / 1.345 / 1.358 | 18.727 / 18.716 / 18.683 | no |
| hallucination/sports-absent-quarterback | 1.000 / 1.000 / 1.000 | 0.445 / 0.683 / 0.455 | 18.440 / 12.034 / 18.298 | no |
| hallucination/api-absent-firmware | 1.000 / 1.000 / 1.000 | 0.210 / 0.306 / 0.211 | 17.708 / 11.664 / 17.680 | no |
| camera/snow | 0.750 / 0.750 / 0.750 | 1.068 / 0.820 / 0.621 | 13.863 / 18.518 / 19.042 | no |
| camera/lookalike-object | 0.950 / 0.950 / 0.950 | 1.111 / 0.838 / 0.612 | 13.869 / 18.366 / 19.226 | no |
| sports/nfl-adversarial-noisy-upset | 1.000 / 1.000 / 1.000 | 2.025 / 1.091 / 1.211 | 14.162 / 19.525 / 19.270 | no |
| rag/direct_answer | 1.000 / 1.000 / 1.000 | 19.003 / 2.556 / 2.622 | 1.008 / 5.749 / 5.637 | no |
| rag/unanswerable | 1.000 / 1.000 / 1.000 | 47.611 / 3.056 / 2.493 | 0.084 / 1.203 / 1.494 | no |

## gemma

- TTFT: mean 4.020s; median 0.910s; SD 9.483s; range 0.341–46.307s
- Throughput: mean 11.055; median 13.506; SD 5.395; range 0.086–15.937 tok/s
- Output tokens: mean 306.8; range 4–800
- Schema success where applicable: 6/15 (40.0%)
- Peak system memory: 16.50 GB; peak swap: 0.40 GB

| Case | Quality trials | TTFT trials (s) | Throughput trials (tok/s) | Changed? |
|---|---:|---:|---:|---:|
| coding/implement_function | 0.750 / 0.750 / 0.750 | 0.835 / 0.971 / 0.610 | 14.442 / 11.238 / 14.039 | no |
| coding/code_review | 1.000 / 1.000 / 1.000 | 0.368 / 0.398 / 0.370 | 15.044 / 15.717 / 15.314 | no |
| reasoning/architecture_tradeoffs | 1.000 / 1.000 / 1.000 | 0.358 / 0.352 / 0.387 | 15.937 / 15.754 / 13.862 | no |
| reasoning/incomplete_debugging | 1.000 / 1.000 / 1.000 | 0.358 / 0.557 / 0.341 | 15.350 / 10.026 / 15.439 | no |
| repository/architecture-navigation | 0.000 / 0.000 / 0.000 | 13.066 / 2.579 / 2.187 | 2.765 / 13.506 / 13.930 | no |
| repository/appropriate-no-change | 1.000 / 1.000 / 1.000 | 12.597 / 2.358 / 2.301 | 1.378 / 11.534 / 10.588 | no |
| hallucination/sports-absent-quarterback | 0.000 / 0.000 / 0.000 | 0.914 / 1.459 / 1.005 | 15.075 / 9.604 / 13.328 | no |
| hallucination/api-absent-firmware | 0.000 / 0.000 / 0.000 | 0.570 / 0.897 / 0.639 | 15.852 / 10.027 / 13.467 | no |
| camera/snow | 0.000 / 0.000 / 0.000 | 0.817 / 0.910 / 0.837 | 15.558 / 14.631 / 15.373 | no |
| camera/lookalike-object | 1.000 / 1.000 / 1.000 | 0.819 / 0.826 / 0.813 | 14.825 / 14.635 / 14.571 | no |
| sports/nfl-adversarial-noisy-upset | 0.000 / 0.000 / 0.000 | 1.540 / 1.733 / 1.665 | 3.340 / 13.352 / 12.164 | no |
| rag/direct_answer | 1.000 / 1.000 / 1.000 | 38.323 / 3.998 / 4.024 | 0.497 / 3.498 / 3.461 | no |
| rag/unanswerable | 1.000 / 1.000 / 1.000 | 46.307 / 3.813 / 3.891 | 0.086 / 0.983 / 0.968 | no |

## Deterministic routing

A five-percentage-point margin is required; executable full-suite pass rate drives coding.

| Workload | Qwen | Gemma | Recommendation |
|---|---:|---:|---|
| coding | 100.0% | 80.0% | Qwen |
| reasoning | 83.3% | 100.0% | Gemma |
| repository | 100.0% | 50.0% | Qwen |
| multimodal | 93.4% | 84.1% | Qwen |
| vision | 93.4% | 84.1% | Qwen |
| camera | 91.4% | 91.1% | No meaningful difference |
| rag | 99.9% | 95.0% | No meaningful difference |
| sports | 100.0% | 0.0% | Qwen |
| hallucination | 100.0% | 0.0% | Qwen |
| long_context | 100.0% | 60.9% | Qwen |
| default | 77.8% | 11.1% | Qwen |

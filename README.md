# local-mlx-lab

A reproducible, localhost-only MLX lab for comparing one model at a time on a 24 GiB Apple
Silicon Mac. It provides safe model process management, an OpenAI-compatible client, repeatable
benchmarks, JSONL measurements, Markdown summaries, and a separate multimodal test.

## Models and API compatibility

| Alias | Model | Runtime | Download | Multimodal | Responses API |
|---|---|---|---:|---|---|
| `qwen` | `mlx-community/Qwen3.5-9B-4bit` | `mlx-vlm` | ~5.98 GB | yes | yes |
| `gptoss` | `mlx-community/gpt-oss-20b-MXFP4-Q8` | `mlx-lm` | ~12.1 GB | no | no |
| `gptoss-final` | same GPT-OSS weights, final-channel JSON profile | `mlx-lm` | cached with `gptoss` | no | no |
| `gemma` | `mlx-community/gemma-4-12B-it-4bit` | `mlx-vlm` | ~6.77 GB | yes | yes |

`gemma-default` and `gemma-strict` are experimental request profiles over the same cached Gemma
weights. The strict profile suppresses channel-token generation but is not the recommended default;
see [`docs/gemma-template-investigation.md`](docs/gemma-template-investigation.md).

All servers explicitly bind to `127.0.0.1:8080`. The runtime registry is
[`config/models.yaml`](config/models.yaml); model IDs are not scattered through the code.

## Prerequisites and setup

- Apple Silicon Mac with macOS and Xcode Command Line Tools
- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Enough free disk space for the selected model plus cache overhead

```bash
make info
make setup
make check
```

Setup creates/synchronizes `.venv` from `uv.lock`; it does not download weights. Copy
`.env.example` to `.env` only if you need overrides.

## Download, start, switch, and stop

Downloads are explicit and interactive so a start command cannot unexpectedly fetch gigabytes:

```bash
make download MODEL=qwen
make model MODEL=qwen
make health
make stop
```

After downloading each model, `make model MODEL=qwen|gptoss|gemma` is the one-command start or
switch operation. Switching first stops the process recorded in `.local-mlx/active.json` and then
loads the requested model. `make stop` only signals the recorded process after checking its PID and
creation time; it will not blindly kill whatever happens to occupy port 8080. Logs are under
`.local-mlx/`.

## Query the API

```bash
uv run local-mlx chat "Write a robust Python retry function."
curl http://127.0.0.1:8080/v1/models
curl http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"mlx-community/Qwen3.5-9B-4bit","messages":[{"role":"user","content":"Hello"}],"max_tokens":64}'
```

Application code uses a runtime-neutral abstraction which discovers the managed active model:

```python
from local_mlx import LocalLLM

llm = LocalLLM()
print(llm.chat("Review this Python function for potential bugs."))
```

See [`examples/local_client.py`](examples/local_client.py) and
[`examples/openai_sdk.py`](examples/openai_sdk.py) for the official OpenAI SDK configured with
`base_url="http://127.0.0.1:8080/v1"`. `LocalLLM.response()` uses Responses on `mlx-vlm` and hides
the `mlx-lm` mismatch by falling back to chat completions.

## Benchmarks

The suite covers implementation, repair, review, refactoring, explanation, defensive security
engineering, multi-step reasoning, explicit instruction following, schema validation, and three
behaviors grounded in the fixed local document `benchmarks/documents/cedar.txt`.

```bash
make bench MODEL=qwen                 # conservative 2K configuration
make bench MODEL=qwen CONTEXT=8192
make bench MODEL=qwen CONTEXT=16384
make bench-all CONTEXT=2048           # requires all weights downloaded; sequential only
```

`CONTEXT` records and caps the evaluation configuration; prompts remain fixed so results are
comparable. Results go to `benchmarks/results/` as JSONL plus Markdown. Measurements include model,
test/configuration, server-reported token usage, TTFT from streaming, elapsed time, output speed,
schema validity, output/error, process RSS, system memory, swap, and memory pressure. If initial
pressure is warning/critical, or becomes critical during a case, the run aborts instead of forcing
the machine. Review JSONL outputs qualitatively for correctness and unsupported RAG claims; the
report deliberately does not declare the fastest model the best.

Run only one category with:

```bash
uv run local-mlx benchmark --model qwen --context-size 2048 --category coding
```

### Practical local-development profiles

The extended suite adds fixture-backed REST consumption, image-via-REST analysis, privacy-safe
camera scenes and temporal changes, mixed JSON/text/image extraction, fictional NFL/NBA/MLB-style
matchups, deterministic Python features versus model arithmetic, hallucination resistance, REST
tool planning, and repository navigation/change tasks.

```bash
make bench-fast MODEL=qwen
make bench-vision MODEL=qwen
make bench-camera MODEL=qwen
make bench-sports MODEL=qwen
make bench-agentic MODEL=qwen
make bench-hallucination MODEL=qwen
make bench-rag MODEL=qwen CONTEXT=2048
make bench-executable MODEL=qwen
make bench-realistic-rag MODEL=qwen
make bench-photographic MODEL=qwen
make bench-full MODEL=qwen
make compare MODEL_A=qwen MODEL_B=gemma
make reliability-report
```

Fixture APIs and MLX both bind only to `127.0.0.1`. Retrieval, parsing, model inference, and final
quality are recorded separately, so HTTP failures do not count against model quality. See
[`docs/practical-benchmarks.md`](docs/practical-benchmarks.md) for formulas, privacy boundaries,
small-sample prediction caveats, score thresholds, and adding a future authenticated provider.
The executable suite applies changes only inside disposable fixture copies and runs targeted plus
full tests. Realistic RAG uses naturally sized repository/document corpora at approximately 2K,
8K, and 16K. The photographic profile uses attributed Wikimedia Commons photographs and never asks
a local model to generate imagery. Reviewed repeated-trial data is in
[`docs/results/reliability-trials.md`](docs/results/reliability-trials.md).
GPT-OSS results and open follow-ups are tracked in
[`docs/results/gptoss-evaluation-2026-08-19.md`](docs/results/gptoss-evaluation-2026-08-19.md).

## Multimodal test

Keep image evaluation separate from fair text comparisons:

```bash
uv run local-mlx multimodal --model qwen --image /absolute/path/to/image.png
uv run local-mlx multimodal --model gemma --image /absolute/path/to/image.png
```

## Memory guidance

Model files are not the full runtime footprint: weights, KV cache, temporary allocations, the OS,
and other applications share 24 GiB. Registry defaults cap KV context at 16K, server concurrency at
one for VLMs, and vision cache at one. Begin at 2K, close memory-heavy applications, watch
`make health`, and stop if swap rises persistently. `gptoss` is the tightest fit (~12.1 GB weights)
and should be tested especially conservatively.

The GPT-OSS command sequence, capability-skip matrix, and completed-run status are in
[`docs/gptoss-readiness.md`](docs/gptoss-readiness.md). Use `gptoss-final` for structured benchmark
requests; it forces the Harmony final channel and injects the requested JSON schema.

## Codex and other tools

Most Python, TypeScript, editor, and agent clients that accept an OpenAI base URL can target the
chat-completions endpoint. Codex needs Responses API compatibility; see
[`docs/codex-local-provider.md`](docs/codex-local-provider.md). No Codex configuration is modified.

## Troubleshooting

- **Not cached:** run `make download MODEL=<alias>` and confirm the interactive download.
- **Port 8080 busy:** stop the other service; this project will not kill an unowned process.
- **Server exits:** inspect `.local-mlx/<alias>.log` and rerun `uv sync --all-groups`.
- **Out of memory or heavy swap:** `make stop`, close large apps, restart at 2K, and prefer Qwen.
- **Structured JSON invalid:** this is a benchmark result; inspect JSONL rather than deleting it.
- **Responses request fails on gptoss:** expected; `mlx-lm` has no Responses endpoint.
- **Stale state:** `make health` detects a missing/reused process without signaling it.

## Add a model

Add one entry to `config/models.yaml` with a unique alias, exact Hugging Face ID, installed runtime,
port, capabilities, conservative context and temperature, estimated download, server entry point,
arguments, and notes. Run `uv run local-mlx preflight <alias>`, add registry tests if introducing a
new runtime, then download explicitly. Never add a LAN host flag to the registry.

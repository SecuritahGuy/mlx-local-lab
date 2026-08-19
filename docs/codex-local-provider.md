# Codex local-provider experiment

This is an experiment, not an automatic configuration change. Back up and edit your Codex
configuration yourself. Start with Qwen because its `mlx-vlm` runtime provides the Responses API.

```bash
make download MODEL=qwen
make model MODEL=qwen
curl http://127.0.0.1:8080/v1/models
curl -sS http://127.0.0.1:8080/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{"model":"mlx-community/Qwen3.5-9B-4bit","input":"Reply with LOCAL_OK","max_output_tokens":32}'
```

Suggested *manual* `~/.codex/config.toml` experiment:

```toml
model = "mlx-community/Qwen3.5-9B-4bit"
model_provider = "local-mlx"

[model_providers.local-mlx]
name = "Local MLX (experimental)"
base_url = "http://127.0.0.1:8080/v1"
wire_api = "responses"
```

Restart Codex after editing and keep the server bound to `127.0.0.1`. Exact Codex configuration
fields can change, so compare this snippet with the version of Codex you have installed before use.
Tool calling, streaming events, reasoning fields, token accounting, and other Responses semantics
may be only partially compatible even if a basic request succeeds.

`gptoss` uses `mlx-lm`, whose installed server supports `/v1/models` and
`/v1/chat/completions` but not `/v1/responses`. It therefore cannot be a direct Codex Responses
provider. The `LocalLLM.response()` abstraction falls back to chat completions for ordinary Python
applications, but that does not change Codex's wire protocol. A small Responses-to-Chat adapter is
a possible second phase only after the Qwen experiment establishes which semantics Codex needs.

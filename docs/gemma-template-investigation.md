# Gemma template and channel-marker investigation

## What the runtime is doing

The cached Gemma tokenizer template ends a non-thinking generation prompt with
`<|channel>thought\n<channel|>`. Tokenizer inspection maps `<|channel>` to token
100 and `<channel|>` to token 101. Neither is in the model's configured EOS set
(`[1, 106, 50]`), so an output loop can continue emitting channel delimiters.

The installed `mlx-vlm` OpenAI-compatible route accepts the template control
`enable_thinking` through `extra_body`; it does not implement a normal request
`stop` field suitable for this fix. Response extraction was left unchanged, and
no channel stripping, fence removal beyond the existing generic JSON parser, or
model-specific JSON repair was added.

## Configurations tested

- `gemma-default` uses the ordinary request path.
- `gemma-strict` passes `extra_body={"enable_thinking": false}`, applies a -100
  logit bias to channel-token IDs 100 and 101, and adds a system instruction to
  emit only the requested raw format without channel tokens or Markdown fences.

The same cached weights and server are used in both configurations. An initial
attempt passed `enable_thinking` as a top-level OpenAI client argument and failed
before inference; those transport-error artifacts are excluded. The corrected
implementation passes it as an extension body field.

## Result

The strict profile removed the repeated internal channel-marker symptom. It did
not materially improve benchmark quality:

| Profile | Hallucination score | Repository score | Executable full-suite pass |
|---|---:|---:|---:|
| Gemma default | 5.0/10 | 8.0/10 | 80% |
| Gemma strict | 5.0/10 | 7.0/10 | 60% |

In strict hallucination testing, the sports answer was `None` and the API answer
was `Abstain`; neither satisfied the unchanged deterministic abstention matcher,
so the evaluated failures remained. Architecture navigation remained schema
invalid, and strict mode also made the hard executable case schema-invalid at
the output limit. The security patch still failed its targeted tests.

Conclusion: serving controls fix the visible channel-token failure mode, but the
underlying format-following, abstention, and executable-correctness weaknesses
remain. Strict serving is useful for cleaner output, not a better default Gemma
configuration. Qwen did not exhibit the channel-token pathology, so no asymmetric
token suppression was applied to it.

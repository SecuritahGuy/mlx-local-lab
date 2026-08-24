# Published experiment summaries

Use this directory for reviewed, shareable benchmark summaries. Raw output stays
under `benchmarks/results/` and is ignored by Git.

Before publishing a summary, remove credentials, private prompts or retrieved
content, personal filenames, absolute home-directory paths, and unnecessary
host identifiers. Retain the model ID, benchmark revision, hardware class,
runtime versions, methodology, aggregate metrics, and known limitations needed
to interpret or reproduce the experiment.

Reviewed summaries:

- [`statspace-validation-2026-08-21.md`](statspace-validation-2026-08-21.md) — StatSpace v3/v4
  sports benchmark validation across Qwen, Gemma, and GPT-OSS.
- [`mlx-candidates-2026-08-24.md`](mlx-candidates-2026-08-24.md) — download, runtime, memory,
  and smoke-test results for Qwen3.8, LFM2.5-VL, Nemotron Parse, and Octen Embedding.

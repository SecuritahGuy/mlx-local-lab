# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added

- Executable coding benchmarks with disposable repositories, targeted/full test execution,
  regression checks, minimality scoring, and explicit no-change evaluation.
- Natural-corpus RAG evaluation at approximately 2K, 8K, and 16K contexts.
- Licensed photographic fixtures, provenance metadata, reliability reporting, and repeated-trial
  summaries.
- `gptoss-final`, `gemma-default`, and `gemma-strict` request profiles.
- Versioned natural and guardrailed hallucination tracks.
- Reproducible `qwen38` and `lfm25` model profiles, including Qwen3.8's matching MTP drafter and
  an isolated OptiQ runtime for LFM2.5-VL.
- A reviewed August 2026 MLX candidate report covering Qwen3.8, LFM2.5-VL, Nemotron Parse, and
  Octen Embedding download integrity, runtime compatibility, memory behavior, and smoke tests.
- Companion-artifact support so model downloads and startup preflight verify required drafter
  repositories as well as the primary checkpoint.

### Changed

- GPT-OSS structured requests now force the Harmony final channel and include the target JSON
  schema, raising the observed core mean quality from 70.2% to 90.1%.
- Executable edit quality now includes `minimality-v2` graded edit efficiency and added-comment
  detection while targeted and full tests remain the correctness authority.
- Consolidated reliability output now includes GPT-OSS with per-case sample coverage and N/A values
  for missing or insufficient repeated-trial data.
- Executable no-change instructions now require a consistent false decision with an empty changes
  list. The validation run improved patch application from 80% to 100% and appropriate no-change
  behavior from 0% to 100%.
- Executable prompts now discourage style-only rewrites, and hallucination prompts define a strict
  evidence/abstention contract. Validation reached 100% executable minimality and a 10.0/10
  hallucination score with 3/3 correct abstentions on supported text cases.
- Text-only capabilities are skipped rather than scored as intelligence failures.
- Explicit model overrides now select the overridden model's runtime instead of inheriting an
  unrelated active server runtime.
- Qwen3.8 is capped at a conservative 2K context and retained for controlled experiments after its
  4-bit target plus MTP drafter triggered heavy swap and elevated memory pressure on the 24 GiB
  reference host.
- LFM2.5-VL runs through an isolated `uvx` OptiQ environment because its Transformers requirement
  conflicts with the shared MLX-VLM environment.

### Fixed

- GPT-OSS Harmony channel text leaking into structured benchmark responses.
- JSON schema noncompliance under `mlx-lm`'s ignored `response_format` parameter.
- Runtime selection when `LOCAL_MLX_MODEL` differs from the currently managed model.
- Image-only hallucination cases being attempted and scored as failures for text-only models.
- Local multimodal requests now encode image files as standard base64 data URLs and expose the
  documented `--model` and `--image` options instead of sending unsupported `file://` URLs.

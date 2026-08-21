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
- Grounded StatSpace recommendation explanations with authoritative deterministic gates.

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
- StatSpace slate evaluation now covers inclusive thresholds, required versus optional source
  health, duplicate precedence, and complete candidate coverage; ledger audits now score settled
  stake explicitly.

### Fixed

- GPT-OSS Harmony channel text leaking into structured benchmark responses.
- JSON schema noncompliance under `mlx-lm`'s ignored `response_format` parameter.
- Runtime selection when `LOCAL_MLX_MODEL` differs from the currently managed model.
- Image-only hallucination cases being attempted and scored as failures for text-only models.

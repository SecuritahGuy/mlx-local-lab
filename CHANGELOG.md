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
- Versioned `executable-v2` and `hallucination-v2` prompt contracts.

### Changed

- GPT-OSS structured requests now force the Harmony final channel and include the target JSON
  schema, raising the observed core mean quality from 70.2% to 90.1%.
- Executable no-change instructions now require a consistent false decision with an empty changes
  list. The validation run improved patch application from 80% to 100% and appropriate no-change
  behavior from 0% to 100%.
- Executable prompts now discourage style-only rewrites, and hallucination prompts define a strict
  evidence/abstention contract. The first v2 validation reached 100% executable minimality and 3/3
  correct abstentions on supported text cases.
- Text-only capabilities are skipped rather than scored as intelligence failures.
- Explicit model overrides now select the overridden model's runtime instead of inheriting an
  unrelated active server runtime.

### Fixed

- GPT-OSS Harmony channel text leaking into structured benchmark responses.
- JSON schema noncompliance under `mlx-lm`'s ignored `response_format` parameter.
- Runtime selection when `LOCAL_MLX_MODEL` differs from the currently managed model.
- Image-only hallucination cases being attempted and scored as failures for text-only models.

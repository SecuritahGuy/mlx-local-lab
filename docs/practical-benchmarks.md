# Practical benchmark methodology

The practical suite separates retrieval, parsing, model inference, and quality. A failed HTTP
request, invalid content type, oversized body, malformed payload, timeout, or corrupt image stops
before inference and is marked as an infrastructure failure. It is not assigned a model-quality
score.

## Local fixtures and privacy

`scripts/generate-fixtures.py` creates deterministic illustrations and fictional sports records.
The camera fixtures contain no real people, identities, faces, credentials, private locations, or
sensitive traits. Camera prompts prohibit identity, intent, criminality, and threat inference. The
fixture server binds to an ephemeral `127.0.0.1` port; MLX remains on `127.0.0.1:8080`.

## Scores

Raw output and measurements are always retained in JSONL. Category quality is the arithmetic mean
of deterministic per-case values in `[0, 1]`, multiplied by ten:

- Camera: boolean object presence, person count, lighting/weather, temporal state, Q&A evidence,
  and visible anomaly recognition. Summary wording is not scored.
- Vision: required facts visible in the supplied synthetic diagram, screenshot, chart, or combined
  JSON/text/image sources.
- Sports: valid probabilities, internally consistent factors, source-grounded evidence, and a
  separate arithmetic case. Winner outcome, Brier score, and log loss are reported but do not erase
  a sensible losing prediction.
- Hallucination: appropriate explicit abstention when the requested fact is absent.
- Agentic: correct minimal endpoint selection and successful completion after retrieval.
- Repository: expected-file recall, a restricted write target, and focused test success in a
  temporary fixture copy.
- Speed: median generation rate divided by 30 tokens/s, capped at 10.
- Memory efficiency: `10 × (1 - peak sampled system-used GiB / 24)`, floored at zero.

The displayed overall value is an unweighted mean of displayed categories. It is provided alongside,
not instead of, category scores and raw data. Recommendations use fixed category thresholds and are
explicitly labeled benchmark-derived.

The original Qwen validation displayed 8.41/10 because it averaged six quality categories with
speed (5.05) and system-wide memory efficiency (3.75). This is intentional rather than a quality
regression. Unsupported categories are omitted, model failures score zero, and infrastructure
failures receive no model-quality score.

## Difficulty and comparison

Every comparison row is tagged `easy`, `medium`, `hard`, or `adversarial`. Camera, sports,
repository, and hallucination each contain all four tiers. The repository adversarial case rewards
an explicit no-change decision when behavior matches the supplied contract.

Prompt contracts that materially affect scoring are versioned in JSONL rows. `executable-v2`
requires boolean/list consistency for no-change decisions and explicitly prohibits style-only
comments, docstrings, helpers, and refactors. `hallucination-v2` defines missing source fields as
unknown and requires answers to begin with `INSUFFICIENT_EVIDENCE` when the requested fact is not
directly supported. Results without these fields predate prompt versioning and should not be used as
like-for-like evidence of a prompt improvement.

Pairwise category winners require at least 0.30 points on the 10-point scale. Difficulty-tier
winners require at least 3 percentage points. Smaller gaps are reported as `Tie / no meaningful
difference`. Performance uses separate practical margins (0.15 seconds for median TTFT, 0.75 tok/s
for generation speed, and 0.5 GiB for peak system memory). Unsupported capabilities are `N/A`, not
zero.

TTFT outliers use `TTFT > max(3 × model median, 3.0 seconds)`. Reports preserve input type,
server-reported prompt/output tokens, runtime, retrieval latency, throughput, and memory. Causes are
described only when a measured feature supports them; otherwise the report says no cause was
established.

Only three fictional historical outcomes are included initially, so aggregate prediction accuracy,
Brier score, log loss, and calibration are marked small-sample and are not statistically meaningful.

## External providers

Implement the `SportsProvider` protocol for another source and map provider data into a stable team
shape. For REST sources, construct `RestDataSource` with a base URL, bounded timeout/size, and the
names of environment variables containing bearer or basic-auth credentials. Do not put secrets in
the registry, fixture files, command line, cache keys, logs, or result records. Add new domains only
after reviewing their privacy and data-retention requirements.

## Profiles

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
```

Text-only RAG behavior is compared under 2048, 8192, and 16384 caps with deterministic irrelevant
padding. Actual server-reported prompt tokens are recorded; padding leaves output ground truth
unchanged. Image profiles are not duplicated across token contexts because that would not isolate a
meaningful image variable. Cold startup is recorded by lifecycle management; inference measurements
are warm and keep HTTP download time separate from model latency.

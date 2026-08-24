# MLX candidate evaluation — 2026-08-24

## Host and scope

Four MLX checkpoints published during August 10–24, 2026 were downloaded and smoke-tested on
the lab's 24 GiB Apple M5 host. Tests were sequential; no model servers remained active afterward.

## Results

| Candidate | Downloaded | Result | Disposition |
|---|---:|---|---|
| Qwen3.8 27B 4-bit + MTP | 15.23 GB | Loaded and generated correctly, but startup raised swap from 0.99 GB to 6.30 GB; the benchmark safety guard then detected warning memory pressure | Keep cached for controlled smoke tests only; not a 24 GiB daily driver |
| LFM2.5-VL 3B OptiQ 4-bit | 2.64 GB | API and image recognition worked at roughly 16–45 tok/s, but all four strict vision cases failed their required JSON output contracts | Keep as an experimental human-facing image reader, not structured automation |
| Nemotron Parse 2.0 4-bit | 1.41 GB | Direct MLX generation entered token repetition loops on both tested images; the OpenAI server path also failed for this encoder-decoder architecture | Keep downloaded artifact out of the runnable registry; reject this 4-bit variant |
| Octen Embedding 4B MLX 4-bit | 2.12 GB | Both semantic-retrieval queries ranked the intended document first; vectors were 2,560-dimensional with unit norm | Best successful candidate; evaluate on a larger domain retrieval set next |

## Runtime notes

- Qwen's MTP repository is a required companion artifact. The registry downloads and verifies both
  repositories and starts them with a 2K KV cap, one sequence, and MTP draft mode.
- LFM2.5 OptiQ conflicts with the lab's Transformers dependency when installed in the shared
  environment. Its registry entry uses an isolated `uvx` runtime with `mlx-optiq>=0.4.20`.
- The vision benchmark artifact is `20260824-161648-lfm25-vision.{jsonl,md}`.
- Nemotron Parse can deserialize with MLX-VLM's built-in processor, but its server and output-quality
  failures make a normal lab alias misleading.

# Benchmark results

This directory is the default destination for locally generated benchmark
JSONL and Markdown reports. Those files are ignored because they can contain
full prompts, model responses, retrieved data, absolute paths, and host-level
performance details.

To share experimental progress, review and redact a report first, then place a
curated summary in `docs/results/`. Keep the model IDs, benchmark revision,
hardware class, methodology, and aggregate measurements needed to reproduce
the experiment, while removing personal paths, credentials, and private input.

The `.gitkeep` file preserves this output directory in fresh clones.

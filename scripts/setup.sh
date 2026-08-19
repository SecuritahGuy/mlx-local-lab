#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
command -v uv >/dev/null 2>&1 || { echo "uv is required: https://docs.astral.sh/uv/"; exit 1; }
uv sync --all-groups
echo "Setup complete. No model weights were downloaded."
uv run local-mlx models

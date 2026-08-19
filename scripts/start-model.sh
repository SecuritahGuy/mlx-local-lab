#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec uv run local-mlx start "${1:?usage: start-model.sh qwen|gptoss|gemma}"

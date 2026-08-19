.PHONY: setup info model stop health bench bench-all bench-fast bench-vision bench-camera bench-sports bench-agentic bench-hallucination bench-hallucination-natural bench-hallucination-guardrailed bench-rag bench-full bench-executable bench-realistic-rag bench-photographic reliability-report compare test lint check download multimodal

MODEL ?= qwen
CONTEXT ?= 2048
IMAGE ?=
MODEL_A ?= qwen
MODEL_B ?= gemma

setup:
	./scripts/setup.sh

info:
	./scripts/system-info.sh

download:
	uv run local-mlx download $(MODEL)

model:
	./scripts/start-model.sh $(MODEL)

stop:
	./scripts/stop-model.sh

health:
	uv run local-mlx health

bench:
	uv run local-mlx benchmark --model $(MODEL) --context-size $(CONTEXT)

bench-all:
	uv run local-mlx benchmark-all --context-size $(CONTEXT)

bench-fast:
	uv run local-mlx practical --model $(MODEL) --profile fast

bench-vision:
	uv run local-mlx practical --model $(MODEL) --profile vision

bench-camera:
	uv run local-mlx practical --model $(MODEL) --profile camera

bench-sports:
	uv run local-mlx practical --model $(MODEL) --profile sports

bench-agentic:
	uv run local-mlx practical --model $(MODEL) --profile agentic

bench-hallucination:
	uv run local-mlx practical --model $(MODEL) --profile hallucination

bench-hallucination-natural:
	uv run local-mlx practical --model $(MODEL) --profile hallucination-natural

bench-hallucination-guardrailed:
	uv run local-mlx practical --model $(MODEL) --profile hallucination-guardrailed

bench-rag:
	uv run local-mlx benchmark --model $(MODEL) --context-size $(CONTEXT) --category rag

bench-full:
	uv run local-mlx practical --model $(MODEL) --profile full

bench-executable:
	uv run local-mlx bench-executable --model $(MODEL)

bench-realistic-rag:
	uv run local-mlx bench-realistic-rag --model $(MODEL)

bench-photographic:
	uv run local-mlx bench-photographic --model $(MODEL)

reliability-report:
	uv run local-mlx reliability-report

compare:
	uv run local-mlx compare $(MODEL_A) $(MODEL_B)

multimodal:
	@test -n "$(IMAGE)" || { echo "Set IMAGE=/absolute/path/to/image"; exit 2; }
	uv run local-mlx multimodal --model $(MODEL) --image "$(IMAGE)"

test:
	uv run pytest

lint:
	uv run ruff check .

check: lint test

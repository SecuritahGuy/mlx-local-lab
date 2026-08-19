from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / ".local-mlx"
REGISTRY_PATH = ROOT / "config" / "models.yaml"


class ModelConfig(BaseModel):
    alias: str = ""
    name: str
    model_id: str
    runtime: str
    port: int = 8080
    model_type: str
    multimodal: bool
    reasoning: bool
    context_limit: int = Field(le=16384)
    temperature: float = 0.1
    estimated_download_gb: float
    startup_command: str
    startup_args: list[str] = []
    responses_api: bool = False
    request_profile: str = "default"
    chat_template: str | None = None
    notes: str = ""

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"


def load_models(path: Path = REGISTRY_PATH) -> dict[str, ModelConfig]:
    raw = yaml.safe_load(path.read_text())["models"]
    return {alias: ModelConfig(alias=alias, **value) for alias, value in raw.items()}


def get_model(alias: str) -> ModelConfig:
    models = load_models()
    if alias not in models:
        raise ValueError(f"Unknown model {alias!r}; choose: {', '.join(models)}")
    return models[alias]


def configured_base_url() -> str:
    return os.getenv("LOCAL_MLX_BASE_URL", "http://127.0.0.1:8080/v1")

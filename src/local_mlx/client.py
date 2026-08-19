from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

from openai import OpenAI

from local_mlx.config import configured_base_url, get_model, load_models
from local_mlx.models import read_state


class LocalLLM:
    """Runtime-neutral client for the one active localhost MLX model."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = base_url or configured_base_url()
        self._client = OpenAI(
            base_url=self.base_url, api_key=api_key or os.getenv("LOCAL_MLX_API_KEY", "local")
        )

    @property
    def model(self) -> str:
        override = os.getenv("LOCAL_MLX_MODEL")
        if override:
            return override
        state = read_state()
        if state:
            return state["model_id"]
        models = self._client.models.list().data
        if not models:
            raise RuntimeError("The server reported no loaded model")
        return models[0].id

    def chat(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 512,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        kwargs: dict[str, Any] = {}
        if response_format:
            kwargs["response_format"] = response_format
        result = self._client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return result.choices[0].message.content or ""

    def stream(self, prompt: str, **kwargs: Any) -> Iterator[Any]:
        state = read_state()
        if state and get_model(state["alias"]).request_profile == "strict":
            kwargs.setdefault("extra_body", {"enable_thinking": False})
            kwargs.setdefault("logit_bias", {"100": -100, "101": -100})
        return self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            stream_options={"include_usage": True},
            **kwargs,
        )

    def response(self, prompt: str, **kwargs: Any) -> str:
        state = read_state()
        model_id = self.model
        runtime = state["runtime"] if state and state["model_id"] == model_id else next(
            (cfg.runtime for cfg in load_models().values() if cfg.model_id == model_id), None
        )
        if runtime == "mlx-lm":
            return self.chat(prompt, **kwargs)
        if "max_tokens" in kwargs:
            kwargs["max_output_tokens"] = kwargs.pop("max_tokens")
        result = self._client.responses.create(model=model_id, input=prompt, **kwargs)
        return result.output_text

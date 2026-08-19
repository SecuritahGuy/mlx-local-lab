from unittest.mock import MagicMock, patch

from local_mlx.client import LocalLLM


def test_model_env_override(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_MLX_MODEL", "test-model")
    assert LocalLLM().model == "test-model"


def test_response_falls_back_for_mlx_lm() -> None:
    client = LocalLLM()
    state = {"runtime": "mlx-lm", "model_id": "mlx-community/gpt-oss-20b-MXFP4-Q8"}
    with patch("local_mlx.client.read_state", return_value=state):
        client.chat = MagicMock(return_value="ok")
        assert client.response("hello") == "ok"
        client.chat.assert_called_once_with("hello")


def test_response_translates_token_limit(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_MLX_MODEL", "mlx-community/Qwen3.5-9B-4bit")
    client = LocalLLM()
    client._client.responses.create = MagicMock(
        return_value=MagicMock(output_text="response-ok")
    )
    assert client.response("hello", max_tokens=12) == "response-ok"
    client._client.responses.create.assert_called_once_with(
        model="mlx-community/Qwen3.5-9B-4bit",
        input="hello",
        max_output_tokens=12,
    )


def test_model_override_uses_overridden_models_runtime(monkeypatch) -> None:
    monkeypatch.setenv("LOCAL_MLX_MODEL", "mlx-community/Qwen3.5-9B-4bit")
    client = LocalLLM()
    client._client.responses.create = MagicMock(
        return_value=MagicMock(output_text="response-ok")
    )
    state = {"runtime": "mlx-lm", "model_id": "mlx-community/gpt-oss-20b-MXFP4-Q8"}
    with patch("local_mlx.client.read_state", return_value=state):
        assert client.response("hello") == "response-ok"


def test_strict_gemma_suppresses_channel_control_tokens() -> None:
    client = LocalLLM()
    client._client.chat.completions.create = MagicMock(return_value=iter(()))
    state = {"alias": "gemma-strict", "model_id": "mlx-community/gemma-4-12B-it-4bit"}
    with patch("local_mlx.client.read_state", return_value=state):
        list(client.stream("answer from evidence"))
    kwargs = client._client.chat.completions.create.call_args.kwargs
    assert kwargs["extra_body"] == {"enable_thinking": False}
    assert kwargs["logit_bias"] == {"100": -100, "101": -100}

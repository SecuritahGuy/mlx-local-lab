from local_mlx.config import get_model, load_models
from local_mlx.models import server_command


def test_exact_registry() -> None:
    models = load_models()
    assert {key: value.model_id for key, value in models.items()} == {
        "qwen": "mlx-community/Qwen3.5-9B-4bit",
        "gptoss": "mlx-community/gpt-oss-20b-MXFP4-Q8",
        "gemma": "mlx-community/gemma-4-12B-it-4bit",
    }


def test_every_server_is_localhost_only() -> None:
    for model in load_models().values():
        command = server_command(model)
        assert command[command.index("--host") + 1] == "127.0.0.1"
        assert command[command.index("--port") + 1] == "8080"


def test_runtime_split() -> None:
    assert get_model("qwen").responses_api
    assert get_model("gemma").responses_api
    assert not get_model("gptoss").responses_api

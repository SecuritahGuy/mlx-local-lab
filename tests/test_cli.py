from typer.testing import CliRunner

from local_mlx import cli


def test_multimodal_sends_local_image_as_data_url(tmp_path, monkeypatch) -> None:
    image = tmp_path / "fixture.png"
    image.write_bytes(b"fake-png")
    captured = {}

    class Response:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "ok"}}]}

    def post(url, json, timeout):
        captured.update(url=url, payload=json, timeout=timeout)
        return Response()

    monkeypatch.setattr(cli.httpx, "post", post)
    result = CliRunner().invoke(
        cli.app, ["multimodal", "--model", "qwen", "--image", str(image)]
    )

    assert result.exit_code == 0
    image_url = captured["payload"]["messages"][0]["content"][1]["image_url"]["url"]
    assert image_url.startswith("data:image/png;base64,")
    assert "ok" in result.stdout

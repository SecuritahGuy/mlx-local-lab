from pathlib import Path

import pytest

from local_mlx.fixture_server import FixtureServer
from local_mlx.rest import RestDataSource, RetrievalError


@pytest.fixture
def fixture_source(tmp_path: Path):
    with FixtureServer() as server:
        yield RestDataSource(server.base_url, timeout=0.05, retries=0, cache_dir=tmp_path)


def test_fixture_server_json_and_image(fixture_source: RestDataSource) -> None:
    team, team_result = fixture_source.get_json("/api/sports/nfl/harbor-hawks")
    image, image_result = fixture_source.get_image("/api/cameras/front-door/snapshot/package")
    assert team["team"] == "Harbor Hawks"
    assert team_result.retrieval_success and team_result.parse_success
    assert image.startswith(b"\x89PNG")
    assert image_result.content_type == "image/png" and image_result.parse_success


def test_cache_is_safe_and_reused(fixture_source: RestDataSource) -> None:
    fixture_source.get_json("/api/sports/nfl/harbor-hawks")
    _, second = fixture_source.get_json("/api/sports/nfl/harbor-hawks")
    assert second.cache_hit


@pytest.mark.parametrize(
    ("path", "method", "code"),
    [
        ("/api/errors/404", "get_json", "http_error"),
        ("/api/errors/401", "get_json", "http_error"),
        ("/api/errors/403", "get_json", "http_error"),
        ("/api/errors/429", "get_json", "http_error"),
        ("/api/errors/500", "get_json", "http_error"),
        ("/api/errors/malformed", "get_json", "malformed_json"),
        ("/api/errors/wrong-type", "get_json", "wrong_content_type"),
        ("/api/errors/empty-image", "get_image", "empty_image"),
        ("/api/errors/timeout", "get_json", "timeout"),
    ],
)
def test_api_failures_are_structured(
    fixture_source: RestDataSource, path: str, method: str, code: str
) -> None:
    with pytest.raises(RetrievalError) as caught:
        getattr(fixture_source, method)(path)
    assert caught.value.code == code
    if code == "malformed_json":
        assert caught.value.result.retrieval_success
        assert caught.value.result.parse_success is False


def test_oversized_response_is_stopped() -> None:
    with FixtureServer() as server:
        source = RestDataSource(server.base_url, retries=0, max_response_bytes=1024)
        with pytest.raises(RetrievalError, match="size limit") as caught:
            source.get_json("/api/errors/oversized")
        assert caught.value.code == "oversized_response"


def test_wrong_image_content_type(fixture_source: RestDataSource) -> None:
    with pytest.raises(RetrievalError) as caught:
        fixture_source.get_image("/api/errors/wrong-type")
    assert caught.value.code == "wrong_content_type"

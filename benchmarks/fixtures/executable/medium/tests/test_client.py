from app.client import request_options
from app.config import REQUEST_TIMEOUT_MS


def test_timeout_is_converted_to_seconds() -> None:
    assert REQUEST_TIMEOUT_MS == 500
    assert request_options() == {"timeout": 0.5}

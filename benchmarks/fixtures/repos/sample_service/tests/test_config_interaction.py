from app.api import error_payload


def test_default_error_does_not_expose_detail() -> None:
    assert error_payload(RuntimeError("database hostname secret")) == {"error": "request failed"}

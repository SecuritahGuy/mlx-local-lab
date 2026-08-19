from app.config import REQUEST_TIMEOUT_MS


def request_options() -> dict[str, float]:
    return {"timeout": REQUEST_TIMEOUT_MS}

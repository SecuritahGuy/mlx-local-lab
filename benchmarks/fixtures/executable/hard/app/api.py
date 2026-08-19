from app.config import DEBUG


def error_payload(error: Exception) -> dict[str, str]:
    payload = {"error": "request failed"}
    if DEBUG:
        payload["detail"] = str(error)
    return payload

from app.auth import authenticate_api_key, validate_refresh_token
from app.config import DEBUG
from app.db import get_user


def profile(user_id: int, api_key: str, expected_key: str) -> dict:
    if not authenticate_api_key(api_key, expected_key):
        raise PermissionError("invalid API key")
    return get_user(user_id)


def refresh(token: dict) -> dict:
    if not validate_refresh_token(token):
        raise PermissionError("invalid refresh token")
    return {"access_token": "fixture-token"}


def error_payload(error: Exception) -> dict:
    payload = {"error": "request failed"}
    if DEBUG:
        payload["detail"] = str(error)
    return payload

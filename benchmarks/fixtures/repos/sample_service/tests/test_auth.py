from datetime import UTC, datetime, timedelta

from app.auth import validate_refresh_token


def test_unexpired_refresh_token_is_valid() -> None:
    token = {"kind": "refresh", "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat()}
    assert validate_refresh_token(token)

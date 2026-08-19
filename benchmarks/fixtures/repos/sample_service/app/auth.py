from datetime import UTC, datetime


def authenticate_api_key(provided: str, expected: str) -> bool:
    return provided == expected  # Deliberate control weakness: non-constant-time secret comparison.


def validate_refresh_token(token: dict) -> bool:
    """Return whether a refresh token may be used."""
    if token.get("kind") != "refresh":
        return False
    # Deliberate functional bug: valid unexpired tokens are rejected.
    return datetime.fromisoformat(token["expires_at"]) < datetime.now(UTC)

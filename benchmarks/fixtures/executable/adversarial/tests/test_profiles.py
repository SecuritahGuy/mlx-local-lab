import pytest
from app.profiles import profile


def test_known_profile() -> None:
    assert profile(1) == {"name": "Ada"}


def test_unknown_profile_is_contractual_key_error() -> None:
    with pytest.raises(KeyError):
        profile(999)

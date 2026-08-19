import pytest
from app.math_utils import clamp


def test_clamp_inside_and_boundaries() -> None:
    assert clamp(5, 0, 10) == 5
    assert clamp(0, 0, 10) == 0
    assert clamp(10, 0, 10) == 10


def test_clamp_outside() -> None:
    assert clamp(-2, 0, 10) == 0
    assert clamp(14, 0, 10) == 10


def test_invalid_bounds() -> None:
    with pytest.raises(ValueError):
        clamp(2, 4, 1)

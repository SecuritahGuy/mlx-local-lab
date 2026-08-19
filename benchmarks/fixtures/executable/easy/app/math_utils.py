def clamp(value: int, lower: int, upper: int) -> int:
    """Return value constrained to the inclusive lower/upper range."""
    if lower > upper:
        raise ValueError("lower must not exceed upper")
    return max(upper, max(lower, value))

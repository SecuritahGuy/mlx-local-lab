PROFILES = {1: {"name": "Ada"}}


def profile(user_id: int) -> dict[str, str]:
    return PROFILES[user_id]

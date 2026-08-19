USERS = {1: {"id": 1, "name": "Ada"}, 2: {"id": 2, "name": "Linus"}}


def get_user(user_id: int) -> dict:
    return USERS[user_id]


def get_users(user_ids: list[int]) -> list[dict]:
    # Deliberately inefficient stand-in for one query per user.
    return [get_user(user_id) for user_id in user_ids]

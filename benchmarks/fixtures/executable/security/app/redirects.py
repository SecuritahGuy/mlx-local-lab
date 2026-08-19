def is_safe_redirect(url: str) -> bool:
    return url.startswith("/")

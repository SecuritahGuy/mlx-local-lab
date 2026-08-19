from app.redirects import is_safe_redirect


def test_local_redirects_remain_allowed() -> None:
    assert is_safe_redirect("/account")
    assert is_safe_redirect("/search?q=mlx")


def test_external_and_ambiguous_redirects_are_blocked() -> None:
    assert not is_safe_redirect("https://evil.example")
    assert not is_safe_redirect("//evil.example/path")
    assert not is_safe_redirect("/\\evil.example")
    assert not is_safe_redirect("")

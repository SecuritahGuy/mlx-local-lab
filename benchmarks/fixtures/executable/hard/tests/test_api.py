import os
import subprocess
import sys


def _payload(debug: str | None) -> str:
    env = os.environ.copy()
    if debug is None:
        env.pop("DEBUG", None)
    else:
        env["DEBUG"] = debug
    code = "from app.api import error_payload; print(error_payload(RuntimeError('secret host')))"
    return subprocess.check_output([sys.executable, "-c", code], env=env, text=True)


def test_default_and_false_are_safe() -> None:
    assert "secret host" not in _payload(None)
    assert "secret host" not in _payload("false")


def test_documented_truthy_values_enable_detail() -> None:
    for value in ("1", "true", "yes", "TRUE"):
        assert "secret host" in _payload(value)

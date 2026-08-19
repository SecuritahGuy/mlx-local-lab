from __future__ import annotations

import httpx

from local_mlx.config import configured_base_url
from local_mlx.models import memory_snapshot, read_state


def health_report() -> dict:
    state = read_state()
    report = {"running": bool(state), "state": state, "memory": memory_snapshot()}
    if not state:
        return report
    try:
        response = httpx.get(configured_base_url().removesuffix("/v1") + "/health", timeout=3)
        report["http_status"] = response.status_code
        report["server"] = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        report["error"] = str(exc)
    return report

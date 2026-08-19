from __future__ import annotations

import threading
import time
from contextlib import AbstractContextManager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Self

from local_mlx.config import ROOT

FIXTURE_ROOT = ROOT / "benchmarks" / "fixtures"


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *_: object) -> None:
        return

    def do_GET(self) -> None:
        route = self.path.split("?", 1)[0]
        special = {
            "/api/errors/401": (401, "application/json", b'{"error":"unauthorized"}'),
            "/api/errors/403": (403, "application/json", b'{"error":"forbidden"}'),
            "/api/errors/404": (404, "application/json", b'{"error":"not found"}'),
            "/api/errors/429": (429, "application/json", b'{"error":"rate limited"}'),
            "/api/errors/500": (500, "application/json", b'{"error":"server error"}'),
            "/api/errors/malformed": (200, "application/json", b'{bad json'),
            "/api/errors/wrong-type": (200, "text/plain", b"not json"),
            "/api/errors/empty-image": (200, "image/jpeg", b""),
            "/api/errors/oversized": (200, "application/json", b"x" * 4096),
        }
        if route == "/api/errors/timeout":
            time.sleep(0.3)
            self._send(200, "application/json", b"{}")
            return
        if route in special:
            self._send(*special[route])
            return
        path, content_type = self._resolve(route)
        if not path or not path.is_file():
            self._send(404, "application/json", b'{"error":"not found"}')
            return
        self._send(200, content_type, path.read_bytes())

    def _resolve(self, route: str) -> tuple[Path | None, str]:
        camera_prefix = "/api/cameras/front-door/snapshot/"
        sports_prefix = "/api/sports/"
        vision_prefix = "/api/vision/"
        if route.startswith(camera_prefix):
            name = route.removeprefix(camera_prefix)
            return FIXTURE_ROOT / "camera" / f"{name}.png", "image/png"
        if route.startswith(sports_prefix):
            name = route.removeprefix(sports_prefix).replace("/", "-")
            return FIXTURE_ROOT / "sports" / f"{name}.json", "application/json"
        if route.startswith(vision_prefix):
            name = route.removeprefix(vision_prefix)
            return FIXTURE_ROOT / "api" / f"{name}.png", "image/png"
        if route == "/api/mixed/incident":
            return FIXTURE_ROOT / "api" / "incident.json", "application/json"
        if route == "/api/mixed/runbook":
            return FIXTURE_ROOT / "api" / "runbook.txt", "text/plain"
        return None, "application/octet-stream"

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass


class FixtureServer(AbstractContextManager["FixtureServer"]):
    def __init__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> Self:
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

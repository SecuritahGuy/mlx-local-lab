from __future__ import annotations

import hashlib
import io
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx
from PIL import Image, UnidentifiedImageError


class RetrievalError(RuntimeError):
    """A structured retrieval failure that must not be scored as a model failure."""

    def __init__(self, code: str, message: str, result: RetrievalResult):
        super().__init__(message)
        self.code = code
        self.result = result


@dataclass
class RetrievalResult:
    url: str
    retrieval_success: bool = False
    http_status: int | None = None
    content_type: str | None = None
    download_latency: float | None = None
    parse_success: bool | None = None
    size_bytes: int = 0
    cache_hit: bool = False
    error_code: str | None = None
    error: str | None = None

    def as_dict(self) -> dict:
        return vars(self).copy()


class RestDataSource:
    """Bounded REST GET client with secret-safe configuration and optional disk cache."""

    def __init__(
        self,
        base_url: str,
        *,
        headers: dict[str, str] | None = None,
        bearer_token_env: str | None = None,
        basic_auth_env: tuple[str, str] | None = None,
        timeout: float = 5,
        retries: int = 2,
        max_response_bytes: int = 5 * 1024 * 1024,
        cache_dir: Path | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = dict(headers or {})
        if bearer_token_env and (token := os.getenv(bearer_token_env)):
            self.headers["Authorization"] = f"Bearer {token}"
        self.auth = None
        if basic_auth_env:
            user, password = (os.getenv(name) for name in basic_auth_env)
            if user and password:
                self.auth = (user, password)
        self.timeout = timeout
        self.retries = retries
        self.max_response_bytes = max_response_bytes
        self.cache_dir = cache_dir

    def _url(self, path: str) -> str:
        return path if path.startswith(("http://", "https://")) else self.base_url + "/" + path.lstrip("/")

    def _cache_path(self, url: str, kind: str) -> Path | None:
        if self.cache_dir is None:
            return None
        digest = hashlib.sha256(f"{kind}:{url}".encode()).hexdigest()
        return self.cache_dir / digest

    def _get(self, path: str, expected: Literal["json", "text", "image"]) -> tuple[bytes, RetrievalResult]:
        url = self._url(path)
        result = RetrievalResult(url=url)
        cache = self._cache_path(url, expected)
        if cache and cache.exists():
            result.retrieval_success = True
            result.parse_success = None
            result.size_bytes = cache.stat().st_size
            result.cache_hit = True
            result.content_type = {"json": "application/json", "text": "text/plain", "image": "image/cached"}[expected]
            return cache.read_bytes(), result
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout, headers=self.headers, auth=self.auth) as client:
                for attempt in range(self.retries + 1):
                    try:
                        with client.stream("GET", url) as response:
                            result.http_status = response.status_code
                            result.content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                            if response.status_code in {429, 500, 502, 503, 504} and attempt < self.retries:
                                continue
                            chunks = []
                            size = 0
                            for chunk in response.iter_bytes():
                                size += len(chunk)
                                if size > self.max_response_bytes:
                                    result.size_bytes = size
                                    self._fail(result, "oversized_response", "Response exceeds configured size limit")
                                chunks.append(chunk)
                            body = b"".join(chunks)
                            break
                    except httpx.TransportError:
                        if attempt == self.retries:
                            raise
            assert result.http_status is not None
            result.size_bytes = len(body)
            if not 200 <= result.http_status < 300:
                self._fail(result, "http_error", f"HTTP {result.http_status}")
            valid_type = {
                "json": result.content_type == "application/json",
                "text": result.content_type.startswith("text/"),
                "image": result.content_type in {"image/jpeg", "image/png", "image/webp"},
            }[expected]
            if not valid_type:
                self._fail(result, "wrong_content_type", f"Expected {expected}, got {result.content_type or 'missing'}")
            if expected == "image" and not body:
                self._fail(result, "empty_image", "Image response was empty")
            result.retrieval_success = True
            return body, result
        except httpx.TimeoutException as exc:
            self._fail(result, "timeout", "Request timed out", exc)
        except httpx.TransportError as exc:
            self._fail(result, "transport_error", "Request failed", exc)
        finally:
            result.download_latency = round(time.perf_counter() - started, 6)
        raise AssertionError("unreachable")

    @staticmethod
    def _fail(result: RetrievalResult, code: str, message: str, cause: Exception | None = None) -> None:
        result.error_code = code
        result.error = message
        raise RetrievalError(code, message, result) from cause

    def get_json(self, path: str) -> tuple[dict | list, RetrievalResult]:
        body, result = self._get(path, "json")
        try:
            value = json.loads(body)
            result.parse_success = True
            self._write_cache(result.url, "json", body)
            return value, result
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            result.parse_success = False
            self._fail(result, "malformed_json", "Response was not valid JSON", exc)

    def get_text(self, path: str) -> tuple[str, RetrievalResult]:
        body, result = self._get(path, "text")
        try:
            value = body.decode("utf-8")
            result.parse_success = True
            self._write_cache(result.url, "text", body)
            return value, result
        except UnicodeDecodeError as exc:
            result.parse_success = False
            self._fail(result, "text_decode_error", "Response was not UTF-8 text", exc)

    def get_image(self, path: str) -> tuple[bytes, RetrievalResult]:
        body, result = self._get(path, "image")
        try:
            with Image.open(io.BytesIO(body)) as image:
                image.verify()
            result.parse_success = True
            self._write_cache(result.url, "image", body)
            return body, result
        except (UnidentifiedImageError, OSError) as exc:
            result.parse_success = False
            self._fail(result, "invalid_image", "Response was not a valid image", exc)

    def _write_cache(self, url: str, kind: str, body: bytes) -> None:
        cache = self._cache_path(url, kind)
        if cache and not cache.exists():
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(body)

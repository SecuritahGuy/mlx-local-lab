import httpx

from app.config import API_RETRIES


def retry_count() -> int:
    return API_RETRIES


def fetch(url: str) -> dict:
    return httpx.get(url, timeout=2).json()

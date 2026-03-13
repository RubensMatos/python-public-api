"""Client responsible for fetching and caching public API data."""

from __future__ import annotations

from dataclasses import dataclass
import json
import threading
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .config import CACHE_TTL_SECONDS, UPSTREAM_BASE_URL, UPSTREAM_TIMEOUT_SECONDS


@dataclass
class FetchResult:
    data: list[dict[str, Any]]
    source: str


class JsonPlaceholderClient:
    """Fetches data from JSONPlaceholder and falls back when offline."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, list[dict[str, Any]], str]] = {}
        self._lock = threading.Lock()

    def list_posts(self, *, user_id: int | None = None, limit: int | None = None) -> FetchResult:
        raw = self._fetch_resource("posts")
        posts = raw.data

        if user_id is not None:
            posts = [post for post in posts if post.get("userId") == user_id]

        if limit is not None:
            posts = posts[:limit]

        return FetchResult(data=posts, source=raw.source)

    def get_post(self, post_id: int) -> tuple[dict[str, Any] | None, str]:
        posts = self._fetch_resource("posts")
        for post in posts.data:
            if post.get("id") == post_id:
                return post, posts.source
        return None, posts.source

    def list_users(self) -> FetchResult:
        return self._fetch_resource("users")

    def _fetch_resource(self, resource: str) -> FetchResult:
        with self._lock:
            cached = self._cache.get(resource)
            if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
                return FetchResult(data=cached[1], source=cached[2])

        try:
            data = self._fetch_remote(resource)
            source = "jsonplaceholder"
        except URLError:
            data = self._fallback_data(resource)
            source = "fallback"

        with self._lock:
            self._cache[resource] = (time.time(), data, source)

        return FetchResult(data=data, source=source)

    def _fetch_remote(self, resource: str) -> list[dict[str, Any]]:
        request = Request(
            f"{UPSTREAM_BASE_URL}/{resource}",
            headers={"User-Agent": "rubens-portfolio-api/1.0"},
        )
        with urlopen(request, timeout=UPSTREAM_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
        if isinstance(payload, list):
            return payload
        return []

    @staticmethod
    def _fallback_data(resource: str) -> list[dict[str, Any]]:
        fallback = {
            "posts": [
                {
                    "userId": 1,
                    "id": 1,
                    "title": "fallback post",
                    "body": "Upstream indisponivel no momento.",
                }
            ],
            "users": [
                {
                    "id": 1,
                    "name": "Demo User",
                    "username": "demo",
                    "email": "demo@example.com",
                }
            ],
        }
        return fallback.get(resource, [])

"""HTTP server for the Python Public API project."""

from __future__ import annotations

import argparse
import json
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .client import JsonPlaceholderClient
from .config import DEFAULT_LIMIT, MAX_LIMIT


def _json_response(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status.value)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


class PortfolioApiHandler(BaseHTTPRequestHandler):
    """Routes incoming requests and serves JSON responses."""

    server_version = "RubensPythonAPI/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/health":
            self._handle_health()
            return
        if path == "/api/posts":
            self._handle_posts(parse_qs(parsed.query))
            return
        if path.startswith("/api/posts/"):
            self._handle_single_post(path)
            return
        if path == "/api/users":
            self._handle_users()
            return
        if path == "/api/info":
            self._handle_info()
            return

        _json_response(
            self,
            HTTPStatus.NOT_FOUND,
            {
                "success": False,
                "error": "Endpoint nao encontrado",
                "availableEndpoints": ["/health", "/api/info", "/api/posts", "/api/posts/{id}", "/api/users"],
            },
        )

    def _handle_health(self) -> None:
        uptime_seconds = int(time.time() - self.server.started_at)
        _json_response(
            self,
            HTTPStatus.OK,
            {
                "success": True,
                "status": "ok",
                "uptimeSeconds": uptime_seconds,
            },
        )

    def _handle_info(self) -> None:
        _json_response(
            self,
            HTTPStatus.OK,
            {
                "success": True,
                "service": "Python Public API",
                "description": "API em Python consumindo endpoint publico sem autenticacao.",
                "upstream": "https://jsonplaceholder.typicode.com",
            },
        )

    def _handle_posts(self, query: dict[str, list[str]]) -> None:
        try:
            user_id = self._optional_int(query.get("userId", [None])[0], field_name="userId")
            limit = self._optional_int(query.get("limit", [str(DEFAULT_LIMIT)])[0], field_name="limit")
            if limit is not None and limit > MAX_LIMIT:
                raise ValueError(f"limit deve ser <= {MAX_LIMIT}")
        except ValueError as error:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"success": False, "error": str(error)})
            return

        result = self.server.client.list_posts(user_id=user_id, limit=limit)
        _json_response(
            self,
            HTTPStatus.OK,
            {
                "success": True,
                "data": result.data,
                "meta": {
                    "count": len(result.data),
                    "source": result.source,
                },
            },
        )

    def _handle_single_post(self, path: str) -> None:
        post_id_segment = path.rsplit("/", 1)[-1]
        try:
            post_id = int(post_id_segment)
            if post_id <= 0:
                raise ValueError
        except ValueError:
            _json_response(self, HTTPStatus.BAD_REQUEST, {"success": False, "error": "ID invalido"})
            return

        post, source = self.server.client.get_post(post_id)
        if post is None:
            _json_response(self, HTTPStatus.NOT_FOUND, {"success": False, "error": "Post nao encontrado"})
            return

        _json_response(
            self,
            HTTPStatus.OK,
            {
                "success": True,
                "data": post,
                "meta": {"source": source},
            },
        )

    def _handle_users(self) -> None:
        result = self.server.client.list_users()
        _json_response(
            self,
            HTTPStatus.OK,
            {
                "success": True,
                "data": result.data,
                "meta": {
                    "count": len(result.data),
                    "source": result.source,
                },
            },
        )

    @staticmethod
    def _optional_int(value: str | None, *, field_name: str) -> int | None:
        if value in (None, ""):
            return None
        parsed = int(value)
        if parsed <= 0:
            raise ValueError(f"{field_name} deve ser inteiro positivo")
        return parsed

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


class PortfolioApiServer(ThreadingHTTPServer):
    """Threading HTTP server with runtime metadata."""

    def __init__(self, host: str, port: int, client: JsonPlaceholderClient | None = None) -> None:
        super().__init__((host, port), PortfolioApiHandler)
        self.client = client or JsonPlaceholderClient()
        self.started_at = time.time()


def create_server(host: str, port: int, client: JsonPlaceholderClient | None = None) -> PortfolioApiServer:
    return PortfolioApiServer(host, port, client=client)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Rubens Python Public API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = create_server(args.host, args.port)
    print(f"[python-public-api] running on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from app.client import FetchResult
from app.server import create_server


class FakeClient:
    def __init__(self) -> None:
        self._posts = [
            {"userId": 1, "id": 1, "title": "alpha", "body": "A"},
            {"userId": 1, "id": 2, "title": "beta", "body": "B"},
            {"userId": 2, "id": 3, "title": "gamma", "body": "C"},
        ]
        self._users = [{"id": 1, "name": "Rubens"}, {"id": 2, "name": "Equipe"}]

    def list_posts(self, *, user_id=None, limit=None):
        data = self._posts
        if user_id is not None:
            data = [post for post in data if post["userId"] == user_id]
        if limit is not None:
            data = data[:limit]
        return FetchResult(data=data, source="fake")

    def get_post(self, post_id):
        for post in self._posts:
            if post["id"] == post_id:
                return post, "fake"
        return None, "fake"

    def list_users(self):
        return FetchResult(data=self._users, source="fake")


class ApiServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server("127.0.0.1", 0, client=FakeClient())
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=1)

    def request_json(self, path: str):
        with urlopen(f"http://127.0.0.1:{self.port}{path}") as response:
            status = response.getcode()
            body = response.read().decode("utf-8")
        return status, json.loads(body)

    def request_error(self, path: str):
        with self.assertRaises(HTTPError) as ctx:
            urlopen(f"http://127.0.0.1:{self.port}{path}")
        return ctx.exception.code, json.loads(ctx.exception.read().decode("utf-8"))

    def test_health_endpoint(self):
        status, payload = self.request_json("/health")
        self.assertEqual(status, 200)
        self.assertTrue(payload["success"])

    def test_list_posts_default(self):
        status, payload = self.request_json("/api/posts")
        self.assertEqual(status, 200)
        self.assertEqual(payload["meta"]["count"], 3)

    def test_list_posts_filtered(self):
        status, payload = self.request_json("/api/posts?userId=1&limit=1")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["data"]), 1)
        self.assertEqual(payload["data"][0]["id"], 1)

    def test_single_post_not_found(self):
        status, payload = self.request_error("/api/posts/999")
        self.assertEqual(status, 404)
        self.assertFalse(payload["success"])

    def test_single_post_found(self):
        status, payload = self.request_json("/api/posts/2")
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"]["title"], "beta")

    def test_bad_query(self):
        status, payload = self.request_error("/api/posts?userId=abc")
        self.assertEqual(status, 400)
        self.assertIn("invalid literal", payload["error"])


if __name__ == "__main__":
    unittest.main()

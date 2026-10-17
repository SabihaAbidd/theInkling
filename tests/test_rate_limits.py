"""Behavior checks for Redis-backed API request limiting."""

import unittest

import app.web as web
from fastapi import HTTPException
from starlette.requests import Request


class FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    async def eval(self, script: str, key_count: int, key: str, seconds: int) -> int:
        del script, key_count, seconds
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]


def make_request(client_ip: str = "203.0.113.12") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": (client_ip, 12345),
            "scheme": "http",
        }
    )


def run_dependency(dependency, request: Request) -> None:
    """Run the fully synchronous mocked dependency coroutine to completion."""

    coroutine = dependency(request)
    try:
        coroutine.send(None)
    except StopIteration:
        return


class RateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_redis = web.redis_client
        self.redis = FakeRedis()
        web.redis_client = self.redis

    def tearDown(self) -> None:
        web.redis_client = self.previous_redis

    def test_request_limit_returns_retry_after_when_exceeded(self) -> None:
        dependency = web.redis_rate_limit(2, 60, "test-scope").dependency
        request = make_request()

        run_dependency(dependency, request)
        run_dependency(dependency, request)
        with self.assertRaises(HTTPException) as raised:
            run_dependency(dependency, request)

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.headers["Retry-After"], "60")
        self.assertIn("rate-limit:test-scope:203.0.113.12", self.redis.counts)

    def test_missing_redis_fails_closed(self) -> None:
        web.redis_client = None
        dependency = web.redis_rate_limit(5, 60, "test-scope").dependency

        with self.assertRaises(HTTPException) as raised:
            run_dependency(dependency, make_request())

        self.assertEqual(raised.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()

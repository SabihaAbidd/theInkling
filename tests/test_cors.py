"""Regression checks for the API's browser-origin allowlist."""

import os
import unittest
from unittest.mock import patch

from app.web import app, configured_cors_origins
from starlette.middleware.cors import CORSMiddleware


class CorsAllowlistTests(unittest.TestCase):
    def test_origins_come_only_from_the_configured_list(self) -> None:
        with patch.dict(
            os.environ,
            {"CORS_ORIGINS": "https://reader.example, https://staging.example"},
        ):
            self.assertEqual(
                configured_cors_origins(),
                ["https://reader.example", "https://staging.example"],
            )

    def test_credentialed_cors_does_not_use_wildcard_origin_patterns(self) -> None:
        cors = next(
            middleware
            for middleware in app.user_middleware
            if middleware.cls is CORSMiddleware
        )
        instance = CORSMiddleware(app, *cors.args, **cors.kwargs)

        self.assertIsNone(instance.allow_origin_regex)
        self.assertNotIn("https://untrusted-preview.vercel.app", instance.allow_origins)


if __name__ == "__main__":
    unittest.main()

"""Tests for OpenRouter response parsing and safe diagnostics."""

import unittest
from unittest.mock import patch

from core.openrouter_client import OpenRouterClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class OpenRouterClientTests(unittest.TestCase):
    def test_text_parts_are_combined(self):
        payload = {
            "model": "test/model",
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": [
                    {"type": "text", "text": "first"},
                    {"type": "output_text", "text": " second"},
                ]},
            }],
            "usage": {},
        }
        with patch("core.openrouter_client.requests.post", return_value=FakeResponse(payload)):
            result = OpenRouterClient(api_key="test-key").chat(
                model="test/model",
                messages=[{"role": "user", "content": "hello"}],
            )
        self.assertEqual(result.content, "first second")

    def test_empty_content_reports_safe_diagnostics(self):
        payload = {
            "model": "served/model",
            "choices": [{"finish_reason": "length", "message": {"content": None}}],
            "usage": {},
        }
        with patch("core.openrouter_client.requests.post", return_value=FakeResponse(payload)):
            with self.assertRaisesRegex(
                RuntimeError,
                r"served model: served/model; finish reason: length",
            ):
                OpenRouterClient(api_key="secret-never-print-this").chat(
                    model="requested/model",
                    messages=[{"role": "user", "content": "hello"}],
                )


if __name__ == "__main__":
    unittest.main()

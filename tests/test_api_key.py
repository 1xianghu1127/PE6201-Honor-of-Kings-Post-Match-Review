"""Tests for secure, process-only OpenRouter key handling."""

import os
import unittest
from unittest.mock import patch

from core.openrouter_client import prompt_for_openrouter_api_key


class ApiKeyPromptTests(unittest.TestCase):
    def test_existing_process_key_is_reused_without_prompt(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "runtime-key"}, clear=False):
            with patch("core.openrouter_client.getpass.getpass") as prompt:
                self.assertEqual(prompt_for_openrouter_api_key(), "runtime-key")
                prompt.assert_not_called()

    def test_terminal_key_is_kept_in_process_memory(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("core.openrouter_client.sys.stdin.isatty", return_value=True):
                with patch("core.openrouter_client.getpass.getpass", return_value="entered-key"):
                    self.assertEqual(prompt_for_openrouter_api_key(), "entered-key")
                    self.assertEqual(os.environ["OPENROUTER_API_KEY"], "entered-key")

    def test_empty_terminal_key_is_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("core.openrouter_client.sys.stdin.isatty", return_value=True):
                with patch("core.openrouter_client.getpass.getpass", return_value=""):
                    with self.assertRaisesRegex(RuntimeError, "cannot be empty"):
                        prompt_for_openrouter_api_key()


if __name__ == "__main__":
    unittest.main()

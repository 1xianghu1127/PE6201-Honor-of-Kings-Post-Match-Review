"""Streamlit smoke tests for page loading and the manual baseline path."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class AppSmokeTests(unittest.TestCase):
    def test_app_loads_without_exception(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path)).run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.title[0].value, "Honor of Kings AI Post-Match Review Assistant")
        self.assertEqual(len(app.file_uploader), 0)

    def test_manual_baseline_flow(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path)).run(timeout=20)
        next(button for button in app.button if button.label == "Use this match data").click().run(timeout=20)
        app.radio[0].set_value("Rule baseline").run(timeout=20)
        next(button for button in app.button if button.label == "Analyse match").click().run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Rule-based baseline", [item.value for item in app.subheader])


if __name__ == "__main__":
    unittest.main()

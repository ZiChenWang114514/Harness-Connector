import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "dsh_session.py"
SPEC = importlib.util.spec_from_file_location("dsh_session", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DshSessionTests(unittest.TestCase):
    def test_selected_model(self):
        text = """ui-theme:\n  preference: system\nagent-default-model:\n  provider: deepseek-official\n  model: deepseek-v4-flash\n  reasoningEffort: max\n"""
        self.assertEqual(
            MODULE.selected_model(text),
            ("deepseek-official", "deepseek-v4-flash", "max"),
        )

    def test_missing_model_block(self):
        self.assertEqual(MODULE.selected_model("ui-theme:\n  preference: system\n"), (None, None, None))

    def test_replace_selected_model(self):
        text = "agent-default-model:\n  provider: deepseek-official\n  model: old\n"
        updated = MODULE.replace_selected_model(text, "deepseek-v4-pro")
        self.assertIn("model: deepseek-v4-pro", updated)
        self.assertNotIn("model: old", updated)

    def test_any_to_payload_extracts_one_session(self):
        payload = MODULE.any_to_payload(
            {"ok": True, "new_session_entries": ["session-1"]}, "invoke"
        )
        self.assertEqual(payload["target"], "deepseek-harness")
        self.assertEqual(payload["session_id"], "session-1")

    def test_success_without_session_is_explicit(self):
        payload = MODULE.any_to_payload(
            {"ok": True, "new_session_entries": [], "response": "done"}, "invoke"
        )
        self.assertIsNone(payload["session_id"])
        self.assertIn("headless_session_not_persisted", payload["warnings"])


if __name__ == "__main__":
    unittest.main()

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "codex_session.py"
SPEC = importlib.util.spec_from_file_location("codex_session", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CodexSessionTests(unittest.TestCase):
    def test_parse_jsonl_events(self):
        text = "\n".join([
            '{"type":"thread.started","thread_id":"thread-1"}',
            '{"type":"item.completed","item":{"type":"agent_message","text":"done","model":"gpt-test"}}',
        ])
        result = MODULE.parse_events(text)
        self.assertEqual(result["session_id"], "thread-1")
        self.assertEqual(result["message"], "done")
        self.assertEqual(result["actual_model"], "gpt-test")

    def test_envelope_has_shared_fields(self):
        result = MODULE.envelope("status", ok=True)
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["target"], "codex")
        self.assertIsNone(result["error"])


if __name__ == "__main__":
    unittest.main()

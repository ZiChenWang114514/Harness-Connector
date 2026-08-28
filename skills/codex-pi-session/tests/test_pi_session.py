import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "pi_session.py"
SPEC = importlib.util.spec_from_file_location("pi_session", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PiSessionTests(unittest.TestCase):
    def test_parse_jsonl_events(self):
        text = "\n".join([
            '{"type":"session","id":"session-1","cwd":"C:\\\\repo"}',
            '{"type":"message_end","message":{"role":"assistant","provider":"openai-codex","model":"gpt-5.6-luna","content":[{"type":"text","text":"done"}]}}',
        ])
        result = MODULE.parse_events(text)
        self.assertEqual(result["session_id"], "session-1")
        self.assertEqual(result["message"], "done")
        self.assertEqual(result["provider"], "openai-codex")
        self.assertEqual(result["actual_model"], "gpt-5.6-luna")

    def test_envelope_has_shared_fields(self):
        result = MODULE.envelope("status", ok=True)
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["target"], "pi")
        self.assertIsNone(result["error"])

    def test_pi_command_uses_exact_session(self):
        args = type("Args", (), {
            "provider": "openai-codex", "model": "gpt-5.6-luna",
            "thinking": "low", "session_dir": "sessions", "command": "resume",
            "session_id": "exact-id", "isolated": True, "no_tools": True,
        })()
        original = MODULE.executable
        MODULE.executable = lambda: "pi"
        try:
            command = MODULE.pi_command(args, "continue")
        finally:
            MODULE.executable = original
        self.assertIn("--session-id", command)
        self.assertEqual(command[command.index("--session-id") + 1], "exact-id")
        self.assertNotIn("--fork", command)


if __name__ == "__main__":
    unittest.main()

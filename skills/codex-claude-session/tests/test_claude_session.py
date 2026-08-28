import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "claude_session.py"
SPEC = importlib.util.spec_from_file_location("claude_session", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ClaudeSessionTests(unittest.TestCase):
    def test_deepseek_environment_uses_child_mapping(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-secret"}, clear=False):
            env, model = MODULE.provider_environment("deepseek", "flash")
        self.assertEqual(model, "deepseek-v4-flash")
        self.assertEqual(env["ANTHROPIC_BASE_URL"], MODULE.DEEPSEEK_BASE_URL)
        self.assertEqual(env["ANTHROPIC_AUTH_TOKEN"], "test-secret")

    def test_official_environment_removes_provider_override(self):
        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://example.test", "ANTHROPIC_AUTH_TOKEN": "x"}, clear=False):
            env, model = MODULE.provider_environment("official")
        self.assertNotIn("ANTHROPIC_BASE_URL", env)
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", env)
        self.assertIsNone(model)

    def test_parse_json_response(self):
        result = MODULE.parse_response('{"session_id":"s1","result":"ok","model":"m1"}')
        self.assertEqual(result["session_id"], "s1")
        self.assertEqual(result["actual_model"], "m1")

    def test_parse_model_usage(self):
        raw = '{"result":"ok","modelUsage":{"deepseek-v4-flash":{"canonicalModel":"deepseek-v4-flash"}}}'
        self.assertEqual(MODULE.parse_response(raw)["actual_model"], "deepseek-v4-flash")


if __name__ == "__main__":
    unittest.main()

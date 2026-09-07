import importlib.util
from pathlib import Path
import unittest
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "codex_session.py"
SPEC = importlib.util.spec_from_file_location("codex_session", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CodexSessionTests(unittest.TestCase):
    def test_windows_candidates_prefer_native_executable(self):
        def fake_which(name):
            return {"codex.exe": r"C:\\Native\\codex.exe",
                    "codex": r"C:\\npm\\codex.CMD"}.get(name)

        with mock.patch.object(MODULE.os, "name", "nt"), \
                mock.patch.object(MODULE.shutil, "which", side_effect=fake_which):
            self.assertEqual(MODULE.executable_candidates(), [
                r"C:\\Native\\codex.exe", r"C:\\npm\\codex.CMD"])

    def test_resolver_falls_back_after_broken_launcher(self):
        broken = MODULE.subprocess.CompletedProcess(["bad"], 1, "", "missing package")
        good = MODULE.subprocess.CompletedProcess(["good"], 0, "codex-cli 1.2.3", "")
        with mock.patch.object(MODULE, "executable_candidates", return_value=["bad", "good"]), \
                mock.patch.object(MODULE, "run_text", side_effect=[broken, good]):
            executable, diagnostics = MODULE.resolve_executable()
        self.assertEqual(executable, "good")
        self.assertFalse(diagnostics[0]["ok"])
        self.assertTrue(diagnostics[1]["ok"])

    def test_status_accepts_login_message_from_stderr(self):
        version = MODULE.subprocess.CompletedProcess(["codex", "--version"], 0,
                                                     "codex-cli 1.2.3\n", "")
        login = MODULE.subprocess.CompletedProcess(["codex", "login", "status"], 0,
                                                   "", "Logged in using ChatGPT\n")
        help_result = MODULE.subprocess.CompletedProcess(
            ["codex", "exec", "--help"], 0,
            "--json --model --cd --output-schema --ephemeral", "")
        with mock.patch.object(MODULE, "resolve_executable", return_value=("codex", [])), \
                mock.patch.object(MODULE, "run_text", side_effect=[version, login, help_result]), \
                mock.patch.object(MODULE, "config_defaults", return_value={
                    "model": None, "reasoning_effort": None}):
            payload = MODULE.status_payload()
        self.assertTrue(payload["logged_in"])
        self.assertEqual(payload["login_status"], "Logged in using ChatGPT")

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

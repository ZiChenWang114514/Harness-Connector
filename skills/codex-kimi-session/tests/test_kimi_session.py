import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "kimi_session.py"
SPEC = importlib.util.spec_from_file_location("kimi_session", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class KimiSessionTests(unittest.TestCase):
    def test_any_to_payload_preserves_model(self):
        payload = MODULE.any_to_payload(
            {"ok": True, "actual_model": "kimi-code/k3"}, "invoke"
        )
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["target"], "kimi-code")
        self.assertEqual(payload["actual_model"], "kimi-code/k3")


if __name__ == "__main__":
    unittest.main()

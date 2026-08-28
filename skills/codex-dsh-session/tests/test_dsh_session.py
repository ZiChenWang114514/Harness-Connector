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


if __name__ == "__main__":
    unittest.main()

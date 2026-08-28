import importlib.util
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "zcode_session.py"
SPEC = importlib.util.spec_from_file_location("zcode_session", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ZCodeSessionTests(unittest.TestCase):
    def test_catalog_detects_multimodal_model(self):
        config = {"provider": {"zai": {"models": {
            "glm-text": {"name": "Text"},
            "glm-vision": {"supportsImages": True},
        }}}}
        models, multimodal = MODULE.catalog(config)
        self.assertEqual(models, ["zai/glm-text", "zai/glm-vision"])
        self.assertEqual(multimodal, ["zai/glm-vision"])

    def test_empty_config_has_no_credentials(self):
        self.assertFalse(MODULE.configured({}))

    def test_select_main_model(self):
        config = {"model": {"main": "old", "lite": "lite"}}
        selected = MODULE.select_main_model(config, "zai/glm-5.3")
        self.assertEqual(selected["model"]["main"], "zai/glm-5.3")
        self.assertEqual(selected["model"]["lite"], "lite")

    def test_any_to_payload(self):
        payload = MODULE.any_to_payload({"ok": True, "main_model": "zai/glm-5.3"}, "status")
        self.assertEqual(payload["target"], "zcode")
        self.assertEqual(payload["requested_model"], "zai/glm-5.3")
        self.assertEqual(payload["warnings"], [])

    def test_windows_command_uses_node_entry_point(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable = root / "zcode.cmd"
            entry = root / "node_modules" / "zcode-app-cli" / "bin" / "zcode.js"
            entry.parent.mkdir(parents=True)
            executable.touch()
            entry.touch()
            with mock.patch.object(MODULE.os, "name", "nt"), mock.patch.object(
                MODULE.shutil, "which", return_value="C:/node.exe"
            ):
                self.assertEqual(
                    MODULE.zcode_command(str(executable)),
                    ["C:/node.exe", str(entry)],
                )

    def test_model_usage_reads_isolated_database(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / ".zcode"
            database = home / "cli" / "db" / "db.sqlite"
            database.parent.mkdir(parents=True)
            with closing(sqlite3.connect(database)) as connection:
                connection.execute(
                    """create table model_usage (
                    session_id text, provider_id text, model_id text, status text,
                    retry_count integer, error_type text, error_code text, started_at integer
                    )"""
                )
                connection.execute(
                    "insert into model_usage values (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("sess_test", "bigmodel", "GLM-5-Turbo", "completed", 0, None, None, 1),
                )
                connection.commit()
            usage = MODULE.model_usage("sess_test", {**os.environ, "ZCODE_HOME": str(home)})
            self.assertEqual(usage["actual_model"], "bigmodel/GLM-5-Turbo")
            self.assertEqual(usage["model_status"], "completed")


if __name__ == "__main__":
    unittest.main()

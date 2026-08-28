from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AggregateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads((ROOT / "catalog" / "skills.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))

    def test_manifest_and_catalog_identity(self) -> None:
        self.assertEqual("harness-connector", self.manifest["name"])
        self.assertEqual("./skills/", self.manifest["skills"])
        self.assertEqual(self.manifest["name"], self.catalog["plugin"])

    def test_exactly_eight_unique_skills(self) -> None:
        skill_ids = [item["skill_id"] for item in self.catalog["skills"]]
        self.assertEqual(8, len(skill_ids))
        self.assertEqual(8, len(set(skill_ids)))
        directories = sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir())
        self.assertEqual(sorted(skill_ids), directories)

    def test_complete_independent_snapshots(self) -> None:
        for item in self.catalog["skills"]:
            with self.subTest(skill=item["skill_id"]):
                skill_root = ROOT / "skills" / item["skill_id"]
                for relative in ["README.md", "README.zh-CN.md", "SKILL.md", "agents/openai.yaml", item["main_script"]]:
                    self.assertTrue((skill_root / relative).is_file(), relative)
                self.assertTrue((skill_root / "references").is_dir())
                self.assertTrue((skill_root / "tests").is_dir())

    def test_main_scripts_parse_help_in_nested_paths(self) -> None:
        for item in self.catalog["skills"]:
            script = ROOT / "skills" / item["skill_id"] / item["main_script"]
            with self.subTest(skill=item["skill_id"]):
                result = subprocess.run(
                    [sys.executable, str(script), "--help"],
                    cwd=script.parent.parent,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertIn("usage", result.stdout.lower())

    def test_no_generated_bytecode(self) -> None:
        result = subprocess.run(
            ["git", "ls-files", "*.pyc"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual("", result.stdout.strip())


if __name__ == "__main__":
    unittest.main()

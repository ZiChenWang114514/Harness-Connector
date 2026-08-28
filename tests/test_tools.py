from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_tool(name: str):
    path = ROOT / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ToolTests(unittest.TestCase):
    def test_catalog_render_is_complete(self) -> None:
        tool = load_tool("generate_catalog")
        catalog = json.loads((ROOT / "catalog" / "skills.json").read_text(encoding="utf-8"))
        matrix = tool.render_matrix(catalog)
        self.assertEqual(8, matrix.count("| [`$"))
        for item in catalog["skills"]:
            self.assertIn(item["skill_id"], matrix)

    def test_matrix_replacement_preserves_surrounding_text(self) -> None:
        tool = load_tool("generate_catalog")
        text = "before\n<!-- skill-matrix:start -->\nold\n<!-- skill-matrix:end -->\nafter\n"
        actual = tool.replace_section(text, "new")
        self.assertEqual("before\n<!-- skill-matrix:start -->\nnew\n<!-- skill-matrix:end -->\nafter\n", actual)

    def test_sync_copy_ignores_repository_metadata(self) -> None:
        tool = load_tool("sync_from_sources")
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source"
            source.mkdir()
            (source / ".git").mkdir()
            (source / ".git" / "config").write_text("private metadata", encoding="utf-8")
            (source / "SKILL.md").write_text("content", encoding="utf-8")
            target = tool.SKILLS_ROOT / "__test-sync-copy__"
            try:
                tool.copy_snapshot(source, target)
                self.assertTrue((target / "SKILL.md").is_file())
                self.assertFalse((target / ".git").exists())
            finally:
                if target.exists():
                    import shutil

                    shutil.rmtree(target)


if __name__ == "__main__":
    unittest.main()

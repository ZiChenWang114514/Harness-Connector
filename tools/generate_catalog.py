#!/usr/bin/env python3
"""Generate and verify the public skill matrix from catalog/skills.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "skills.json"
TARGETS = [ROOT / "README.md", ROOT / "README.zh-CN.md", ROOT / "docs" / "skill-catalog.md"]
START = "<!-- skill-matrix:start -->"
END = "<!-- skill-matrix:end -->"


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def render_matrix(catalog: dict) -> str:
    lines = [
        "| Skill | Target Harness | Commands | Source | Verification |",
        "|---|---|---|---|---|",
    ]
    for item in catalog["skills"]:
        repository = item["source_repository"]
        repo_name = repository.split("/", 1)[1]
        source = f"[{repo_name}](https://github.com/{repository}) @ `{item['source_commit'][:8]}`"
        commands = ", ".join(f"`{command}`" for command in item["commands"])
        status = item["verification"]["status"]
        lines.append(
            f"| [`${item['skill_id']}`](skills/{item['skill_id']}/) | {item['target']} | {commands} | {source} | `{status}` |"
        )
    return "\n".join(lines)


def replace_section(text: str, matrix: str) -> str:
    start = text.find(START)
    end = text.find(END)
    if start < 0 or end < start:
        raise ValueError("skill matrix markers are missing or out of order")
    return text[: start + len(START)] + "\n" + matrix + "\n" + text[end:]


def expected_content(path: Path, matrix: str) -> str:
    return replace_section(path.read_text(encoding="utf-8"), matrix)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Update generated matrices")
    mode.add_argument("--check", action="store_true", help="Verify generated matrices")
    args = parser.parse_args()

    matrix = render_matrix(load_catalog())
    stale: list[str] = []
    for path in TARGETS:
        current = path.read_text(encoding="utf-8")
        expected = replace_section(current, matrix)
        if current == expected:
            continue
        if args.write:
            path.write_text(expected, encoding="utf-8", newline="\n")
        else:
            stale.append(path.relative_to(ROOT).as_posix())

    if stale:
        print(json.dumps({"ok": False, "stale": stale}, indent=2))
        return 1
    print(json.dumps({"ok": True, "updated": bool(args.write), "targets": [p.relative_to(ROOT).as_posix() for p in TARGETS]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

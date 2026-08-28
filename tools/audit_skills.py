#!/usr/bin/env python3
"""Audit the Harness Connector plugin and its eight independent skills."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog" / "skills.json"
MANIFEST_PATH = ROOT / ".codex-plugin" / "plugin.json"
TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt", ".ps1", ".svg"}
REQUIRED_ROOT_FILES = {
    "README.md",
    "README.zh-CN.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "pyproject.toml",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def skill_frontmatter_name(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    match = re.search(r"(?m)^name:\s*['\"]?([^'\"\r\n]+)", text[3:end])
    return match.group(1).strip() if match else None


def scan_public_files() -> list[str]:
    errors: list[str] = []
    mistaken_brand = re.compile("I" + r"\s+need\s+to", re.IGNORECASE)
    secret_patterns = [
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ]
    personal_path = ("C:" + "\\" + "Users" + "\\" + "11234").lower()

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != "LICENSE":
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        if mistaken_brand.search(text):
            errors.append(f"mistaken brand phrase found: {rel}")
        if personal_path in text.lower():
            errors.append(f"personal absolute path found: {rel}")
        for pattern in secret_patterns:
            if pattern.search(text):
                errors.append(f"possible credential found: {rel}")
                break
    return errors


def audit() -> list[str]:
    errors: list[str] = []
    for name in sorted(REQUIRED_ROOT_FILES):
        if not (ROOT / name).is_file():
            errors.append(f"missing root file: {name}")

    catalog = load_json(CATALOG_PATH)
    manifest = load_json(MANIFEST_PATH)
    records = catalog.get("skills", [])
    expected_ids = [record.get("skill_id") for record in records]
    actual_ids = sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir())

    if catalog.get("plugin") != manifest.get("name"):
        errors.append("catalog plugin name does not match plugin manifest")
    if manifest.get("skills") != "./skills/":
        errors.append("plugin manifest must declare only ./skills/")
    if len(expected_ids) != 8 or len(set(expected_ids)) != 8:
        errors.append("catalog must contain eight unique skill IDs")
    if sorted(expected_ids) != actual_ids:
        errors.append(f"catalog and skill directories differ: catalog={sorted(expected_ids)}, directories={actual_ids}")

    frontmatter_names: list[str] = []
    for record in records:
        skill_id = record.get("skill_id")
        if not isinstance(skill_id, str):
            errors.append("catalog contains an invalid skill ID")
            continue
        skill_root = ROOT / "skills" / skill_id
        required = [
            skill_root / "README.md",
            skill_root / "README.zh-CN.md",
            skill_root / "SKILL.md",
            skill_root / "agents" / "openai.yaml",
            skill_root / record.get("main_script", ""),
        ]
        for path in required:
            if not path.is_file():
                errors.append(f"{skill_id}: missing {path.relative_to(skill_root).as_posix()}")
        if not (skill_root / "references").is_dir():
            errors.append(f"{skill_id}: missing references directory")
        name = skill_frontmatter_name(skill_root / "SKILL.md") if (skill_root / "SKILL.md").is_file() else None
        if name != skill_id:
            errors.append(f"{skill_id}: SKILL.md frontmatter name is {name!r}")
        elif name:
            frontmatter_names.append(name)
        commit = record.get("source_commit", "")
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            errors.append(f"{skill_id}: invalid source commit")
        if not record.get("source_repository", "").startswith("ZiChenWang114514/"):
            errors.append(f"{skill_id}: invalid source repository")
        if not record.get("commands"):
            errors.append(f"{skill_id}: command list is empty")

    if len(frontmatter_names) != len(set(frontmatter_names)):
        errors.append("SKILL.md frontmatter names are not unique")
    if list(ROOT.rglob("*.pyc")):
        errors.append("generated Python bytecode is present")
    errors.extend(scan_public_files())
    return errors


def main() -> int:
    errors = audit()
    payload = {"ok": not errors, "skill_count": 8, "errors": errors}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

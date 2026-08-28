#!/usr/bin/env python3
"""Check or explicitly refresh one skill snapshot from its public source."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
CATALOG_PATH = ROOT / "catalog" / "skills.json"


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def remote_main(repository: str) -> str:
    url = f"https://github.com/{repository}.git"
    result = subprocess.run(
        ["git", "ls-remote", url, "refs/heads/main"],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    line = result.stdout.strip()
    if not line:
        raise RuntimeError(f"main branch not found for {repository}")
    return line.split()[0]


def check_sources(catalog: dict) -> list[dict]:
    results = []
    for item in catalog["skills"]:
        current = remote_main(item["source_repository"])
        results.append(
            {
                "skill_id": item["skill_id"],
                "recorded_commit": item["source_commit"],
                "remote_commit": current,
                "up_to_date": current == item["source_commit"],
            }
        )
    return results


def copy_snapshot(source: Path, target: Path) -> None:
    if target.parent.resolve() != SKILLS_ROOT.resolve():
        raise RuntimeError("refusing to update a path outside skills/")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache"),
    )


def apply_source(catalog: dict, skill_id: str) -> dict:
    record = next((item for item in catalog["skills"] if item["skill_id"] == skill_id), None)
    if record is None:
        raise ValueError(f"unknown skill: {skill_id}")
    repository = record["source_repository"]
    with tempfile.TemporaryDirectory(prefix="harness-connector-") as temp_dir:
        checkout = Path(temp_dir) / "source"
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", "--branch", "main", f"https://github.com/{repository}.git", str(checkout)],
            check=True,
            timeout=120,
        )
        commit = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        copy_snapshot(checkout, SKILLS_ROOT / skill_id)
    record["source_commit"] = commit
    record["verification"] = {
        "status": "static-after-sync",
        "summary": "Refreshed from public main; real-call verification has not been repeated.",
    }
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    subprocess.run([sys.executable, str(ROOT / "tools" / "generate_catalog.py"), "--write"], check=True)
    return {"skill_id": skill_id, "repository": repository, "source_commit": commit}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Compare recorded commits with public main")
    mode.add_argument("--apply", action="store_true", help="Refresh one collection snapshot from public main")
    parser.add_argument("--skill", help="Skill ID required with --apply")
    args = parser.parse_args()
    if args.apply and not args.skill:
        parser.error("--apply requires --skill")

    try:
        catalog = load_catalog()
        if args.check:
            results = check_sources(catalog)
            print(json.dumps({"ok": True, "sources": results}, indent=2))
        else:
            result = apply_source(catalog, args.skill)
            print(json.dumps({"ok": True, "updated": result}, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

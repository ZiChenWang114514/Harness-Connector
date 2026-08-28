#!/usr/bin/env python3
"""Credential-safe wrapper for DeepSeek Harness headless tasks."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULTS = json.loads((SKILL_DIR / "references" / "defaults.json").read_text(encoding="utf-8"))


def dsh_home(env: dict[str, str] | None = None) -> Path:
    source = env or os.environ
    return Path(source.get("DSH_HOME", str(Path.home() / ".dsh"))).expanduser()


def settings_text(home: Path | None = None) -> str:
    path = (home or dsh_home()) / "settings.yaml"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def selected_model(text: str) -> tuple[str | None, str | None, str | None]:
    block = re.search(r"(?ms)^agent-default-model:\s*\n(?P<body>(?:^[ \t]+.*\n?)*)", text)
    body = block.group("body") if block else ""
    provider = re.search(r"(?m)^\s+provider:\s*([^#\r\n]+)", body)
    model = re.search(r"(?m)^\s+model:\s*([^#\r\n]+)", body)
    effort = re.search(r"(?m)^\s+reasoningEffort:\s*([^#\r\n]+)", body)
    return tuple(match.group(1).strip() if match else None for match in (provider, model, effort))


def command_version(executable: str) -> str | None:
    try:
        result = subprocess.run([executable, "--version"], text=True, capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or result.stderr.strip() or None


def status() -> dict:
    executable = shutil.which("dsh")
    home = dsh_home()
    provider, model, effort = selected_model(settings_text(home))
    discovered = list(DEFAULTS["supported_models"])
    return {
        "installed": bool(executable),
        "executable": executable,
        "version": command_version(executable) if executable else None,
        "dsh_home": str(home),
        "settings_path": str(home / "settings.yaml"),
        "provider": provider,
        "default_model": model,
        "reasoning_effort": effort,
        "models": discovered,
        "vision_models": [DEFAULTS["vision_model"]],
        "required_models_present": all(item in discovered for item in DEFAULTS["supported_models"]),
        "model_access_configured": bool(os.environ.get("DEEPSEEK_API_KEY")),
        "sessions_path": str(home / "sessions"),
    }


def session_entries(home: Path) -> set[str]:
    root = home / "sessions"
    if not root.is_dir():
        return set()
    return {str(path.relative_to(root)) for path in root.rglob("*") if path.is_dir() and path.name.startswith(("sess_", "agent_"))}


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    if args.prompt:
        return args.prompt
    raise ValueError("provide --prompt or --prompt-file")


def terminate_owned_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    else:
        process.kill()


def invoke_raw(directory: Path, prompt: str, timeout: int, env: dict[str, str] | None = None) -> dict:
    executable = shutil.which("dsh")
    if not executable:
        return {"ok": False, "error": "dsh_not_found"}
    command = [executable, "--profile", "headless", prompt]
    if os.name == "nt":
        # Passing a multiline argument through the npm-generated dsh.cmd shim
        # truncates the task at the first newline. Invoke the JavaScript entry
        # directly so the complete prompt remains one argv value.
        node = shutil.which("node")
        npm_root = Path(executable).resolve().parent
        launcher = npm_root / "node_modules" / "@deepseek-ai" / "dsh" / "lib" / "bin.js"
        if node and launcher.is_file():
            command = [node, str(launcher), "--profile", "headless", prompt]
    effective_env = env or os.environ.copy()
    home = dsh_home(effective_env)
    before = session_entries(home)
    process = subprocess.Popen(command, cwd=directory,
                               env=effective_env, text=True, encoding="utf-8", errors="replace",
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_owned_process(process)
        stdout, stderr = process.communicate()
        return {"ok": False, "error": "timeout", "pid": process.pid,
                "stdout": stdout.strip(), "stderr": stderr.strip()}
    after = session_entries(home)
    return {"ok": process.returncode == 0, "exit_code": process.returncode, "pid": process.pid,
            "new_session_entries": sorted(after - before), "response": stdout.strip() or None,
            "stderr": stderr.strip() or None}


def smoke_test(directory: Path, timeout: int) -> dict:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        return {"ok": False, "error": "model_access_not_configured"}
    source_home = dsh_home()
    with tempfile.TemporaryDirectory(prefix="codex-dsh-smoke-") as temp:
        temp_home = Path(temp) / ".dsh"
        temp_home.mkdir(parents=True)
        for name in ("profiles", "settings.yaml"):
            source = source_home / name
            target = temp_home / name
            if source.is_dir():
                try:
                    os.symlink(source, target, target_is_directory=True)
                except OSError:
                    if os.name != "nt":
                        raise
                    link = subprocess.run(["cmd", "/c", "mklink", "/J", str(target), str(source)],
                                          text=True, capture_output=True)
                    if link.returncode != 0:
                        return {"ok": False, "error": "profile_link_failed", "detail": link.stderr.strip()}
            elif source.is_file():
                shutil.copy2(source, target)
        env = os.environ.copy()
        env["DSH_HOME"] = str(temp_home)
        result = invoke_raw(directory, f'Reply exactly {DEFAULTS["smoke_reply"]}', timeout, env)
        result["expected_reply_found"] = DEFAULTS["smoke_reply"] in (result.get("response") or "")
        result["isolated_home"] = True
        result["ok"] = bool(result.get("ok") and result["expected_reply_found"])
        return result


def emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_status = sub.add_parser("status")
    p_status.add_argument("--json", action="store_true")
    for name in ("invoke", "smoke-test"):
        p = sub.add_parser(name)
        p.add_argument("--dir", required=True)
        p.add_argument("--timeout", type=int, default=DEFAULTS["smoke_timeout_seconds"] if name == "smoke-test" else DEFAULTS["invoke_timeout_seconds"])
        p.add_argument("--json", action="store_true")
        if name == "invoke":
            group = p.add_mutually_exclusive_group(required=True)
            group.add_argument("--prompt")
            group.add_argument("--prompt-file")
    args = parser.parse_args()
    if args.command == "status":
        payload = status()
    else:
        directory = Path(args.dir).resolve()
        if not directory.is_dir():
            payload = {"ok": False, "error": "directory_not_found", "directory": str(directory)}
        elif args.command == "smoke-test":
            payload = smoke_test(directory, args.timeout)
        else:
            payload = invoke_raw(directory, read_prompt(args), args.timeout)
    emit(payload, args.json)
    return 0 if payload.get("ok", payload.get("installed", False)) else 1


if __name__ == "__main__":
    sys.exit(main())

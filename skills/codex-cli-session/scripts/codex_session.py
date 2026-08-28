#!/usr/bin/env python3
"""Run, resume, fork, and verify Codex CLI sessions from any harness."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any


SCHEMA_VERSION = 1
TARGET = "codex"


def executable() -> str:
    value = shutil.which("codex")
    if not value:
        raise RuntimeError("codex_not_found")
    return value


def run_text(command: list[str], *, cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, encoding="utf-8", errors="replace",
                          capture_output=True, timeout=timeout, check=False)


def config_defaults() -> dict[str, Any]:
    path = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml"
    if not path.is_file():
        return {"path": str(path), "model": None, "reasoning_effort": None}
    try:
        import tomllib
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"path": str(path), "model": None, "reasoning_effort": None}
    return {
        "path": str(path),
        "model": data.get("model"),
        "reasoning_effort": data.get("model_reasoning_effort"),
    }


def envelope(command: str, *, ok: bool, provider: str = "openai", workdir: str | None = None,
             session_id: str | None = None, requested_model: str | None = None,
             actual_model: str | None = None, result: Any = None,
             warnings: list[str] | None = None, error: Any = None, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "ok": ok,
        "target": TARGET,
        "command": command,
        "provider": provider,
        "workdir": workdir,
        "session_id": session_id,
        "requested_model": requested_model,
        "actual_model": actual_model,
        "result": result,
        "warnings": warnings or [],
        "error": error,
    }
    payload.update(extra)
    return payload


def parse_events(stdout: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    messages: list[str] = []
    session_id = None
    actual_model = None
    for raw in stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        events.append(event)
        session_id = session_id or event.get("thread_id") or event.get("session_id")
        if event.get("type") == "thread.started":
            session_id = event.get("thread_id") or session_id
        item = event.get("item")
        if isinstance(item, dict):
            actual_model = item.get("model") or actual_model
            if item.get("type") == "agent_message" and item.get("text"):
                messages.append(str(item["text"]))
        actual_model = event.get("model") or actual_model
    return {
        "events": events,
        "session_id": session_id,
        "actual_model": actual_model,
        "message": messages[-1] if messages else None,
    }


def run_jsonl(command: list[str], *, cwd: Path | None, timeout: int) -> dict[str, Any]:
    try:
        process = run_text(command, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "exit_code": None, "stdout": exc.stdout or "", "stderr": exc.stderr or "",
                "error": "timeout"}
    parsed = parse_events(process.stdout)
    return {
        "ok": process.returncode == 0 and bool(parsed["message"]),
        "exit_code": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr.strip() or None,
        "error": None if process.returncode == 0 else "codex_command_failed",
        **parsed,
    }


def status_payload() -> dict[str, Any]:
    exe = executable()
    version = run_text([exe, "--version"])
    login = run_text([exe, "login", "status"])
    help_result = run_text([exe, "exec", "--help"])
    defaults = config_defaults()
    required = ["--json", "--model", "--cd", "--output-schema", "--ephemeral"]
    support = {flag: flag in help_result.stdout for flag in required}
    ok = version.returncode == 0 and login.returncode == 0 and all(support.values())
    return envelope(
        "status", ok=ok, requested_model=defaults["model"],
        executable=exe, version=version.stdout.strip(), login_status=login.stdout.strip(),
        logged_in=login.returncode == 0, reasoning_effort=defaults["reasoning_effort"],
        required_flag_support=support,
    )


def prompt_text(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    return args.prompt


def execute_payload(args: argparse.Namespace) -> dict[str, Any]:
    exe = executable()
    workdir = Path(args.workdir).resolve() if getattr(args, "workdir", None) else None
    if workdir and not workdir.is_dir():
        return envelope(args.command, ok=False, workdir=str(workdir), error="directory_not_found")
    prompt = prompt_text(args)
    command = [exe, "exec"]
    if args.command == "invoke":
        command += ["--json", "--cd", str(workdir), "--sandbox", args.sandbox]
        if args.skip_git_repo_check:
            command.append("--skip-git-repo-check")
        if args.ephemeral:
            command.append("--ephemeral")
    else:
        command += [args.command, "--json"]
    if args.model:
        command += ["--model", args.model]
    if args.command in {"resume", "fork"}:
        command.append(args.session_id)
    command.append(prompt)
    raw = run_jsonl(command, cwd=workdir, timeout=args.timeout)
    session_id = raw.get("session_id") or (args.session_id if args.command == "resume" else None)
    return envelope(
        args.command, ok=raw["ok"], workdir=str(workdir) if workdir else None,
        session_id=session_id, requested_model=args.model,
        actual_model=raw.get("actual_model") or args.model,
        result=raw.get("message"), error=raw.get("error"), exit_code=raw.get("exit_code"),
        stderr=raw.get("stderr"), event_count=len(raw.get("events", [])),
    )


def smoke_payload(args: argparse.Namespace) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="any-to-codex-") as temp:
        workdir = Path(temp)
        run_text(["git", "init", "--quiet"], cwd=workdir)
        common = {"model": args.model, "timeout": args.timeout, "sandbox": "read-only",
                  "skip_git_repo_check": False, "ephemeral": False, "prompt_file": None}
        first = execute_payload(argparse.Namespace(command="invoke", workdir=str(workdir),
                                prompt="Reply exactly ANY_TO_CODEX_NEW", **common))
        if not first["ok"] or "ANY_TO_CODEX_NEW" not in (first.get("result") or "") or not first.get("session_id"):
            return envelope("smoke-test", ok=False, workdir=str(workdir), requested_model=args.model,
                            actual_model=first.get("actual_model"), result={"invoke": first}, error="invoke_failed")
        resumed = execute_payload(argparse.Namespace(command="resume", workdir=str(workdir),
                                  session_id=first["session_id"], prompt="Reply exactly ANY_TO_CODEX_RESUME",
                                  prompt_file=None, model=args.model, timeout=args.timeout))
        forked = execute_payload(argparse.Namespace(command="fork", workdir=str(workdir),
                                 session_id=first["session_id"], prompt="Reply exactly ANY_TO_CODEX_FORK",
                                 prompt_file=None, model=args.model, timeout=args.timeout))
        ok = bool(resumed["ok"] and forked["ok"] and
                  "ANY_TO_CODEX_RESUME" in (resumed.get("result") or "") and
                  "ANY_TO_CODEX_FORK" in (forked.get("result") or ""))
        return envelope("smoke-test", ok=ok, workdir=str(workdir), session_id=first["session_id"],
                        requested_model=args.model, actual_model=first.get("actual_model"),
                        result={"invoke": first, "resume": resumed, "fork": forked},
                        error=None if ok else "lifecycle_failed", isolated_workspace=True)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")
    for name in ("invoke", "resume", "fork"):
        item = sub.add_parser(name)
        if name == "invoke":
            item.add_argument("--workdir", "--dir", dest="workdir", required=True)
            item.add_argument("--sandbox", choices=("read-only", "workspace-write"), default="workspace-write")
            item.add_argument("--skip-git-repo-check", action="store_true")
            item.add_argument("--ephemeral", action="store_true")
        else:
            item.add_argument("--session-id", required=True)
            item.add_argument("--workdir", "--dir", dest="workdir")
        prompts = item.add_mutually_exclusive_group(required=True)
        prompts.add_argument("--prompt")
        prompts.add_argument("--prompt-file")
        item.add_argument("--model")
        item.add_argument("--timeout", type=int, default=600)
        item.add_argument("--json", action="store_true")
    smoke = sub.add_parser("smoke-test")
    smoke.add_argument("--model")
    smoke.add_argument("--timeout", type=int, default=600)
    smoke.add_argument("--json", action="store_true")
    return root


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "status":
            payload = status_payload()
        elif args.command == "smoke-test":
            payload = smoke_payload(args)
        else:
            payload = execute_payload(args)
    except Exception as exc:
        payload = envelope(args.command, ok=False, error=str(exc))
    emit(payload, args.json)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

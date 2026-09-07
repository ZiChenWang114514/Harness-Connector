#!/usr/bin/env python3
"""Run, resume, fork, and verify Pi sessions from any compatible harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any
import uuid


SCHEMA_VERSION = 1
TARGET = "pi"
SMOKE_PROVIDER = "openai-codex"
SMOKE_MODEL = "gpt-5.6-luna"


def executable() -> str:
    value = shutil.which("pi")
    if not value:
        raise RuntimeError("pi_not_found")
    return value


def run_text(command: list[str], *, cwd: Path | None = None, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def envelope(command: str, *, ok: bool, provider: str | None = None,
             workdir: str | None = None, session_id: str | None = None,
             requested_model: str | None = None, actual_model: str | None = None,
             result: Any = None, warnings: list[str] | None = None,
             error: Any = None, **extra: Any) -> dict[str, Any]:
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
    provider = None
    actual_model = None
    for raw in stdout.splitlines():
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        events.append(event)
        if event.get("type") == "session":
            session_id = event.get("id") or session_id
        message = event.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        provider = message.get("provider") or provider
        actual_model = message.get("model") or actual_model
        if event.get("type") != "message_end":
            continue
        text_parts = [
            str(item.get("text"))
            for item in message.get("content", [])
            if isinstance(item, dict) and item.get("type") == "text" and item.get("text")
        ]
        if text_parts:
            messages.append("\n".join(text_parts))
    return {
        "events": events,
        "session_id": session_id,
        "provider": provider,
        "actual_model": actual_model,
        "message": messages[-1] if messages else None,
    }


def run_jsonl(command: list[str], *, cwd: Path, timeout: int) -> dict[str, Any]:
    try:
        process = run_text(command, cwd=cwd, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "exit_code": None,
            "stderr": exc.stderr or "",
            "error": "timeout",
            "events": [],
            "message": None,
            "session_id": None,
            "provider": None,
            "actual_model": None,
        }
    parsed = parse_events(process.stdout)
    return {
        "ok": process.returncode == 0 and bool(parsed["message"]),
        "exit_code": process.returncode,
        "stderr": process.stderr.strip() or None,
        "error": None if process.returncode == 0 else "pi_command_failed",
        **parsed,
    }


def status_payload(args: argparse.Namespace) -> dict[str, Any]:
    exe = executable()
    version = run_text([exe, "--version"])
    help_result = run_text([exe, "--help"])
    models = run_text([exe, "--list-models", args.provider])
    auth = run_text([
        exe, "auth", "check", "--provider", args.provider,
        "--model", args.model, "--json",
    ])
    try:
        auth_data = json.loads(auth.stdout)
    except json.JSONDecodeError:
        auth_data = {"status": "unknown"}
    required = ["--mode", "--session-id", "--session-dir", "--fork", "--provider", "--model"]
    support = {flag: flag in help_result.stdout for flag in required}
    model_available = args.model.lower() in models.stdout.lower()
    authenticated = auth.returncode == 0 and auth_data.get("status") == "ready"
    ok = version.returncode == 0 and all(support.values()) and model_available and authenticated
    return envelope(
        "status",
        ok=ok,
        provider=args.provider,
        requested_model=args.model,
        actual_model=args.model if model_available else None,
        result={
            "executable": exe,
            "version": version.stdout.strip(),
            "authenticated": authenticated,
            "auth_type": auth_data.get("authType"),
            "model_available": model_available,
            "required_flag_support": support,
        },
        error=None if ok else "pi_status_failed",
    )


def prompt_text(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    return args.prompt


def pi_command(args: argparse.Namespace, prompt: str) -> list[str]:
    command = [executable()]
    if args.provider:
        command += ["--provider", args.provider]
    if args.model:
        command += ["--model", args.model]
    command += ["--thinking", args.thinking, "--mode", "json", "--print"]
    if args.session_dir:
        command += ["--session-dir", str(Path(args.session_dir).resolve())]
    if args.command == "invoke":
        if args.session_id:
            command += ["--session-id", args.session_id]
    elif args.command == "resume":
        command += ["--session-id", args.session_id]
    elif args.command == "fork":
        command += ["--fork", args.session_id]
    if args.isolated:
        command += ["--no-extensions", "--no-skills", "--no-context-files"]
    if args.no_tools:
        command.append("--no-tools")
    command += ["--no-approve", prompt]
    return command


def execute_payload(args: argparse.Namespace) -> dict[str, Any]:
    workdir = Path(args.workdir).resolve()
    if not workdir.is_dir():
        return envelope(
            args.command,
            ok=False,
            provider=args.provider,
            workdir=str(workdir),
            session_id=getattr(args, "session_id", None),
            requested_model=args.model,
            error="directory_not_found",
        )
    raw = run_jsonl(pi_command(args, prompt_text(args)), cwd=workdir, timeout=args.timeout)
    warnings = [raw["stderr"]] if raw.get("stderr") else []
    return envelope(
        args.command,
        ok=raw["ok"],
        provider=raw.get("provider") or args.provider,
        workdir=str(workdir),
        session_id=raw.get("session_id") or getattr(args, "session_id", None),
        requested_model=args.model,
        actual_model=raw.get("actual_model"),
        result=raw.get("message"),
        warnings=warnings,
        error=raw.get("error"),
        exit_code=raw.get("exit_code"),
        event_count=len(raw.get("events", [])),
    )


def smoke_payload(args: argparse.Namespace) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="any-to-pi-") as temp:
        root = Path(temp)
        workdir = root / "work"
        sessions = root / "sessions"
        workdir.mkdir()
        sessions.mkdir()
        run_text(["git", "init", "--quiet"], cwd=workdir)
        session_id = str(uuid.uuid4())
        common = {
            "workdir": str(workdir),
            "session_dir": str(sessions),
            "provider": args.provider,
            "model": args.model,
            "thinking": "low",
            "timeout": args.timeout,
            "prompt_file": None,
            "isolated": True,
            "no_tools": True,
        }
        first = execute_payload(argparse.Namespace(
            command="invoke", session_id=session_id,
            prompt="Reply with exactly ANY_TO_PI_NEW and nothing else.", **common,
        ))
        if not first["ok"] or first.get("result") != "ANY_TO_PI_NEW":
            return envelope(
                "smoke-test", ok=False, provider=args.provider,
                workdir=str(workdir), session_id=session_id,
                requested_model=args.model, actual_model=first.get("actual_model"),
                result={"invoke": first}, error="invoke_failed", isolated_workspace=True,
            )
        resumed = execute_payload(argparse.Namespace(
            command="resume", session_id=session_id,
            prompt="Reply with exactly ANY_TO_PI_RESUME and nothing else.", **common,
        ))
        forked = execute_payload(argparse.Namespace(
            command="fork", session_id=session_id,
            prompt="Reply with exactly ANY_TO_PI_FORK and nothing else.", **common,
        ))
        ok = bool(
            resumed["ok"] and resumed.get("result") == "ANY_TO_PI_RESUME"
            and forked["ok"] and forked.get("result") == "ANY_TO_PI_FORK"
            and forked.get("session_id") != session_id
            and first.get("actual_model") == args.model
            and resumed.get("actual_model") == args.model
            and forked.get("actual_model") == args.model
        )
        return envelope(
            "smoke-test", ok=ok, provider=args.provider,
            workdir=str(workdir), session_id=session_id,
            requested_model=args.model, actual_model=first.get("actual_model"),
            result={"invoke": first, "resume": resumed, "fork": forked},
            error=None if ok else "lifecycle_failed", isolated_workspace=True,
        )


def add_common(item: argparse.ArgumentParser, *, session: bool) -> None:
    item.add_argument("--workdir", required=True)
    if session:
        item.add_argument("--session-id", required=True)
    else:
        item.add_argument("--session-id")
    prompts = item.add_mutually_exclusive_group(required=True)
    prompts.add_argument("--prompt")
    prompts.add_argument("--prompt-file")
    item.add_argument("--provider")
    item.add_argument("--model")
    item.add_argument("--session-dir")
    item.add_argument("--thinking", choices=("off", "minimal", "low", "medium", "high", "xhigh"), default="medium")
    item.add_argument("--timeout", type=int, default=600)
    item.add_argument("--isolated", action="store_true")
    item.add_argument("--no-tools", action="store_true")
    item.add_argument("--json", action="store_true")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--provider", default=SMOKE_PROVIDER)
    status.add_argument("--model", default=SMOKE_MODEL)
    status.add_argument("--json", action="store_true")
    add_common(sub.add_parser("invoke"), session=False)
    add_common(sub.add_parser("resume"), session=True)
    add_common(sub.add_parser("fork"), session=True)
    smoke = sub.add_parser("smoke-test")
    smoke.add_argument("--provider", default=SMOKE_PROVIDER)
    smoke.add_argument("--model", default=SMOKE_MODEL)
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
            payload = status_payload(args)
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

#!/usr/bin/env python3
"""Run Claude Code through an official subscription or the DeepSeek Anthropic API."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any


SCHEMA_VERSION = 1
TARGET = "claude-code"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/anthropic"
DEEPSEEK_MODELS = {
    "pro": "deepseek-v4-pro[1m]",
    "flash": "deepseek-v4-flash",
    "deepseek-v4-pro[1m]": "deepseek-v4-pro[1m]",
    "deepseek-v4-flash": "deepseek-v4-flash",
}


def executable() -> str:
    value = shutil.which("claude")
    if not value:
        raise RuntimeError("claude_not_found")
    return value


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
        timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace",
                          capture_output=True, timeout=timeout, check=False)


def provider_environment(provider: str, model: str | None = None) -> tuple[dict[str, str], str | None]:
    env = os.environ.copy()
    if provider == "official":
        for name in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY",
                     "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
                     "ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL",
                     "CLAUDE_CODE_SUBAGENT_MODEL"):
            env.pop(name, None)
        return env, model
    key = env.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("deepseek_api_key_not_configured")
    selected = DEEPSEEK_MODELS.get(model or "pro")
    if not selected:
        raise ValueError("unsupported_deepseek_model")
    env["ANTHROPIC_BASE_URL"] = DEEPSEEK_BASE_URL
    env["ANTHROPIC_AUTH_TOKEN"] = key
    env.pop("ANTHROPIC_API_KEY", None)
    env["ANTHROPIC_MODEL"] = selected
    env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = "deepseek-v4-pro[1m]"
    env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = "deepseek-v4-pro[1m]"
    env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = "deepseek-v4-flash"
    env["CLAUDE_CODE_SUBAGENT_MODEL"] = "deepseek-v4-flash"
    env["CLAUDE_CODE_EFFORT_LEVEL"] = "max"
    env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] = "786432"
    return env, selected


def envelope(command: str, *, ok: bool, provider: str, workdir: str | None = None,
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


def parse_response(stdout: str) -> dict[str, Any]:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {"session_id": None, "actual_model": None, "result": stdout.strip() or None,
                "is_error": False, "raw": None}
    if not isinstance(data, dict):
        return {"session_id": None, "actual_model": None, "result": data,
                "is_error": False, "raw": data}
    model_usage = data.get("modelUsage") or {}
    actual_model = data.get("model") or data.get("model_name")
    if not actual_model and isinstance(model_usage, dict) and len(model_usage) == 1:
        model_id, details = next(iter(model_usage.items()))
        actual_model = details.get("canonicalModel") if isinstance(details, dict) else None
        actual_model = actual_model or model_id
    return {
        "session_id": data.get("session_id"),
        "actual_model": actual_model,
        "result": data.get("result") or data.get("response"),
        "is_error": bool(data.get("is_error")),
        "raw": data,
    }


def auth_status(exe: str) -> dict[str, Any]:
    result = run([exe, "auth", "status"], timeout=30)
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        data = {"loggedIn": False, "detail": result.stdout.strip() or result.stderr.strip()}
    return data if isinstance(data, dict) else {"loggedIn": False}


def status_payload(provider: str, model: str | None) -> dict[str, Any]:
    exe = executable()
    version = run([exe, "--version"], timeout=30)
    auth = auth_status(exe)
    help_result = run([exe, "--help"], timeout=30)
    flags = ("--print", "--output-format", "--resume", "--model", "--permission-mode")
    support = {flag: flag in help_result.stdout for flag in flags}
    selected = DEEPSEEK_MODELS.get(model or "pro") if provider == "deepseek" else model
    provider_ready = bool(os.environ.get("DEEPSEEK_API_KEY")) if provider == "deepseek" else bool(auth.get("loggedIn"))
    ok = version.returncode == 0 and all(support.values()) and provider_ready
    return envelope(
        "status", ok=ok, provider=provider, requested_model=selected,
        executable=exe, version=version.stdout.strip(), official_auth=auth,
        deepseek_api_key_present=bool(os.environ.get("DEEPSEEK_API_KEY")),
        provider_ready=provider_ready, required_flag_support=support,
        error=None if ok else "provider_not_ready",
    )


def prompt_text(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    return args.prompt


def execute_payload(args: argparse.Namespace) -> dict[str, Any]:
    exe = executable()
    env, selected_model = provider_environment(args.provider, args.model)
    workdir = Path(args.workdir).resolve() if getattr(args, "workdir", None) else None
    if workdir and not workdir.is_dir():
        return envelope(args.command, ok=False, provider=args.provider, workdir=str(workdir),
                        requested_model=selected_model, error="directory_not_found")
    command = [exe, "--print", prompt_text(args), "--output-format", "json",
               "--permission-mode", args.permission_mode]
    if selected_model and args.provider == "official":
        command += ["--model", selected_model]
    if args.command == "resume":
        command += ["--resume", args.session_id]
    try:
        process = run(command, cwd=workdir, env=env, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        return envelope(args.command, ok=False, provider=args.provider,
                        workdir=str(workdir) if workdir else None,
                        requested_model=selected_model, error="timeout")
    parsed = parse_response(process.stdout)
    ok = process.returncode == 0 and not parsed["is_error"] and bool(parsed["result"])
    return envelope(
        args.command, ok=ok, provider=args.provider,
        workdir=str(workdir) if workdir else None,
        session_id=parsed["session_id"] or (args.session_id if args.command == "resume" else None),
        requested_model=selected_model, actual_model=parsed["actual_model"],
        result=parsed["result"], error=None if ok else "claude_command_failed",
        warnings=["claude_code_unrecognized_model_notice"] if "unrecognized_model" in process.stderr else [],
        exit_code=process.returncode, stderr=process.stderr.strip() or None,
    )


def smoke_payload(args: argparse.Namespace) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="any-to-claude-") as temp:
        workdir = Path(temp)
        run(["git", "init", "--quiet"], cwd=workdir, timeout=30)
        call = argparse.Namespace(
            command="invoke", provider=args.provider, model=args.model, workdir=str(workdir),
            prompt="Reply exactly ANY_TO_CLAUDE_OK", prompt_file=None,
            permission_mode="plan", timeout=args.timeout,
        )
        first = execute_payload(call)
        marker = "ANY_TO_CLAUDE_OK" in (first.get("result") or "")
        resumed = execute_payload(argparse.Namespace(
            command="resume", provider=args.provider, model=args.model,
            workdir=str(workdir), session_id=first.get("session_id"),
            prompt="Reply exactly ANY_TO_CLAUDE_RESUME", prompt_file=None,
            permission_mode="plan", timeout=args.timeout,
        )) if first.get("session_id") else envelope(
            "resume", ok=False, provider=args.provider, error="session_id_missing"
        )
        resume_marker = "ANY_TO_CLAUDE_RESUME" in (resumed.get("result") or "")
        same_session = bool(first.get("session_id") and resumed.get("session_id") == first.get("session_id"))
        ok = bool(first["ok"] and marker and resumed["ok"] and resume_marker and same_session)
        return envelope(
            "smoke-test", ok=ok, provider=args.provider, workdir=str(workdir),
            session_id=first.get("session_id"), requested_model=first.get("requested_model"),
            actual_model=first.get("actual_model"), result={"invoke": first, "resume": resumed},
            error=None if ok else "lifecycle_failed", isolated_workspace=True,
            resume_session_match=same_session, resume_reply_found=resume_marker,
        )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status")
    status.add_argument("--provider", choices=("official", "deepseek"), default="official")
    status.add_argument("--model")
    status.add_argument("--json", action="store_true")
    for name in ("invoke", "resume"):
        item = sub.add_parser(name)
        item.add_argument("--provider", choices=("official", "deepseek"), default="official")
        item.add_argument("--model")
        if name == "invoke":
            item.add_argument("--workdir", "--dir", dest="workdir", required=True)
        else:
            item.add_argument("--session-id", required=True)
            item.add_argument("--workdir", "--dir", dest="workdir")
        prompts = item.add_mutually_exclusive_group(required=True)
        prompts.add_argument("--prompt")
        prompts.add_argument("--prompt-file")
        item.add_argument("--permission-mode", choices=("plan", "default", "acceptEdits", "dontAsk"), default="default")
        item.add_argument("--timeout", type=int, default=600)
        item.add_argument("--json", action="store_true")
    smoke = sub.add_parser("smoke-test")
    smoke.add_argument("--provider", choices=("official", "deepseek"), default="official")
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
            payload = status_payload(args.provider, args.model)
        elif args.command == "smoke-test":
            payload = smoke_payload(args)
        else:
            payload = execute_payload(args)
    except Exception as exc:
        payload = envelope(args.command, ok=False, provider=getattr(args, "provider", "official"), error=str(exc))
    emit(payload, args.json)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

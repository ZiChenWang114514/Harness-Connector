#!/usr/bin/env python3
"""Invoke and inspect local Kimi Code sessions with exact workspace checks."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from types import SimpleNamespace
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULTS_PATH = SKILL_DIR / "references" / "defaults.json"
SESSION_ID_PATTERN = re.compile(
    r"^session_[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
READONLY_FORBIDDEN_TOOLS = {
    "Write", "Edit", "Bash", "Agent", "AgentSwarm", "AskUserQuestion",
}


class SessionError(RuntimeError):
    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.details = {"ok": False, "error": message, **details}


def load_defaults() -> dict[str, Any]:
    with DEFAULTS_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    timeout = data.get("request_timeout_seconds")
    limit = data.get("max_prompt_characters")
    if not isinstance(timeout, int) or timeout <= 0:
        raise ValueError("request_timeout_seconds must be a positive integer")
    if not isinstance(limit, int) or not 1000 <= limit <= 30000:
        raise ValueError("max_prompt_characters must be between 1000 and 30000")
    return data


def kimi_home(environment: dict[str, str] | None = None) -> Path:
    env = environment or os.environ
    configured = env.get("KIMI_CODE_HOME")
    return Path(configured).expanduser().resolve() if configured else Path.home() / ".kimi-code"


def find_kimi() -> str:
    explicit = os.environ.get("KIMI_CODE_EXE")
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_file():
            return str(path)
        raise FileNotFoundError(f"KIMI_CODE_EXE does not name a file: {path}")
    names = ["kimi.exe", "kimi.cmd", "kimi"] if os.name == "nt" else ["kimi"]
    for name in names:
        if resolved := shutil.which(name):
            return resolved
    candidates = [kimi_home() / "bin" / ("kimi.exe" if os.name == "nt" else "kimi")]
    for path in candidates:
        if path.is_file():
            return str(path)
    raise FileNotFoundError("Kimi Code CLI was not found on PATH or under KIMI_CODE_HOME/bin")


def canonical_path(value: str | Path) -> str:
    return os.path.normcase(os.path.normpath(str(Path(value).expanduser().resolve())))


def resolve_directory(value: str | Path, label: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_dir():
        raise NotADirectoryError(f"{label} does not exist or is not a directory: {path}")
    return path


def read_config_summary(home: Path) -> dict[str, Any]:
    path = home / "config.toml"
    if not path.is_file():
        return {
            "config_path": str(path), "config_exists": False,
            "default_model": None, "model_aliases": [],
        }
    with path.open("rb") as handle:
        data = tomllib.load(handle)
    models = data.get("models")
    aliases = sorted(models) if isinstance(models, dict) else []
    default_model = data.get("default_model")
    return {
        "config_path": str(path), "config_exists": True,
        "default_model": default_model if isinstance(default_model, str) else None,
        "model_aliases": aliases,
    }


def read_session_index(home: Path) -> tuple[list[dict[str, Any]], int]:
    path = home / "session_index.jsonl"
    if not path.is_file():
        return [], 0
    records: list[dict[str, Any]] = []
    invalid = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            invalid += 1
            continue
        if isinstance(item, dict):
            records.append(item)
        else:
            invalid += 1
    return records, invalid


def records_for_workdir(records: list[dict[str, Any]], workdir: Path) -> list[dict[str, Any]]:
    expected = canonical_path(workdir)
    return [
        item for item in records
        if isinstance(item.get("workDir"), str)
        and canonical_path(item["workDir"]) == expected
    ]


def get_session_record(home: Path, session_id: str, workdir: Path) -> dict[str, Any]:
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise SessionError("Invalid Kimi session ID format", session_id=session_id)
    records, invalid = read_session_index(home)
    matches = [item for item in records if item.get("sessionId") == session_id]
    if len(matches) != 1:
        raise SessionError(
            "The exact Kimi session ID was not found once in the session index",
            session_id=session_id, matching_records=len(matches), invalid_index_lines=invalid,
        )
    record = matches[0]
    recorded_workdir = record.get("workDir")
    if not isinstance(recorded_workdir, str) or canonical_path(recorded_workdir) != canonical_path(workdir):
        raise SessionError(
            "The session belongs to a different working directory",
            session_id=session_id, requested_workdir=str(workdir), recorded_workdir=recorded_workdir,
        )
    session_dir_raw = record.get("sessionDir")
    if not isinstance(session_dir_raw, str):
        raise SessionError("The session index record has no sessionDir", session_id=session_id)
    session_dir = Path(session_dir_raw).expanduser().resolve()
    sessions_root = (home / "sessions").resolve()
    try:
        session_dir.relative_to(sessions_root)
    except ValueError as exc:
        raise SessionError(
            "The indexed session directory is outside KIMI_CODE_HOME/sessions",
            session_id=session_id, session_dir=str(session_dir),
        ) from exc
    if not session_dir.is_dir():
        raise SessionError(
            "The indexed session directory does not exist",
            session_id=session_id, session_dir=str(session_dir),
        )
    return record


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return data


def inspect_wire(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "wire_exists": path.is_file(), "wire_event_count": 0,
        "last_event_type": None, "profile": None, "actual_model": None,
        "provider": None, "thinking_effort": None, "permission_mode": None,
        "active_tools": [], "disallowed_tools": [],
    }
    if not path.is_file():
        return summary
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        summary["wire_event_count"] += 1
        event_type = event.get("type")
        if isinstance(event_type, str):
            summary["last_event_type"] = event_type
        if event_type == "profile.bind":
            summary["profile"] = event.get("profileName")
            summary["actual_model"] = event.get("modelAlias") or summary["actual_model"]
            summary["thinking_effort"] = event.get("thinkingEffort")
            if isinstance(event.get("activeToolNames"), list):
                summary["active_tools"] = event["activeToolNames"]
            if isinstance(event.get("disallowedTools"), list):
                summary["disallowed_tools"] = event["disallowedTools"]
        elif event_type == "permission.set_mode":
            summary["permission_mode"] = event.get("mode")
        elif event_type == "llm.request":
            summary["actual_model"] = event.get("modelAlias") or summary["actual_model"]
            summary["provider"] = event.get("provider")
            summary["thinking_effort"] = event.get("thinkingEffort") or summary["thinking_effort"]
    return summary


def inspect_session(home: Path, session_id: str, workdir: Path) -> dict[str, Any]:
    record = get_session_record(home, session_id, workdir)
    session_dir = Path(record["sessionDir"]).resolve()
    state_path = session_dir / "state.json"
    if not state_path.is_file():
        raise SessionError("The session state file is missing", session_id=session_id)
    state = load_json_object(state_path)
    if state.get("id") != session_id:
        raise SessionError("The state file has a different session ID", session_id=session_id)
    state_cwd = state.get("cwd")
    if not isinstance(state_cwd, str) or canonical_path(state_cwd) != canonical_path(workdir):
        raise SessionError(
            "The state file has a different working directory",
            session_id=session_id, state_workdir=state_cwd, requested_workdir=str(workdir),
        )
    wire = inspect_wire(session_dir / "agents" / "main" / "wire.jsonl")
    return {
        "ok": True,
        "session_id": session_id,
        "workdir": str(workdir),
        "session_dir": str(session_dir),
        "title": state.get("title"),
        "created_at": state.get("createdAt"),
        "updated_at": state.get("updatedAt"),
        "archived": state.get("archived"),
        "last_turn_reason": state.get("lastTurnReason"),
        **wire,
    }


def redact(text: str, max_chars: int = 4000) -> str:
    value = text[-max_chars:]
    value = re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", value)
    value = re.sub(r"(?i)\b(sk-[A-Za-z0-9_-]{12,})\b", "[REDACTED]", value)
    return value


def stop_owned_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_process(
    command: list[str], workdir: Path, environment: dict[str, str], timeout: int,
) -> dict[str, Any]:
    process = subprocess.Popen(
        command, cwd=str(workdir), env=environment,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
        start_new_session=(os.name != "nt"),
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stop_owned_process(process)
        stdout, stderr = process.communicate()
    return {
        "returncode": process.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "owned_pid": process.pid,
    }


def run_quick(executable: str, *args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [executable, *args], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
        timeout=timeout, check=False,
    )


def parse_stream_json(stdout: str) -> dict[str, Any]:
    final_reply = ""
    session_id = None
    cli_version = None
    event_count = 0
    tool_names: list[str] = []
    invalid_lines = 0
    for raw in stdout.splitlines():
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            invalid_lines += 1
            continue
        if not isinstance(event, dict):
            invalid_lines += 1
            continue
        event_count += 1
        if event.get("role") == "assistant" and isinstance(event.get("content"), str):
            final_reply = event["content"]
        if event.get("role") == "meta" and event.get("type") == "system.version":
            cli_version = event.get("version")
        if event.get("role") == "meta" and event.get("type") == "session.resume_hint":
            session_id = event.get("session_id")
        calls = event.get("tool_calls")
        if isinstance(calls, list):
            for call in calls:
                if not isinstance(call, dict):
                    continue
                function = call.get("function")
                name = function.get("name") if isinstance(function, dict) else call.get("name")
                if isinstance(name, str) and name not in tool_names:
                    tool_names.append(name)
    return {
        "reply": final_reply,
        "session_id": session_id,
        "cli_version": cli_version,
        "stream_event_count": event_count,
        "stream_invalid_line_count": invalid_lines,
        "tool_call_names": tool_names,
    }


def build_command(
    executable: str, args: argparse.Namespace | SimpleNamespace,
    prompt: str, defaults: dict[str, Any],
) -> tuple[list[str], dict[str, str], str]:
    if len(prompt) > defaults["max_prompt_characters"]:
        raise SessionError(
            "The prompt is too long for a reliable Windows process invocation",
            prompt_characters=len(prompt), maximum=defaults["max_prompt_characters"],
        )
    session_id = getattr(args, "session_id", None)
    model = getattr(args, "model", None)
    mode = getattr(args, "mode", None)
    agent = getattr(args, "agent", None)
    agent_file = getattr(args, "agent_file", None)
    add_dirs = list(getattr(args, "add_dir", None) or [])
    skills_dirs = list(getattr(args, "skills_dir", None) or [])
    new_only_selected = any([model, mode, agent, agent_file, add_dirs, skills_dirs])
    if session_id and new_only_selected:
        raise SessionError(
            "Model, mode, Agent, added directories, and custom Skill directories apply only to new sessions",
            session_id=session_id,
        )
    if mode == "readonly" and (agent or agent_file):
        raise SessionError("Readonly mode cannot be combined with --agent or --agent-file")
    if agent and agent_file:
        raise SessionError("--agent and --agent-file cannot be combined")

    command = [executable]
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    effective_mode = "existing" if session_id else (mode or "build")
    if session_id:
        command.extend(["--session", session_id])
    else:
        if model:
            command.extend(["--model", model])
        if effective_mode == "readonly":
            readonly_path = (SKILL_DIR / defaults["readonly_agent_file"]).resolve()
            if not readonly_path.is_file():
                raise FileNotFoundError(f"Readonly Agent file is missing: {readonly_path}")
            command.extend(["--agent-file", str(readonly_path)])
            environment["KIMI_CODE_EXPERIMENTAL_FLAG"] = "1"
        elif agent:
            command.extend(["--agent", agent])
            environment["KIMI_CODE_EXPERIMENTAL_FLAG"] = "1"
        elif agent_file:
            path = Path(agent_file).expanduser().resolve()
            if not path.is_file():
                raise FileNotFoundError(f"Agent file does not exist: {path}")
            command.extend(["--agent-file", str(path)])
            environment["KIMI_CODE_EXPERIMENTAL_FLAG"] = "1"
        for value in add_dirs:
            command.extend(["--add-dir", str(resolve_directory(value, "Added directory"))])
        for value in skills_dirs:
            command.extend(["--skills-dir", str(resolve_directory(value, "Skill directory"))])
    command.extend(["--prompt", prompt, "--output-format", "stream-json"])
    return command, environment, effective_mode


def read_prompt(args: argparse.Namespace | SimpleNamespace, smoke_reply: str | None = None) -> str:
    if smoke_reply is not None:
        return f"Reply with exactly {smoke_reply}. Do not use tools."
    prompt = getattr(args, "prompt", None)
    prompt_file = getattr(args, "prompt_file", None)
    if prompt_file:
        prompt = Path(prompt_file).expanduser().resolve().read_text(encoding="utf-8")
    if not isinstance(prompt, str) or not prompt.strip():
        raise SessionError("A non-empty --prompt or --prompt-file is required")
    return prompt


def invoke_session(
    args: argparse.Namespace | SimpleNamespace,
    *, home_override: Path | None = None,
    environment_override: dict[str, str] | None = None,
    smoke_reply: str | None = None,
) -> dict[str, Any]:
    defaults = load_defaults()
    executable = find_kimi()
    workdir = resolve_directory(args.dir, "Work directory")
    home = home_override or kimi_home()
    prompt = read_prompt(args, smoke_reply)
    config = read_config_summary(home)
    session_id = getattr(args, "session_id", None)
    if session_id:
        get_session_record(home, session_id, workdir)
    before_records, _ = read_session_index(home)
    before_ids = {
        item.get("sessionId") for item in records_for_workdir(before_records, workdir)
        if isinstance(item.get("sessionId"), str)
    }
    command, environment, effective_mode = build_command(executable, args, prompt, defaults)
    if environment_override:
        environment.update(environment_override)
    timeout = int(getattr(args, "timeout", None) or defaults["request_timeout_seconds"])
    if timeout <= 0:
        raise SessionError("--timeout must be a positive integer")
    run = run_process(command, workdir, environment, timeout)
    parsed = parse_stream_json(run["stdout"])
    after_records, _ = read_session_index(home)
    after_ids = {
        item.get("sessionId") for item in records_for_workdir(after_records, workdir)
        if isinstance(item.get("sessionId"), str)
    }
    new_ids = sorted(after_ids - before_ids)
    resolved_session_id = parsed["session_id"] or session_id
    if resolved_session_id is None and len(new_ids) == 1:
        resolved_session_id = new_ids[0]
    common_error = {
        "session_id": resolved_session_id,
        "workdir": str(workdir),
        "returncode": run["returncode"],
        "stderr_tail": redact(run["stderr"]),
    }
    if run["timed_out"]:
        raise SessionError(
            "Kimi invocation timed out; the process tree started by this call was terminated",
            timeout_seconds=timeout, newly_indexed_session_ids=new_ids, **common_error,
        )
    if run["returncode"] != 0:
        raise SessionError("Kimi invocation failed", **common_error)
    if not resolved_session_id or not SESSION_ID_PATTERN.fullmatch(resolved_session_id):
        raise SessionError("Kimi did not return a valid session ID", **common_error)
    if session_id and resolved_session_id != session_id:
        raise SessionError(
            "Kimi returned a different session ID while continuing a session",
            requested_session_id=session_id, **common_error,
        )
    if not parsed["reply"]:
        raise SessionError("Kimi completed without a final assistant reply", **common_error)

    inspected = inspect_session(home, resolved_session_id, workdir)
    requested_model = None if session_id else (getattr(args, "model", None) or config["default_model"])
    actual_model = inspected.get("actual_model")
    if requested_model and actual_model and requested_model != actual_model:
        raise SessionError(
            "Kimi used a different model alias than requested",
            requested_model=requested_model, actual_model=actual_model, **common_error,
        )
    return {
        "ok": True,
        "session_id": resolved_session_id,
        "created_session": resolved_session_id in new_ids,
        "workdir": str(workdir),
        "mode": effective_mode,
        "requested_model": requested_model,
        "actual_model": actual_model,
        "provider": inspected.get("provider"),
        "thinking_effort": inspected.get("thinking_effort"),
        "profile": inspected.get("profile"),
        "permission_mode": inspected.get("permission_mode"),
        "active_tools": inspected.get("active_tools"),
        "disallowed_tools": inspected.get("disallowed_tools"),
        "tool_call_names": parsed["tool_call_names"],
        "reply": parsed["reply"],
        "cli_version": parsed["cli_version"],
        "stream_event_count": parsed["stream_event_count"],
        "stream_invalid_line_count": parsed["stream_invalid_line_count"],
        "last_turn_reason": inspected.get("last_turn_reason"),
    }


def running_kimi_processes() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    result = run_quick("tasklist", "/FI", "IMAGENAME eq kimi.exe", "/FO", "CSV", "/NH")
    if result.returncode != 0:
        return []
    processes: list[dict[str, Any]] = []
    for row in csv.reader(io.StringIO(result.stdout)):
        if len(row) >= 2 and row[0].casefold() == "kimi.exe":
            try:
                pid: int | str = int(row[1])
            except ValueError:
                pid = row[1]
            processes.append({"name": row[0], "pid": pid})
    return processes


def status(args: argparse.Namespace) -> dict[str, Any]:
    executable = find_kimi()
    home = kimi_home()
    version = run_quick(executable, "--version")
    doctor = run_quick(executable, "doctor", timeout=60)
    providers = run_quick(executable, "provider", "list", timeout=60)
    config = read_config_summary(home)
    records, invalid = read_session_index(home)
    workdir = resolve_directory(args.dir, "Work directory") if args.dir else None
    local_records = records_for_workdir(records, workdir) if workdir else []
    default_model = config["default_model"]
    model_available = default_model in config["model_aliases"] if default_model else False
    return {
        "ok": version.returncode == 0 and doctor.returncode == 0 and model_available,
        "executable": executable,
        "version": version.stdout.strip(),
        "kimi_code_home": str(home),
        "config_path": config["config_path"],
        "config_valid": doctor.returncode == 0,
        "default_model": default_model,
        "default_model_available": model_available,
        "model_aliases": config["model_aliases"],
        "provider_summary": [line for line in providers.stdout.splitlines() if line.strip()],
        "credentials_directory_present": (home / "credentials").is_dir(),
        "session_count": len(records),
        "invalid_session_index_lines": invalid,
        "workdir": str(workdir) if workdir else None,
        "workdir_session_count": len(local_records) if workdir else None,
        "latest_workdir_session_id": local_records[-1].get("sessionId") if local_records else None,
        "running_kimi_processes": running_kimi_processes(),
    }


def file_sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def copy_smoke_home(source: Path, destination: Path) -> list[str]:
    copied: list[str] = []
    for name in ("config.toml", "region", "device_id"):
        source_path = source / name
        if source_path.is_file():
            shutil.copy2(source_path, destination / name)
            copied.append(name)
    credentials = source / "credentials"
    if credentials.is_dir():
        shutil.copytree(credentials, destination / "credentials")
        copied.append("credentials/")
    if not (destination / "config.toml").is_file():
        raise SessionError("Cannot run the smoke test without config.toml")
    return copied


def smoke_test(args: argparse.Namespace) -> dict[str, Any]:
    defaults = load_defaults()
    source_home = kimi_home()
    safe_parent = resolve_directory(args.dir, "Safe directory")
    primary_index = source_home / "session_index.jsonl"
    before_hash = file_sha256(primary_index)
    isolated_home_path: Path | None = None
    isolated_workdir_path: Path | None = None
    result: dict[str, Any]
    copied: list[str]
    with tempfile.TemporaryDirectory(prefix="codex-kimi-home-") as home_raw:
        isolated_home_path = Path(home_raw).resolve()
        copied = copy_smoke_home(source_home, isolated_home_path)
        with tempfile.TemporaryDirectory(prefix="codex-kimi-smoke-", dir=str(safe_parent)) as work_raw:
            isolated_workdir_path = Path(work_raw).resolve()
            marker_path = isolated_workdir_path / "kimi-smoke-marker.txt"
            marker_path.write_text(defaults["smoke_test_reply"] + "\n", encoding="utf-8")
            smoke_args = SimpleNamespace(
                dir=str(isolated_workdir_path),
                prompt=(
                    "Use the Read tool to read kimi-smoke-marker.txt, then reply with exactly "
                    f"{defaults['smoke_test_reply']}."
                ),
                prompt_file=None,
                session_id=None, model=args.model, mode="readonly",
                agent=None, agent_file=None, add_dir=[], skills_dir=[], timeout=args.timeout,
            )
            result = invoke_session(
                smoke_args,
                home_override=isolated_home_path,
                environment_override={"KIMI_CODE_HOME": str(isolated_home_path)},
            )
            if result["reply"].strip() != defaults["smoke_test_reply"]:
                raise SessionError(
                    "Unexpected smoke-test reply", reply=result["reply"],
                    session_id=result["session_id"],
                )
            active = set(result.get("active_tools") or [])
            forbidden = sorted(active & READONLY_FORBIDDEN_TOOLS)
            if forbidden:
                raise SessionError(
                    "Readonly smoke test exposed prohibited tools",
                    prohibited_active_tools=forbidden, session_id=result["session_id"],
                )
            if "Read" not in result.get("tool_call_names", []):
                raise SessionError(
                    "Readonly smoke test did not exercise the Read tool",
                    tool_call_names=result.get("tool_call_names", []),
                    session_id=result["session_id"],
                )
            resume_args = SimpleNamespace(
                dir=str(isolated_workdir_path), prompt="Reply exactly KIMI_RESUME_OK.",
                prompt_file=None, session_id=result["session_id"], model=None, mode=None,
                agent=None, agent_file=None, add_dir=[], skills_dir=[], timeout=args.timeout,
            )
            resumed = invoke_session(
                resume_args,
                home_override=isolated_home_path,
                environment_override={"KIMI_CODE_HOME": str(isolated_home_path)},
            )
            if resumed["session_id"] != result["session_id"] or resumed["reply"].strip() != "KIMI_RESUME_OK":
                raise SessionError(
                    "Exact session continuation failed",
                    requested_session_id=result["session_id"],
                    returned_session_id=resumed.get("session_id"),
                    reply=resumed.get("reply"),
                )
    after_hash = file_sha256(primary_index)
    return {
        "ok": True,
        "reply": result["reply"],
        "cli_version": result["cli_version"],
        "requested_model": result["requested_model"],
        "actual_model": result["actual_model"],
        "profile": result["profile"],
        "permission_mode": result["permission_mode"],
        "active_tools": result["active_tools"],
        "tool_call_names": result["tool_call_names"],
        "resume_session_match": resumed["session_id"] == result["session_id"],
        "resume_reply_found": resumed["reply"].strip() == "KIMI_RESUME_OK",
        "test_session_id": result["session_id"],
        "test_session_deleted": isolated_home_path is not None and not isolated_home_path.exists(),
        "temporary_workdir_deleted": isolated_workdir_path is not None and not isolated_workdir_path.exists(),
        "primary_session_index_unchanged": before_hash == after_hash,
        "copied_runtime_items": copied,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Read-only Kimi diagnostics")
    status_parser.add_argument("--dir", "--workdir", dest="dir", help="Optional work directory for session counts")
    status_parser.add_argument("--json", action="store_true")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect one exact Kimi session")
    inspect_parser.add_argument("--dir", "--workdir", dest="dir", required=True)
    inspect_parser.add_argument("--session-id", required=True)
    inspect_parser.add_argument("--json", action="store_true")

    invoke_parser = subparsers.add_parser("invoke", help="Create or continue a Kimi session")
    invoke_parser.add_argument("--dir", "--workdir", dest="dir", required=True)
    prompt_group = invoke_parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt")
    prompt_group.add_argument("--prompt-file")
    invoke_parser.add_argument("--session-id")
    invoke_parser.add_argument("--model", help="Temporary model alias for a new session")
    invoke_parser.add_argument("--mode", choices=("build", "readonly"))
    invoke_parser.add_argument("--agent", help="Kimi Agent name for a new session")
    invoke_parser.add_argument("--agent-file", help="Kimi Agent file for a new session")
    invoke_parser.add_argument("--add-dir", action="append", default=[])
    invoke_parser.add_argument("--skills-dir", action="append", default=[])
    invoke_parser.add_argument("--timeout", type=int)
    invoke_parser.add_argument("--json", action="store_true")

    smoke_parser = subparsers.add_parser("smoke-test", help="Run an isolated real Kimi test")
    smoke_parser.add_argument("--dir", "--workdir", dest="dir", required=True)
    smoke_parser.add_argument("--model", help="Temporary model alias")
    smoke_parser.add_argument("--timeout", type=int)
    smoke_parser.add_argument("--json", action="store_true")
    return parser


def print_result(result: dict[str, Any], as_json: bool, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2), file=stream)
    else:
        for key, value in result.items():
            print(f"{key}: {value}", file=stream)


def any_to_payload(result: dict[str, Any], command: str) -> dict[str, Any]:
    payload = dict(result)
    payload.setdefault("schema_version", 1)
    payload.setdefault("target", "kimi-code")
    payload.setdefault("command", command)
    payload.setdefault("provider", "kimi-code")
    payload.setdefault("workdir", payload.get("workdir") or payload.get("directory"))
    payload.setdefault("session_id", payload.get("session_id"))
    payload.setdefault("requested_model", payload.get("requested_model") or payload.get("default_model"))
    payload.setdefault("actual_model", payload.get("actual_model") or payload.get("model"))
    payload.setdefault("result", payload.get("response"))
    payload.setdefault("warnings", [])
    payload.setdefault("error", None)
    return payload


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "status":
            result = status(args)
        elif args.command == "inspect":
            home = kimi_home()
            workdir = resolve_directory(args.dir, "Work directory")
            result = inspect_session(home, args.session_id, workdir)
        elif args.command == "invoke":
            result = invoke_session(args)
        else:
            result = smoke_test(args)
        if args.json:
            result = any_to_payload(result, args.command)
        print_result(result, args.json)
        return 0 if result.get("ok") else 1
    except SessionError as exc:
        details = exc.details
        if getattr(args, "json", False):
            details = any_to_payload(details, args.command)
        print_result(details, getattr(args, "json", False), error=not getattr(args, "json", False))
        return 1
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "error_type": type(exc).__name__}
        if getattr(args, "json", False):
            result = any_to_payload(result, args.command)
        print_result(result, getattr(args, "json", False), error=not getattr(args, "json", False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

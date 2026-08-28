<p align="center">
  <picture>
    <source media="(max-width: 680px)" srcset="./assets/readme/hero-mobile.svg">
    <img src="./assets/readme/hero.svg" width="100%" alt="Any-to-DeepSeek-Harness: route work from any compatible harness to exact DeepSeek Harness sessions">
  </picture>
</p>

<p align="center">
  <strong>English</strong> · <a href="./README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <a href="https://github.com/ZiChenWang114514/Any-to-DeepSeek-Harness/actions/workflows/ci.yml"><img src="https://github.com/ZiChenWang114514/Any-to-DeepSeek-Harness/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  · Windows · Python 3.10+ · MIT
</p>

# Any-to-DeepSeek-Harness

Connect any compatible coding harness to local DeepSeek Harness sessions. The adapter inspects the active V4 route without exposing the API key, runs one headless task in a chosen repository, and identifies session entries created by that call.

This repository is a local session adapter: a Python CLI, plus a Codex Skill wrapper. It is independent of DeepSeek. DeepSeek Harness is a fast-moving prerelease, so re-run status, unit tests, and the smoke test after upgrading it.

## What is verified

| Model or component | Current evidence |
| --- | --- |
| Skill structure and Python wrapper | Validated in CI on Windows |
| DeepSeek Harness | `0.1.1-rc.2` detected locally |
| `deepseek-v4-flash` | Live isolated request returned `DSH_SMOKE_OK` |
| `deepseek-v4-pro` | Built-in route detected; a separate live request is still required |
| `deepseek-v4-flash-vision-exp` | Text-and-image capability detected; an image round trip is still required |

A model listed by the adapter is selectable. Only a successful request confirms current access.

## What it does

- Report the active provider, model, and reasoning effort without printing `DEEPSEEK_API_KEY`.
- Start every call from the directory supplied by the user.
- Compare the session directory before and after each headless task.
- On timeout, stop only the process tree started by the wrapper.
- Run an isolated smoke test in a temporary `DSH_HOME` linked to the installed profile tree.

The current CLI does not provide an exact headless resume option. Continue an existing conversation through the TUI or Web profile using its complete session ID and original workspace.

Codex, Claude Code, Grok Build, and other tools can call the Python CLI. Codex users can also invoke `$codex-dsh-session` after installing the Skill.

## Install

```powershell
npm install -g @deepseek-ai/dsh
dsh --version
```

Configure `DEEPSEEK_API_KEY` through your normal secret-management method. Do not place the value in a repository, prompt file, or command argument.

```powershell
git clone https://github.com/ZiChenWang114514/Any-to-DeepSeek-Harness.git `
  "$env:USERPROFILE\.codex\skills\codex-dsh-session"
```

The clone destination is the Codex Skill id, `codex-dsh-session`. Other harnesses can run `scripts/dsh_session.py` directly.

## First use

```powershell
python "$env:USERPROFILE\.codex\skills\codex-dsh-session\scripts\dsh_session.py" `
  status --json
```

Typical fields:

```json
{
  "provider": "deepseek-official",
  "default_model": "deepseek-v4-flash",
  "reasoning_effort": "max",
  "required_models_present": true,
  "model_access_configured": true
}
```

Run a headless task:

```powershell
python .\scripts\dsh_session.py invoke `
  --dir C:\path\to\repo `
  --prompt "Inspect this repository and explain the failing tests." `
  --json
```

For a longer instruction:

```powershell
python .\scripts\dsh_session.py invoke `
  --dir C:\path\to\repo `
  --prompt-file .\task.txt `
  --json
```

The headless profile creates a fresh persistent Agent each time.

## Model tracks

| Model | Intended use | Verified here |
| --- | --- | --- |
| `deepseek-v4-pro` | Higher-capability coding and analysis | Route visibility |
| `deepseek-v4-flash` | Fast general coding work | Live text response |
| `deepseek-v4-flash-vision-exp` | Text plus image input | Capability metadata |

The default model comes from `$DSH_HOME/settings.yaml` under `agent-default-model`. Changing it affects Agents created afterward; existing sessions keep their recorded model.

## Verification

1. Run `status --json` and confirm version, provider, model IDs, and credential presence.
2. Review the target repository instructions, current changes, and test commands.
3. Start one headless task with an explicit directory and prompt.
4. Check the returned response and any newly created session entries.
5. Inspect actual file changes and run the repository's own tests.

After installation or an upgrade:

```powershell
python .\scripts\dsh_session.py smoke-test `
  --dir C:\path\to\safe-dir --json
```

A text-only request cannot confirm image handling. For the vision route, use a new TUI or Web session with a harmless test image.

## Using it from a coding agent

```text
Use $codex-dsh-session in C:\path\to\repo.
Check status, then run a headless task that explains the failing tests.
Do not edit files.
```

## Safety notes

- The API key value is never read into status output.
- The wrapper does not terminate unrelated DSH or Node processes.
- It does not commit, push, publish, or alter unrelated files.
- A response and exit code still need repository-level file and test inspection.

## Machine-readable contract

Every command accepts `--json`. The shared fields are `schema_version`, `ok`, `target`, `command`, `provider`, `workdir`, `session_id`, `requested_model`, `actual_model`, `result`, `warnings`, and `error`. Adapter-specific evidence remains alongside them.

## Related adapters

| Repository | Target |
| --- | --- |
| [Any-to-OpenCode](https://github.com/ZiChenWang114514/Any-to-OpenCode) | OpenCode |
| [Any-to-Grok-Build](https://github.com/ZiChenWang114514/Any-to-Grok-Build) | Grok Build |
| [Any-to-Kimi-Code](https://github.com/ZiChenWang114514/Any-to-Kimi-Code) | Kimi Code |
| [Any-to-ZCode](https://github.com/ZiChenWang114514/Any-to-ZCode) | ZCode / GLM |
| [Any-to-Codex](https://github.com/ZiChenWang114514/Any-to-Codex) | Codex CLI |
| [Any-to-Claude-Code](https://github.com/ZiChenWang114514/Any-to-Claude-Code) | Claude Code |
| [Any-to-Pi](https://github.com/ZiChenWang114514/Any-to-Pi) | Pi |
| [Any-to-Antigravity](https://github.com/ZiChenWang114514/Any-to-Antigravity) | Google Antigravity CLI |

## License

[MIT](./LICENSE)

<p align="center">
  <picture>
    <source media="(max-width: 680px)" srcset="./assets/readme/hero-mobile.svg">
    <img src="./assets/readme/hero.svg" width="100%" alt="Any-to-Pi connects compatible coding harnesses to exact Pi sessions">
  </picture>
</p>

<p align="center"><strong>English</strong> · <a href="./README.zh-CN.md">简体中文</a></p>

<p align="center">
  <a href="https://github.com/ZiChenWang114514/Any-to-Pi/actions/workflows/ci.yml"><img src="https://github.com/ZiChenWang114514/Any-to-Pi/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  · Windows · Python 3.11+ · MIT
</p>

# Any-to-Pi

Connect any compatible coding harness to the local [Pi coding agent](https://github.com/earendil-works/pi). The adapter starts a non-interactive task in an explicit workspace, returns one stable JSON object, and resumes or forks an exact Pi session ID.

It uses the user's existing Pi installation, authentication, extensions, and model configuration. It does not install Pi, copy credentials, or alter global settings.

## Proof first

```powershell
python .\scripts\pi_session.py status --json
```

The status command verifies the installed Pi version, OpenAI Codex OAuth readiness, `gpt-5.6-luna` availability, and the CLI flags required for JSON events, exact sessions, and fork.

## How it works

```text
Any compatible harness
        │
        ▼
scripts/pi_session.py
        │  pi --mode json --print
        ▼
Exact Pi session in the requested workspace
```

The Python adapter is the portable interface. `$codex-pi-session` is an optional Codex Skill wrapper around the same commands.

## Install

```powershell
git clone https://github.com/ZiChenWang114514/Any-to-Pi.git `
  "$env:USERPROFILE\.codex\skills\codex-pi-session"
```

Other harnesses can clone the repository anywhere and call `scripts/pi_session.py` directly.

## First successful run

```powershell
python .\scripts\pi_session.py invoke `
  --workdir C:\path\to\repo `
  --prompt "Inspect this repository and summarize its test commands." `
  --provider openai-codex `
  --model gpt-5.6-luna `
  --json
```

Omit `--provider` and `--model` to use the current Pi configuration.

## Exact session lifecycle

```powershell
python .\scripts\pi_session.py resume `
  --workdir C:\path\to\repo `
  --session-id <session-id> `
  --prompt "Continue from the previous result." `
  --json

python .\scripts\pi_session.py fork `
  --workdir C:\path\to\repo `
  --session-id <session-id> `
  --prompt "Explore an independent implementation." `
  --json
```

`resume` preserves the selected conversation. `fork` creates a new session from that history. Pi project sessions are workspace-specific, so both commands require the original working directory and exact ID.

## Machine-readable contract

Every command accepts `--json`. Shared fields are:

```text
schema_version · ok · target · command · provider · workdir
session_id · requested_model · actual_model · result · warnings · error
```

Success uses exit code `0`; execution or verification failure uses `1`; invalid CLI arguments use `2`.

## Verification

```powershell
python -m unittest discover -s tests -v
python .\scripts\pi_session.py smoke-test `
  --provider openai-codex --model gpt-5.6-luna --json
```

Unit tests use simulated events and require no credentials. The real smoke test creates temporary Git and session directories, disables tools and local extensions, then verifies a new session, exact resume, fork, requested model, and actual model.

Verified locally on 2026-08-28 with Pi `0.84.3`: new session, exact resume, and fork all returned the requested `openai-codex/gpt-5.6-luna` route.

## Operational notes

- Use `--isolated` for reproducible diagnostics without Pi extensions, skills, or context files.
- Use `--no-tools` for response-only checks; omit it for authorized coding work.
- The adapter never selects the most recent session automatically.
- Review actual file changes and project tests after an agentic task.
- Authentication data is never included in the JSON result.

## Related adapters

| Repository | Target |
|---|---|
| [Any-to-OpenCode](https://github.com/ZiChenWang114514/Any-to-OpenCode) | OpenCode |
| [Any-to-Grok-Build](https://github.com/ZiChenWang114514/Any-to-Grok-Build) | Grok Build |
| [Any-to-Kimi-Code](https://github.com/ZiChenWang114514/Any-to-Kimi-Code) | Kimi Code |
| [Any-to-ZCode](https://github.com/ZiChenWang114514/Any-to-ZCode) | ZCode / GLM |
| [Any-to-DeepSeek-Harness](https://github.com/ZiChenWang114514/Any-to-DeepSeek-Harness) | DeepSeek Harness |
| [Any-to-Codex](https://github.com/ZiChenWang114514/Any-to-Codex) | Codex CLI |
| [Any-to-Claude-Code](https://github.com/ZiChenWang114514/Any-to-Claude-Code) | Claude Code |
| [Any-to-Pi](https://github.com/ZiChenWang114514/Any-to-Pi) | Pi |

## License

MIT. This independent adapter is not affiliated with the Pi project or OpenAI.

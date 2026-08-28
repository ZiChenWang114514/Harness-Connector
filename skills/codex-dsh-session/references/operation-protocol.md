# Operation protocol

## Model source

DeepSeek Harness `0.1.1-rc.2` advertises `deepseek-v4-flash`, `deepseek-v4-pro`, and `deepseek-v4-flash-vision-exp` from its built-in `dsh-llm-deepseek` adapter. The vision entry declares text and image input. A user `llm-deepseek.models` list replaces that built-in list, so status reports both expected and discovered values.

## Status

`status` reads only version text and non-secret settings. It checks whether `DEEPSEEK_API_KEY` exists but never reads or emits the value.

## Headless invocation

`invoke` calls `dsh --profile headless <task>` from an explicit directory. The profile creates a fresh persistent Agent and prints the final assistant text. The helper compares the session directory before and after the call and reports newly created entries.

Current headless CLI behavior does not offer an exact resume argument. Continue a known session through the TUI or Web profile, using its full identifier and original workspace.

## Smoke test

The test uses a temporary `DSH_HOME`, links the installed profile tree, copies only non-secret settings, inherits the already-present API-key environment variable, and removes the temporary home afterward. A text test of the vision route verifies routing but does not prove image handling.

## Result interpretation

Treat the response, process exit, new session ID, file changes, and project tests as separate observations. Check all observations relevant to the requested task before reporting success.

# Operation protocol

All machine-readable commands use schema version 1. The provider is selected for each invocation. `official` removes third-party provider variables only from the child process and relies on Claude authentication. `deepseek` maps `DEEPSEEK_API_KEY` to the Anthropic-compatible child process without printing or storing the value.

`invoke` creates a Claude Code print-mode session. `resume` requires an exact session ID. The adapter returns the final response, requested and actual model, exit status, and a sanitized error.

The smoke test uses a temporary Git repository and `plan` permission mode. It verifies an exact reply marker. Run it once for DeepSeek V4 Pro and once for V4 Flash after changing credentials or Claude Code versions.

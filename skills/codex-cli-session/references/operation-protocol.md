# Operation protocol

All machine-readable commands use schema version 1. A successful result includes the target, command, work directory, requested and actual model, exact session ID, final result, warnings, and a null error.

`invoke` creates a session with `codex exec --json`. `resume` and `fork` require an exact thread ID. The adapter never selects the latest session automatically. A timeout or nonzero CLI exit returns `ok: false` and a concise error without authentication data.

The smoke test creates a temporary Git repository, verifies a new session, resumes the same thread, forks it, and then removes the temporary workspace. Codex session history remains available under the user's ordinary Codex storage.

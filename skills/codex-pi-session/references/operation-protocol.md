# Operation protocol

## Shared result

Every command supports `--json` and returns one object with these stable fields:

`schema_version`, `ok`, `target`, `command`, `provider`, `workdir`, `session_id`, `requested_model`, `actual_model`, `result`, `warnings`, and `error`.

Exit code `0` means success, `1` means execution or verification failed, and `2` means the command arguments are invalid.

## Session identity

Pi project sessions belong to a working directory. `resume` and `fork` therefore require both `--workdir` and an exact `--session-id`. An optional `--session-dir` provides a caller-controlled session store.

## Isolation

`--isolated` disables extensions, skills, and context files for reproducible diagnostics. `--no-tools` also disables coding tools. The real smoke test uses both options and a temporary Git workspace.

## Authentication

The adapter reads Pi's existing authentication state. It does not copy, print, or persist OAuth tokens or API keys.

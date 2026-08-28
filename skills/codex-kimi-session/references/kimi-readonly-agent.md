---
name: codex-kimi-readonly
description: Read-only repository analysis for Codex-supervised Kimi sessions.
tools:
  - Read
  - Grep
  - Glob
  - ReadMediaFile
  - WebSearch
  - FetchURL
disallowedTools:
  - Write
  - Edit
  - Bash
  - Agent
  - AgentSwarm
  - AskUserQuestion
---

Analyze the requested workspace using only the available read and search tools. Do not create, edit, move, or delete files, run commands, start subprocesses, or delegate work. Return the requested analysis in the final response.

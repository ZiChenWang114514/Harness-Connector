# Initial import report

Import date: 2026-08-28

The first Harness Connector snapshot was assembled from three read-only inputs: each public source repository at the exact commit below, its corresponding local project checkout, and the installed local Skill snapshot. All eight local project checkouts were on the same commit as public `main`. Seven were clean. ZCode contained three tested working-tree updates, which were copied into this collection without changing the source checkout.

| Skill | Public source | Imported commit | Local project state | Collection-specific import note |
|---|---|---|---|---|
| `codex-opencode-session` | `Any-to-OpenCode` | `b9d6c89f1e62cc0052b77ad2c046b6604cf9ca48` | Clean | Uses the current project adapter so the unified JSON contract and its tests remain paired. |
| `codex-grok-build` | `Any-to-Grok-Build` | `e18d10c65180f5ad8fcbf851b458ce926b59d0f2` | Clean | Uses the current project adapter so the unified JSON contract and its tests remain paired. |
| `codex-kimi-session` | `Any-to-Kimi-Code` | `f7f1dddfa8aa7ea05d5b6203a1b13344779d5f8b` | Clean | Uses the current project adapter and project SVG files so code, tests, and documentation agree. |
| `codex-zcode-session` | `Any-to-ZCode` | `497f678de9544f70987052d4589e75bb506a3e4b` | Three tested modifications | Added GLM-5-Turbo defaults, Windows multiline prompt preservation, actual-model reporting, isolated `ZCODE_HOME` sessions, and their tests. |
| `codex-dsh-session` | `Any-to-DeepSeek-Harness` | `a6d99e6ca57e885f67555d1105572115f1f6912b` | Clean | Runtime files use the installed Skill snapshot. |
| `codex-cli-session` | `Any-to-Codex` | `adff954419a8042d391bdf2fdd14aa02e06ddc28` | Clean | Runtime files use the installed Skill snapshot. |
| `codex-claude-session` | `Any-to-Claude-Code` | `f8a476863d186512fb4c784cea5dc18547f6ae0a` | Clean | Runtime files use the installed Skill snapshot. |
| `codex-pi-session` | `Any-to-Pi` | `7306fe198ef3ea77b4c444fadcfb73d57babee45` | Clean | Runtime files use the installed Skill snapshot after the recorded GPT-5.6 Luna smoke test. |

## Installed-snapshot differences

The installed Skill snapshots differed from public `main` in documentation, agent metadata, and several runtime files. Import validation found that three older installed adapters no longer matched their current project tests, so OpenCode, Grok Build, and Kimi Code use the clean local project versions at the recorded public commits. The remaining verified local runtime changes were retained, including the three ZCode modifications described above. Generated Python bytecode was excluded. The source commits remain recorded so future changes can be reviewed with `tools/sync_from_sources.py --check`.

## Verification meaning

- `source-recorded`: the source project contains its earlier automated or real-call evidence; this import does not repeat billable calls.
- `local-real-smoke`: the imported local update was exercised against the named live model before aggregation.

No credential, private session transcript, machine-specific log, or personal absolute path is included in the catalog or this report.

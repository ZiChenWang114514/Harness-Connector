<p align="center">
  <picture>
    <source media="(max-width: 640px)" srcset="assets/readme/hero-mobile.svg">
    <img src="assets/readme/hero.svg" width="100%" alt="Harness Connector 将八个独立的编码 Harness 会话 Skill 连接到准确的 CLI 工作目录、模型和会话。">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/ZiChenWang114514/Harness-Connector/actions/workflows/ci.yml"><img src="https://github.com/ZiChenWang114514/Harness-Connector/actions/workflows/ci.yml/badge.svg" alt="CI 状态"></a>
  <a href="skills/"><img src="https://img.shields.io/badge/session_skills-8-5BA8FF" alt="8 个会话 Skill"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-64E6C4" alt="MIT 许可证"></a>
  <br>
  <a href="README.md">English</a>
</p>

Harness Connector 汇集八个已经投入使用的编码 Harness 会话 Skill，同时保留各自独立的运行脚本、会话规则、模型检查、文档、测试与调用名称。你可以单独复制一个 Skill，也可以把整个仓库作为 Codex 插件包使用。

## Skill 目录

<!-- skill-matrix:start -->
| Skill | Target Harness | Commands | Source | Verification |
|---|---|---|---|---|
| [`$codex-opencode-session`](skills/codex-opencode-session/) | OpenCode | `status`, `free-pool`, `invoke`, `smoke-test` | [Any-to-OpenCode](https://github.com/ZiChenWang114514/Any-to-OpenCode) @ `0c256494` | `local-real-smoke` |
| [`$codex-grok-build`](skills/codex-grok-build/) | Grok Build | `status`, `list`, `inspect`, `wait`, `invoke`, `smoke-test` | [Any-to-Grok-Build](https://github.com/ZiChenWang114514/Any-to-Grok-Build) @ `70026ddc` | `local-real-smoke` |
| [`$codex-kimi-session`](skills/codex-kimi-session/) | Kimi Code | `status`, `inspect`, `invoke`, `smoke-test` | [Any-to-Kimi-Code](https://github.com/ZiChenWang114514/Any-to-Kimi-Code) @ `f7f1dddf` | `source-recorded` |
| [`$codex-zcode-session`](skills/codex-zcode-session/) | ZCode | `status`, `invoke`, `smoke-test` | [Any-to-ZCode](https://github.com/ZiChenWang114514/Any-to-ZCode) @ `497f678d` | `local-real-smoke` |
| [`$codex-dsh-session`](skills/codex-dsh-session/) | DeepSeek Harness | `status`, `invoke`, `smoke-test` | [Any-to-DeepSeek-Harness](https://github.com/ZiChenWang114514/Any-to-DeepSeek-Harness) @ `a6d99e6c` | `source-recorded` |
| [`$codex-cli-session`](skills/codex-cli-session/) | Codex CLI | `status`, `invoke`, `resume`, `fork`, `smoke-test` | [Any-to-Codex](https://github.com/ZiChenWang114514/Any-to-Codex) @ `1a4a2923` | `local-real-smoke` |
| [`$codex-claude-session`](skills/codex-claude-session/) | Claude Code | `status`, `invoke`, `resume`, `smoke-test` | [Any-to-Claude-Code](https://github.com/ZiChenWang114514/Any-to-Claude-Code) @ `f8a47686` | `source-recorded` |
| [`$codex-pi-session`](skills/codex-pi-session/) | Pi | `status`, `invoke`, `resume`, `fork`, `smoke-test` | [Any-to-Pi](https://github.com/ZiChenWang114514/Any-to-Pi) @ `7306fe19` | `source-recorded` |
<!-- skill-matrix:end -->

验证标签描述从各来源项目导入的证据；本次首次聚合不会产生新的付费模型调用。

## 项目价值

- **保持独立：** ZCode 的调整不会悄然改变 Pi、Claude Code 或其他适配器。
- **保持兼容：** 八个现有 Skill ID、命令与参数继续有效。
- **来源清楚：** 每份快照都记录公开来源仓库及准确的 `main` 提交。
- **维护可复现：** 工具可以检查目录、重新生成目录表，并报告来源仓库的新提交。
- **不保存凭据：** CI 运行单元测试和模拟子进程；真实模型凭据始终位于仓库之外。

## 目录结构

```text
Harness-Connector/
├─ .codex-plugin/plugin.json
├─ skills/<skill-id>/
├─ catalog/skills.json
├─ tools/
├─ tests/
├─ docs/
└─ .github/workflows/ci.yml
```

`skills/` 中的每个目录都是可以单独使用的完整项目快照。各 Harness 的运行代码仍然彼此独立。

## 单独使用一个 Skill

把所需目录复制到 Codex Skill 目录，并保持目录名不变。例如在 PowerShell 中安装 Pi Skill：

```powershell
Copy-Item -Recurse `
  .\skills\codex-pi-session `
  "$env:USERPROFILE\.codex\skills\codex-pi-session"
```

安装后重新启动 Codex。调用名称仍为 `$codex-pi-session`，其余七个 Skill 采用同样规则。

## 作为插件包使用

根清单只声明 `./skills/`，没有注册 MCP、Hook、应用或外部服务。插件安装需要使用宿主支持的仓库安装方式；仅克隆本仓库不会改变本机 Codex 配置。

## 验证合集

```powershell
python tools/audit_skills.py
python tools/generate_catalog.py --check
python -m unittest discover -s tests -v
```

每个适配器的原始测试仍保存在 `skills/<skill-id>/tests/`。

## 同步来源项目

检查八个来源仓库是否出现新提交：

```powershell
python tools/sync_from_sources.py --check
```

从公开来源仓库更新某一个合集快照：

```powershell
python tools/sync_from_sources.py --apply --skill codex-pi-session
```

更新命令只会写入当前合集仓库。提交前应当审阅差异并运行测试；本机 Codex Skill 与八个来源仓库均不会被修改。

## 文档

- [导入报告](docs/import-report.md)
- [自动生成的 Skill 目录](docs/skill-catalog.md)
- [贡献指南](CONTRIBUTING.md)
- [更新记录](CHANGELOG.md)

## 许可证

Harness Connector 使用 [MIT License](LICENSE)。各项目原有的许可证与声明继续保存在相应 Skill 快照中。

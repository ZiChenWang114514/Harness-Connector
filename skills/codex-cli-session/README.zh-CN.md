<p align="center">
  <picture>
    <source media="(max-width: 680px)" srcset="./assets/readme/hero-mobile.svg">
    <img src="./assets/readme/hero.svg" width="100%" alt="Any-to-Codex：把任意兼容编码助手接到准确的 Codex CLI 会话">
  </picture>
</p>

<p align="center"><a href="./README.md">English</a> · <strong>简体中文</strong></p>

<p align="center">
  <a href="https://github.com/ZiChenWang114514/Any-to-Codex/actions/workflows/ci.yml"><img src="https://github.com/ZiChenWang114514/Any-to-Codex/actions/workflows/ci.yml/badge.svg" alt="CI 状态"></a>
  · Windows · Python 3.11+ · MIT
</p>

# Any-to-Codex

把任意兼容的编码助手接到本机 Codex CLI。适配器会在明确的工作目录中启动非交互任务，返回稳定的 JSON 结果，并按照准确线程 ID 继续或分叉会话。

它使用用户现有的 ChatGPT 登录和 Codex 配置，不负责安装 Codex、复制凭据、改变全局模型或绕过 Codex 权限。

## 先看实际状态

```powershell
python .\scripts\codex_session.py status --json
```

状态命令检查 CLI、ChatGPT 登录、当前默认模型，以及 JSONL 执行、结构化输出、模型选择和临时测试所需的参数。

## 工作方式

```text
任意兼容 Harness
      │
      ▼
scripts/codex_session.py
      │  codex exec --json
      ▼
指定工作目录中的准确 Codex 线程
```

Python 适配器是通用接口；`$codex-cli-session` 是使用同一组命令的 Codex Skill 封装。

## 安装

```powershell
git clone https://github.com/ZiChenWang114514/Any-to-Codex.git `
  "$env:USERPROFILE\.codex\skills\codex-cli-session"
```

其他 Harness 可以把仓库克隆到任意位置，直接调用 `scripts/codex_session.py`。

## 第一次调用

```powershell
python .\scripts\codex_session.py invoke `
  --workdir C:\path\to\repo `
  --prompt "检查这个仓库并总结测试命令。" `
  --sandbox read-only `
  --json
```

没有传入 `--model` 时，模型沿用用户自己的 Codex 配置。

## 准确会话流程

```powershell
python .\scripts\codex_session.py resume `
  --session-id <thread-id> `
  --prompt "根据上一轮结果继续。" `
  --json

python .\scripts\codex_session.py fork `
  --session-id <thread-id> `
  --prompt "独立研究另一种实现。" `
  --json
```

`resume` 延续原对话；`fork` 从指定历史创建新线程。两者都要求准确 ID。

## 机器可读结果

每个命令都支持 `--json`，统一字段为：

```text
schema_version · ok · target · command · provider · workdir
session_id · requested_model · actual_model · result · warnings · error
```

成功使用退出码 `0`，执行或验证失败使用 `1`，无效参数使用 `2`。

## 验证

```powershell
python -m unittest discover -s tests -v
python .\scripts\codex_session.py smoke-test --json
```

单元测试不需要凭据。真实测试会创建临时 Git 工作目录，并使用当前 ChatGPT 登录所提供的 Codex 模型验证新线程、准确继续和分叉。

## 使用说明

- 只读分析使用 `--sandbox read-only`，获得实施许可后使用 `workspace-write`。
- 只有明确不需要保存会话时才使用 `--ephemeral`。
- 适配器不会自动选择最近会话。
- Agent 执行任务后仍需检查实际文件变化与项目测试。
- 不输出认证信息和完整 Codex 配置。

## 相关适配器

| 仓库 | 目标 |
|---|---|
| [Any-to-OpenCode](https://github.com/ZiChenWang114514/Any-to-OpenCode) | OpenCode |
| [Any-to-Grok-Build](https://github.com/ZiChenWang114514/Any-to-Grok-Build) | Grok Build |
| [Any-to-Kimi-Code](https://github.com/ZiChenWang114514/Any-to-Kimi-Code) | Kimi Code |
| [Any-to-ZCode](https://github.com/ZiChenWang114514/Any-to-ZCode) | ZCode / GLM |
| [Any-to-DeepSeek-Harness](https://github.com/ZiChenWang114514/Any-to-DeepSeek-Harness) | DeepSeek Harness |
| [Any-to-Claude-Code](https://github.com/ZiChenWang114514/Any-to-Claude-Code) | Claude Code |
| [Any-to-Claude-Code](https://github.com/ZiChenWang114514/Any-to-Claude-Code) | Claude Code |
| [Any-to-Claude-Code](https://github.com/ZiChenWang114514/Any-to-Claude-Code) | Claude Code |

## License

MIT。本仓库是独立适配器，不是 OpenAI 官方产品。

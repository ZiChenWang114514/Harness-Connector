<p align="center">
  <picture>
    <source media="(max-width: 680px)" srcset="./assets/readme/hero-mobile.svg">
    <img src="./assets/readme/hero.svg" width="100%" alt="Any-to-Claude-Code：把任意兼容编码助手接到准确的 Claude Code 会话">
  </picture>
</p>

<p align="center"><a href="./README.md">English</a> · <strong>简体中文</strong></p>

<p align="center">
  <a href="https://github.com/ZiChenWang114514/Any-to-Claude-Code/actions/workflows/ci.yml"><img src="https://github.com/ZiChenWang114514/Any-to-Claude-Code/actions/workflows/ci.yml/badge.svg" alt="CI 状态"></a>
  · Windows · Python 3.11+ · MIT
</p>

# Any-to-Claude-Code

把任意兼容的编码助手接到本机 Claude Code 会话。适配器默认支持 Claude 官方订阅，也可以明确选择兼容 Anthropic 接口的 DeepSeek V4 Pro 与 V4 Flash。

Provider 选择只影响当前 Claude 子进程。仓库不会保存 API Key，也不会改写用户的长期 Claude 设置。

## 先看实际状态

```powershell
python .\scripts\claude_session.py status --provider official --json
python .\scripts\claude_session.py status --provider deepseek --model pro --json
```

官方状态检查 Claude 登录；DeepSeek 状态只报告 `DEEPSEEK_API_KEY` 是否存在，并核对本机 CLI 是否支持 print、JSON、准确继续、模型选择和权限模式。

## Provider 线路

| Provider | 认证方式 | 模型 | 用途 |
|---|---|---|---|
| `official` | Claude Pro、Max、Team、Enterprise 或 Console 登录 | 账号默认模型或 `--model` | 公开默认方式 |
| `deepseek` | 子进程继承 `DEEPSEEK_API_KEY` | `deepseek-v4-pro[1m]`、`deepseek-v4-flash` | 明确选择的兼容线路 |

DeepSeek 使用官方说明中的 `https://api.deepseek.com/anthropic`。

## 工作方式

```text
任意兼容 Harness
      │
      ▼
scripts/claude_session.py
      │
      ├── Claude 官方订阅
      └── DeepSeek Anthropic API
                │
                ▼
准确的 Claude Code 会话
```

## 安装

```powershell
git clone https://github.com/ZiChenWang114514/Any-to-Claude-Code.git `
  "$env:USERPROFILE\.codex\skills\codex-claude-session"
```

其他 Harness 可以把仓库克隆到任意位置，直接调用 Python 脚本。

## 第一次调用

官方订阅：

```powershell
python .\scripts\claude_session.py invoke `
  --workdir C:\path\to\repo `
  --prompt "检查这个仓库并总结测试命令。" `
  --permission-mode plan `
  --json
```

DeepSeek V4 Pro：

```powershell
python .\scripts\claude_session.py invoke `
  --provider deepseek --model pro `
  --workdir C:\path\to\repo `
  --prompt "检查这个仓库并总结测试命令。" `
  --permission-mode plan `
  --json
```

快速线路使用 `--model flash`。

## 继续准确会话

```powershell
python .\scripts\claude_session.py resume `
  --provider deepseek --model flash `
  --session-id <session-id> `
  --prompt "根据已经核验的结果继续。" `
  --json
```

自动继续时明确写出 provider、模型和会话 ID。适配器不会选择最近会话。

## 机器可读结果

每个命令都支持 `--json`，统一字段为：

```text
schema_version · ok · target · command · provider · workdir
session_id · requested_model · actual_model · result · warnings · error
```

各适配器自己的验证信息会与统一字段一同保留。

## 验证

```powershell
python -m unittest discover -s tests -v
python .\scripts\claude_session.py smoke-test --provider deepseek --model pro --json
python .\scripts\claude_session.py smoke-test --provider deepseek --model flash --json
```

单元测试无需凭据，用于核对 provider 隔离和响应解析。真实测试使用临时 Git 工作目录和固定回复标记。

## 凭据处理

- 公开默认方式是 Claude 官方订阅。
- 只有传入 `--provider deepseek` 才会启用 DeepSeek。
- `DEEPSEEK_API_KEY` 只在子进程环境中映射为 `ANTHROPIC_AUTH_TOKEN`。
- 密钥不会显示、写入 Claude 设置或进入提交。
- 官方模式只会从其子进程中移除第三方 provider 变量。

## 相关适配器

| 仓库 | 目标 |
|---|---|
| [Any-to-OpenCode](https://github.com/ZiChenWang114514/Any-to-OpenCode) | OpenCode |
| [Any-to-Grok-Build](https://github.com/ZiChenWang114514/Any-to-Grok-Build) | Grok Build |
| [Any-to-Kimi-Code](https://github.com/ZiChenWang114514/Any-to-Kimi-Code) | Kimi Code |
| [Any-to-ZCode](https://github.com/ZiChenWang114514/Any-to-ZCode) | ZCode / GLM |
| [Any-to-DeepSeek-Harness](https://github.com/ZiChenWang114514/Any-to-DeepSeek-Harness) | DeepSeek Harness |
| [Any-to-Codex](https://github.com/ZiChenWang114514/Any-to-Codex) | Codex CLI |

## License

MIT。本仓库是独立适配器，不是 Anthropic 或 DeepSeek 官方产品。

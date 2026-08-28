---
name: codex-claude-session
description: 在用户要求检查、启动、继续或排查本机 Claude Code 会话，或希望通过官方订阅或 DeepSeek Anthropic API 调用 Claude Code 时使用；覆盖 Windows 非交互调用、准确会话恢复、provider 隔离和真实测试。不用于安装、升级或登录 Claude Code。
---

# Claude Code Session

将 Claude Code 作为可由任意兼容 Harness 调用的本机编码协作者。公开默认方式为 Claude 官方订阅；用户明确选择 DeepSeek 时才启用 DeepSeek provider。

## 状态检查

```powershell
python <skill-dir>\scripts\claude_session.py status --provider official --json
python <skill-dir>\scripts\claude_session.py status --provider deepseek --model pro --json
```

`official` 检查 Claude 登录；`deepseek` 只检查 `DEEPSEEK_API_KEY` 是否存在，不输出其内容。

## 调用与继续

```powershell
python <skill-dir>\scripts\claude_session.py invoke `
  --workdir <repo> --prompt-file <task.txt> --json

python <skill-dir>\scripts\claude_session.py invoke `
  --provider deepseek --model pro --workdir <repo> `
  --prompt-file <task.txt> --json

python <skill-dir>\scripts\claude_session.py resume `
  --provider deepseek --model flash --session-id <id> `
  --prompt-file <next.txt> --json
```

DeepSeek 模式只在 Claude 子进程环境中设置兼容地址与令牌。不要把密钥写入 Claude 设置、提示文件、日志或仓库。默认权限模式沿用 Claude Code；只读分析使用 `--permission-mode plan`。

## 真实测试

```powershell
python <skill-dir>\scripts\claude_session.py smoke-test `
  --provider deepseek --model pro --json
python <skill-dir>\scripts\claude_session.py smoke-test `
  --provider deepseek --model flash --json
```

收到结果后独立检查模型、回复标记、会话 ID 与工作目录。详细字段见 [references/operation-protocol.md](references/operation-protocol.md)。

## 操作要求

- 只在用户许可的目录和任务范围中运行。
- 保留已有文件与无关修改，不自行提交、推送、发布或部署。
- 官方订阅与 DeepSeek provider 每次调用独立选择，不修改长期配置。
- 不输出 API Key、认证头或完整 provider 配置。

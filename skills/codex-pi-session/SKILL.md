---
name: codex-pi-session
description: 在用户要求检查、启动、继续、分叉或排查本机 Pi 会话，或希望让其他编码助手调用 Pi 时使用；覆盖非交互 JSONL、准确会话 ID、模型核验与隔离测试。不用于安装、升级、登录或修改 Pi 全局配置。
---

# Pi Session

将 Pi 作为可由任意兼容 Harness 调用的本机编码协作者。开始前确认工作目录、任务内容、已有修改和验证命令。

## 状态检查

```powershell
python <skill-dir>\scripts\pi_session.py status --json
```

结果需要确认 Pi 版本、OpenAI Codex OAuth 状态、`gpt-5.6-luna` 可用性，以及 JSON、会话与 fork 参数。不要显示认证信息。

## 调用与继续

```powershell
python <skill-dir>\scripts\pi_session.py invoke `
  --workdir <repo> --prompt-file <task.txt> --json

python <skill-dir>\scripts\pi_session.py resume `
  --workdir <repo> --session-id <session_id> `
  --prompt-file <next.txt> --json

python <skill-dir>\scripts\pi_session.py fork `
  --workdir <repo> --session-id <session_id> `
  --prompt-file <branch-task.txt> --json
```

未指定 provider 与 model 时沿用用户当前的 Pi 配置。需要固定路由时显式传入 `--provider openai-codex --model gpt-5.6-luna`。继续与 fork 必须同时给出原工作目录和准确 ID。

## 真实测试

首次使用或 Pi 更新后运行：

```powershell
python <skill-dir>\scripts\pi_session.py smoke-test `
  --provider openai-codex --model gpt-5.6-luna --json
```

测试使用临时 Git 目录、独立会话目录、关闭扩展与工具，验证新会话、准确续接和 fork。完成后检查 `requested_model` 与 `actual_model` 均为 `gpt-5.6-luna`。

## 操作要求

- 仅在用户指定的目录执行任务，保留原有文件与无关修改。
- 不自行安装、升级、登录、提交、推送、发布、部署或更改全局配置。
- 超时后检查准确会话状态，再决定是否继续，避免重复发送相同任务。
- 代理完成编码后，需要检查文件差异与项目测试，不能只依赖最终文字或退出码。

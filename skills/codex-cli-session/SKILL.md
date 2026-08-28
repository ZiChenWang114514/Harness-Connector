---
name: codex-cli-session
description: 在用户要求检查、启动、继续、分叉或排查本机 Codex CLI 会话，或希望让其他编码助手调用 Codex 时使用；覆盖 ChatGPT 登录状态、非交互 JSONL、准确会话 ID 和隔离测试。不用于安装、升级或修改 Codex 全局配置。
---

# Codex CLI Session

将 Codex CLI 作为可由任意兼容 Harness 调用的本机编码协作者。开始前确认准确工作目录、任务范围、已有修改和测试命令。

## 状态检查

```powershell
python <skill-dir>\scripts\codex_session.py status --json
```

状态结果应确认 CLI 版本、ChatGPT 登录、默认模型以及 `exec` 所需参数。模型默认使用用户自己的 Codex 配置；只有用户明确指定时才传递 `--model`。

## 调用与继续

```powershell
python <skill-dir>\scripts\codex_session.py invoke `
  --workdir <repo> --prompt-file <task.txt> --json

python <skill-dir>\scripts\codex_session.py resume `
  --session-id <thread_id> --prompt-file <next.txt> --json

python <skill-dir>\scripts\codex_session.py fork `
  --session-id <thread_id> --prompt-file <branch-task.txt> --json
```

默认使用 `workspace-write`。只读分析传入 `--sandbox read-only`。不要使用模糊的最近会话选择；继续和分叉必须提供准确 ID。收到结果后检查实际文件差异与测试，不能只依赖最终文字或退出码。

## 真实测试

首次使用或 CLI 更新后运行：

```powershell
python <skill-dir>\scripts\codex_session.py smoke-test --json
```

测试在临时 Git 工作目录中验证新会话、准确继续和分叉。详细字段与错误分类见 [references/operation-protocol.md](references/operation-protocol.md)。

## 操作要求

- 只在用户许可的目录执行任务，保留已有文件与无关修改。
- 不自行安装、升级、登录、提交、推送、发布、部署或修改全局配置。
- 不显示认证信息、完整本机配置或敏感环境变量。
- 超时后检查准确会话状态，再决定是否继续；不要重复发送同一任务。

---
name: codex-kimi-session
description: 在用户要求连接、启动、继续、监督、检查或排查本机 Kimi Code CLI 会话，或希望将 Kimi 作为外部编码协作者时使用；覆盖 Windows 非交互调用、准确会话恢复、只读分析、模型核验和隔离式真实测试。不用于安装、升级、登录或操作 Kimi TUI。
---

# Codex Kimi Session

将 Kimi Code CLI 作为本机外部编码协作者使用。Codex 负责理解任务、确认工作目录、检查现有改动并独立验证结果；Kimi 在用户授权的目录中执行明确任务。

## 开始前

1. 运行只读状态检查：

   ```powershell
   python <skill-dir>\scripts\kimi_session.py status --json
   ```

2. 确认准确工作目录和 Kimi 需要完成的任务。先阅读该目录适用的项目说明、`git status --short`、现有差异与测试命令，保留已有修改。
3. 安装、升级、登录、修改供应商、改动长期配置、公开分享、提交、推送、发布、部署或批量处理会话，需要用户明确授权。
4. 不要按进程名终止 Kimi。辅助脚本只会在超时时终止自己启动的子进程及其后代。

## 调用 Kimi

长提示先写入 UTF-8 文件，再运行：

```powershell
python <skill-dir>\scripts\kimi_session.py invoke `
  --dir <repo> --prompt-file <prompt.txt> --json
```

Kimi 的 `-p` 模式会自动处理普通工具许可，适合已经确认目录和任务的无人值守执行。成功结果包含 `session_id`、实际模型、Agent 配置、最终回复和工具调用摘要；正式会话默认保留。

继续指定会话时使用准确 ID，并保持原工作目录：

```powershell
python <skill-dir>\scripts\kimi_session.py invoke `
  --dir <repo> --session-id <session_id> --prompt-file <prompt.txt> --json
```

新建只读分析会话时添加 `--mode readonly`。该模式使用随 Skill 提供的 Agent 文件，只开放读取、检索和网页查询工具。Kimi 不支持在非交互提示中临时切换已有会话的 Agent，因此只读模式不能与 `--session-id` 同用。

用户临时指定模型时添加 `--model <alias>`；未指定时读取 Kimi 自己的 `config.toml`，不在本 Skill 中复制默认模型。模型、Agent、附加目录和自定义 Skill 目录只适用于新会话。

## 检查与继续

收到回复后检查实际文件差异、进程状态和测试结果。Kimi 的自述、退出状态或任务清单不能单独证明完成。

调用超时或结果异常时，先检查准确会话：

```powershell
python <skill-dir>\scripts\kimi_session.py inspect `
  --dir <repo> --session-id <session_id> --json
```

根据实际差异准备下一阶段说明，再用同一 `session_id` 继续。不要用 `--continue` 或“最近会话”进行自动化选择。

首次配置或版本变化后运行真实测试：

```powershell
python <skill-dir>\scripts\kimi_session.py smoke-test --dir <safe-dir> --json
```

测试会在临时 `KIMI_CODE_HOME` 中复制运行所需的最少配置与凭据，创建只读会话，核验固定回复、模型和可用工具，随后清理整个临时目录。现有会话索引不会被修改。

需要命令细节、会话文件、只读 Agent 和故障处理说明时，读取 [references/operation-protocol.md](references/operation-protocol.md)。

## 安全要求

- 只在用户授权的工作目录和任务范围内运行非交互 Kimi；不要让它访问额外目录，除非用户明确要求。
- 日志和回复不得显示凭据、认证文件内容、API 密钥或完整供应商配置。
- 继续会话前同时核验准确 ID 与工作目录。普通调用保留会话；不要自行编辑 `session_index.jsonl` 或删除正式会话目录。
- 保留已有文件与无关改动；不要擅自执行 commit、push、reset、clean、stash 或删除操作。
- Kimi TUI 通常运行在终端宿主内；不要使用桌面自动化向终端输入命令。

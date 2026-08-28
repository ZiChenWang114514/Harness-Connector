---
name: codex-dsh-session
description: 在用户要求配置、启动、检查、监督或排查本机 DeepSeek Harness，或希望使用 DeepSeek V4 Pro、V4 Flash、V4 Flash Vision 完成编码任务时使用；覆盖 Windows headless 调用、模型清单、会话识别和隔离测试。不用于开发 DSH 插件或 Python SDK。
---

# Codex DSH Session

将 DeepSeek Harness CLI 作为本机外部编码协作者。Codex 确认任务与工作目录，DSH 执行明确任务，Codex随后检查文件变化和项目测试。

## 开始前

运行只读状态检查：

```powershell
python <skill-dir>\scripts\dsh_session.py status --json
```

状态结果应核对 CLI 版本、当前默认模型、凭据是否存在，以及下列内置模型：

- `deepseek-v4-pro`
- `deepseek-v4-flash`
- `deepseek-v4-flash-vision-exp`，支持图片输入

DSH 的模型清单只是选择建议。真实请求成功后，才可以说明指定模型当前可用。

安装、升级、登录、插件增删、修改长期配置、提交、推送、公开分享、发布或部署需要用户明确提出。开始编码任务前还要阅读适用的项目说明、`git status --short`、已有差异和测试命令。

## 调用

长提示先写入 UTF-8 文件：

```powershell
python <skill-dir>\scripts\dsh_session.py invoke `
  --dir <repo> --prompt-file <prompt.txt> --json
```

辅助脚本调用 `dsh --profile headless`，记录调用前后的会话目录，并返回本次新出现的会话 ID。headless profile 每次创建新 Agent；当前 CLI 没有提供 headless 精确继续参数。需要继续既有会话时，应在 TUI 或 Web profile 中使用准确会话 ID，不要用模糊的最近会话选择。

当前默认模型来自 `$DSH_HOME/settings.yaml` 的 `agent-default-model`。模型变更影响之后创建的 Agent，不会改变已有会话的模型。

## 真实测试

首次配置、CLI 更新或脚本修改后运行：

```powershell
python <skill-dir>\scripts\dsh_session.py smoke-test `
  --dir <safe-dir> --json
```

测试在临时 `DSH_HOME` 中运行，使用固定短回复并在结束后删除临时会话。若缺少 `DEEPSEEK_API_KEY`，结果应报告 `model_access_not_configured`。

视觉模型的文字冒烟测试只能确认模型路由。需要验证图片能力时，使用 Web 或 TUI 新会话附加一张无敏感信息的测试图片，并核对实际回答。

## 操作要求

- headless profile 具有编码工具能力，只在用户许可的目录运行。
- 保留用户文件和无关改动，不自行执行 commit、push、reset、clean、stash 或批量删除。
- 不按进程名统一终止 dsh 或 Node；超时时只停止本次启动的进程树。
- 不输出 `DEEPSEEK_API_KEY`、凭据文件内容或认证头。
- 详细结果字段、模型来源与限制见 [references/operation-protocol.md](references/operation-protocol.md)。

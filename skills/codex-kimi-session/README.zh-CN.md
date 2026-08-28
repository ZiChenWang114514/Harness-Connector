<p align="center">
  <picture>
    <source media="(max-width: 680px)" srcset="./assets/readme/hero-mobile.svg">
    <img src="./assets/readme/hero.svg" width="100%" alt="Any-to-Kimi-Code：把任意兼容编码助手接到准确的 Kimi Code 会话">
  </picture>
</p>

<p align="center">
  <a href="./README.md">English</a> · <strong>简体中文</strong>
</p>

<p align="center">
  <a href="./LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-38bdf8?style=flat-square"></a>
  <img alt="Python 3.11 or newer" src="https://img.shields.io/badge/python-3.11%2B-34d399?style=flat-square">
  <img alt="Tested on Windows" src="https://img.shields.io/badge/tested-Windows-94a3b8?style=flat-square">
</p>

# Any-to-Kimi-Code

把任意兼容的编码助手接到本机 Kimi Code 会话。它在指定目录中启动、继续并检查无头 Kimi CLI 工作，然后返回结构化结果。

本仓库是本地会话适配器：一套 Python 命令行工具，外加 Codex Skill 封装。它不负责安装、升级或登录 Kimi Code，也不是月之暗面的官方产品。

## 它能做什么

- 只有在同时提供准确会话 ID 和原工作目录时，才继续正式会话。
- 新建会话时可明确选择 `readonly` 或 `build`。
- 返回请求模型、实际模型、权限模式、活动工具、工具调用名称，以及解析到的最后一条 assistant 文本。
- 在 Windows 超时时，只终止本次调用启动的进程树。
- 在临时 Kimi 数据目录中做隔离的真实冒烟测试。

Codex、Claude Code、Grok Build 等工具都可以直接调用 Python 脚本。安装 Skill 后，Codex 也可以使用 `$codex-kimi-session`。

## 工作方式

<p align="center">
  <img src="assets/readme/workflow.svg" width="100%" alt="先确认工作目录并检查状态，再选择新建或继续准确会话，最后核验仓库结果">
</p>

1. 明确项目目录，先运行 `status`。
2. 新任务创建新会话；不需要改文件时使用 `--mode readonly`。
3. 继续已有任务时，同时提供准确 `session_id` 与原工作目录。
4. 使用 `inspect` 查看会话元数据，再自行检查文件差异、测试结果和进程状态。

## 安装

需要 Windows 与 PowerShell、Python 3.11 或更高版本，以及已经安装并完成配置的 Kimi Code CLI。

```powershell
git clone https://github.com/ZiChenWang114514/Any-to-Kimi-Code.git `
  "$env:USERPROFILE\.codex\skills\codex-kimi-session"
```

克隆目标目录是 Codex Skill 标识 `codex-kimi-session`。其他编码助手可以直接运行 `scripts/kimi_session.py`。

CLI 的查找顺序是：`KIMI_CODE_EXE`、系统 `PATH`、`KIMI_CODE_HOME\bin`。Kimi 数据目录默认来自 `KIMI_CODE_HOME`；未设置时使用 Kimi 自身的默认位置。

```powershell
$KimiSkill = Join-Path $env:USERPROFILE ".codex\skills\codex-kimi-session"
$Runner = Join-Path $KimiSkill "scripts\kimi_session.py"
$Repo = "C:\path\to\your\repo"

python --version
kimi --version
```

## 最快开始

### 1. 检查本机状态

```powershell
python $Runner status --dir $Repo --json
```

`status` 会执行 `kimi --version`、`kimi doctor` 和 `kimi provider list`，读取会话索引并列举相关进程。`ok: true` 只表示这些检查通过，不能单独证明网络、凭据或真实推理可用。

### 2. 新建只读会话

```powershell
python $Runner invoke `
  --dir $Repo `
  --mode readonly `
  --prompt "阅读项目结构并指出高优先级问题，不修改文件。" `
  --json
```

省略 `--mode` 时，脚本内部采用 `build`。因此每次新建会话都请明确写出模式。

### 3. 检查准确会话

```powershell
$SessionId = "01234567-89ab-cdef-0123-456789abcdef"

python $Runner inspect `
  --dir $Repo `
  --session-id $SessionId `
  --json
```

脚本会核验索引中的唯一记录、会话目录位置，以及 `state.json` 中的会话 ID 和工作目录。

### 4. 继续同一会话

```powershell
python $Runner invoke `
  --dir $Repo `
  --session-id $SessionId `
  --prompt "继续检查 README 与实现是否一致。" `
  --json
```

继续会话时不要同时传入 `--mode`、`--model`、`--agent`、`--agent-file`、`--add-dir` 或 `--skills-dir`。这些参数只适用于新会话。

### 5. 明确授权后使用构建模式

```powershell
python $Runner invoke `
  --dir $Repo `
  --mode build `
  --prompt "按现有代码风格修复已确认的问题，并报告改动与验证结果。" `
  --json
```

构建模式可以修改工作目录。执行前请确认目录、任务范围和当前未提交改动。

## 四个命令

| 命令 | 用途 | 会调用真实模型 | 是否保留正式会话 |
|---|---|:---:|:---:|
| `status` | 检查 CLI、诊断信息、模型别名、会话数量和进程 | 否 | 否 |
| `invoke` | 新建或继续 Kimi 会话 | 是 | 是 |
| `inspect` | 检查一个准确会话的元数据 | 否 | 读取现有会话 |
| `smoke-test` | 在临时环境中进行真实调用 | 是 | 否 |

默认超时为 `1800` 秒，提示文本上限为 `24000` 个字符。长文本请使用 `--prompt-file`。

## `readonly` 的准确含义

`--mode readonly` 会加载本仓库附带的 Agent 配置：

| 可用能力 | 禁用能力 |
|---|---|
| `Read`、`Grep`、`Glob`、`ReadMediaFile` | `Write`、`Edit`、`Bash` |
| `WebSearch`、`FetchURL` | `Agent`、`AgentSwarm`、`AskUserQuestion` |

这不是离线模式，也不是操作系统级隔离。请用结果中的 `active_tools`、`disallowed_tools` 和 `tool_call_names` 核对实际情况。

## 隔离式真实测试

```powershell
python $Runner smoke-test --dir $Repo --json
```

该测试会：

- 创建临时 `KIMI_CODE_HOME` 与临时工作目录。
- 复制实际存在的 `config.toml`、`region`、`device_id` 和整个 `credentials` 目录。
- 发起真实认证模型调用，可能使用网络与账户配额。
- 正常退出后尝试删除临时副本；这不是安全擦除。
- 当前只比较主 `session_index.jsonl` 的 SHA-256，并未检查真实数据目录中的每个文件。
- 当前工具检查确认六个已知禁用工具未出现在活动列表中，并不验证精确允许列表。

请在你认可上述行为、并准备好相应账户用量时再运行。

## 如何判断任务是否完成

CLI 退出码为零、存在会话 ID、返回 assistant 文本或显示模型别名，都不足以单独说明编码任务已经完成。还需要检查：

- Git 工作区差异是否符合预期，是否保留了原有未提交内容。
- 测试、构建或目标命令是否真正成功。
- 应用、服务或页面的实际状态是否符合要求。
- Kimi 的文字结论能否由文件内容和运行结果支持。

`inspect` 返回的是会话元数据，不会替你完成项目核验。

## 敏感信息与本机数据

- 不要在提示、Agent 文件、路径名称或输出中放入密码、令牌和认证配置。
- `--prompt-file` 只是文本管理方式，不提供内容隐藏。
- 脚本会读取会话事件文件，再提取指定字段。
- 错误文本只处理部分常见令牌样式；最终回复、provider 信息和路径没有通用净化保证。
- 分享 JSON 前，请先检查工作目录、进程、provider、会话标题和模型回复等字段。
- 正式 `invoke` 会话会保留在 Kimi 的会话目录中。本项目没有提供删除会话命令。

## 已知限制

- 当前没有固定 Kimi Code CLI 版本，也没有公开的版本兼容列表。
- Kimi 的工具名称、事件格式或 Agent 解释方式发生变化时，解析与只读测试可能需要同步更新。
- Windows 超时时使用 `taskkill /PID ... /T /F` 处理本次启动的进程树；其他系统只终止直接子进程。
- `latest_workdir_session_id` 来自索引中最后一个匹配项，没有按时间字段排序，请勿据此自动选择恢复目标。
- 解析到的最后一条 assistant 文本来自事件流中的最后一条匹配记录，不代表项目验证已完成。

## 在编码助手中使用

```text
使用 $codex-kimi-session，在 C:\path\to\repo 新建 readonly 会话，
阅读完整项目并总结架构、风险和改进建议，不修改文件。
```

继续已有会话时提供准确 ID：

```text
使用 $codex-kimi-session，在 C:\path\to\repo 继续会话
01234567-89ab-cdef-0123-456789abcdef，检查上一次分析的进展。
```

## 项目结构

```text
.
├─ SKILL.md
├─ agents/openai.yaml
├─ scripts/kimi_session.py
├─ references/defaults.json
├─ references/kimi-readonly-agent.md
├─ references/operation-protocol.md
└─ assets/readme/
```

更详细的参数规则见 [`SKILL.md`](SKILL.md) 和 [`references/operation-protocol.md`](references/operation-protocol.md)。

## 机器可读结果

每个命令都支持 `--json`。统一字段包括 `schema_version`、`ok`、`target`、`command`、`provider`、`workdir`、`session_id`、`requested_model`、`actual_model`、`result`、`warnings` 和 `error`，并保留各适配器自己的验证信息。

## 同系列适配器

| 仓库 | 目标 |
| --- | --- |
| [Any-to-OpenCode](https://github.com/ZiChenWang114514/Any-to-OpenCode) | OpenCode |
| [Any-to-Grok-Build](https://github.com/ZiChenWang114514/Any-to-Grok-Build) | Grok Build |
| [Any-to-ZCode](https://github.com/ZiChenWang114514/Any-to-ZCode) | ZCode / GLM |
| [Any-to-DeepSeek-Harness](https://github.com/ZiChenWang114514/Any-to-DeepSeek-Harness) | DeepSeek Harness |
| [Any-to-Codex](https://github.com/ZiChenWang114514/Any-to-Codex) | Codex CLI |
| [Any-to-Claude-Code](https://github.com/ZiChenWang114514/Any-to-Claude-Code) | Claude Code |
| [Any-to-Pi](https://github.com/ZiChenWang114514/Any-to-Pi) | Pi |
| [Any-to-Antigravity](https://github.com/ZiChenWang114514/Any-to-Antigravity) | Google Antigravity CLI |

## 许可证

[MIT](./LICENSE) © 2026 Zichen Wang

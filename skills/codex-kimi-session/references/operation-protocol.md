# Kimi Code 操作说明

## 非交互调用

辅助脚本使用 `kimi -p <prompt> --output-format stream-json`。当前 Kimi Code 在提示模式中自动处理普通工具许可，因此执行类任务只能在用户已经授权的工作目录中启动。

`stream-json` 的稳定结果包括：

- `role=assistant`：模型回复；最后一条纯文本回复作为最终结果。
- `role=meta,type=system.version`：CLI 版本。
- `role=meta,type=session.resume_hint`：准确会话 ID。

脚本还会从会话自己的 `wire.jsonl` 仅读取模型别名、Agent 名称、思考强度、许可模式和工具名称，不读取或返回系统提示、用户消息与凭据。

## 模型与 Agent

默认模型来自 `$KIMI_CODE_HOME/config.toml` 的 `default_model`。单次新会话可用 `--model <alias>` 临时覆盖；继续已有会话时恢复原有 Agent 配置，不传模型或 Agent 参数。

`--mode readonly` 使用 `kimi-readonly-agent.md`，开放 `Read`、`Grep`、`Glob`、`ReadMediaFile`、`WebSearch` 和 `FetchURL`，并排除文件写入、命令执行和委派。辅助脚本仅为该子进程设置 Kimi 的 Agent 文件功能开关，不修改长期配置。

自定义 `--agent`、`--agent-file`、`--skills-dir` 和 `--add-dir` 只适用于新会话。使用项目提供的 Agent 或 Skill 前，应先检查其内容；这些文件可能改变系统提示与可用工具。

## 会话文件

默认数据目录为 `%USERPROFILE%\.kimi-code`，也可由 `KIMI_CODE_HOME` 指定。会话索引位于 `session_index.jsonl`，每条记录包含 `sessionId`、`workDir` 与 `sessionDir`。会话目录中的常用文件有：

- `state.json`：标题、创建时间、更新时间、工作目录和最近一次运行结果。
- `agents/main/wire.jsonl`：Agent 事件流，可用于恢复与检查模型、工具和运行状态。

自动化继续会话时必须同时匹配准确 `sessionId` 与规范化后的工作目录。不要自行改写索引，也不要根据标题或最近使用时间选择会话。

## 隔离式真实测试

`smoke-test` 会创建临时数据目录，只复制 `config.toml`、`credentials/`、`region` 和 `device_id` 中实际存在的项目。测试过程不会输出这些文件内容。固定回复、CLI 版本、模型和只读工具集合通过核验后，临时数据目录与测试会话一起清理。

Kimi 当前没有面向 CLI 的正式会话删除命令，因此不要在真实数据目录中创建测试会话后再直接编辑索引清理。

## 超时与排查

- 超时后，辅助脚本仅终止本次启动的进程树，并报告从标准输出或会话索引确认到的准确会话 ID。
- 使用 `inspect` 查看该会话的 `last_turn_reason`、更新时间、实际模型、许可模式与工具摘要，再判断是否继续。
- CLI 退出码为零仍需检查最终回复、文件差异和验收命令。
- `stream-json` 缺少最终回复时，先检查会话文件与实际差异，不要立即重复发送同一任务。
- 中文输出统一以 UTF-8 读取；脚本使用参数数组启动 Kimi，不经过命令行字符串拼接。
- 发现其他 Kimi TUI、Web 或 ACP 进程时保持不动。不要统一终止 `kimi.exe`。

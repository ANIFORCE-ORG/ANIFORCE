# Claude Agent SDK 学习目录

这个目录用于系统学习整个 `claude-agent-sdk-python`，不是只围绕 `ClaudeSDKClient`。后续所有学习代码、演示脚本、运行输出和阶段结论都放在这里，正式迁移代码前先把关键行为验证清楚。

## 目录

```text
drafts/260615_claude_sdk_learning/
  README.md                 # 本目录说明
  study_notes.md            # 持续更新的学习笔记
  examples/                 # 可运行演示代码
    01_query_quickstart.py  # 第 1 章：Quickstart
    02_agent_loop.py        # 第 2 章：Overview / Agent Loop
    sdk_learning_common.py  # drafts 学习脚本共享工具
  outputs/                  # 演示输出，必须脱敏
```

## 学习范围

- SDK 总览：SDK 是如何驱动 Claude Code agent loop 的。
- `query()`：单次任务入口、流式输出、适用边界。
- `ClaudeSDKClient`：交互式会话、connect/query/receive/disconnect。
- `ClaudeAgentOptions`：模型、cwd、system prompt、tools、permissions、MCP、session、环境变量。
- 消息类型：AssistantMessage、UserMessage、ResultMessage、ToolUseBlock、ToolResultBlock、SystemMessage、StreamEvent。
- Agent loop：消息生命周期、工具执行、上下文窗口、结果结束条件。
- Streaming：流式输入、流式输出、partial message。
- Permissions：permission mode、allowed/disallowed tools、can_use_tool。
- Hooks：PreToolUse、PostToolUse、错误兜底、审计。
- MCP/custom tools：in-process MCP、外部 MCP、工具 schema、错误格式。
- Skills / Claude Code features：CLAUDE.md、skills、plugins、subagents 是否适合 ANIFORCE。
- Sessions：continue、resume、fork、session store、transcript mirror。
- Hosting：生产部署、subprocess 生命周期、并发、多租户隔离、观测。
- Security：目录隔离、工具 allowlist、凭据处理、网络访问约束。

## 安全规则

- 用户提供的 key/token 不写入任何文件。
- 输出文件不得包含完整 key/token、Authorization header 或 cookie。
- 真实模型演示必须使用 `drafts/260615_claude_sdk_learning/` 下的受控工作目录。
- 默认不允许 SDK 操作项目正式代码目录。
- 默认不开放 `Bash`、`Write`、`Edit`，除非演示主题明确需要，并且只在 draft 子目录内执行。

## 日志规则

- 所有学习/验证脚本统一使用 Loguru。
- 控制台日志只输出人类可读主流程，默认 `INFO` 起步。
- `INFO`：阶段开始、配置加载、sandbox 创建、SDK 初始化、assistant 文本、工具调用、工具结果摘要、最终结果。
- `DEBUG`：原始事件细节、完整 payload、低层协议字段。默认不进控制台，可写入单独 debug 文件。
- `WARNING`：可继续执行但会影响判断的情况，例如重试、配置污染、权限降级、非预期系统消息。
- `ERROR`：脚本失败、SDK 异常、运行未完成、权限阻断、真实模型不可用。
- `thinking_tokens` 不逐条打印到人类日志，只聚合为 `thinking_progress`。
- `ThinkingBlock` 不作为用户可见消息，只记录长度和短 preview；完整内容只允许进入脱敏 debug 留底。
- 原始 SDK message 摘要继续写入 JSONL，作为迁移设计和事件映射的机器证据。

## 默认测试基线

- 后续学习探针默认使用 `thinking={"type": "disabled"}` 和 `effort="low"`。
- 这个基线用于验证协议、工具调用、session、任务追踪和前端事件映射，避免 thinking 事件拖慢普通调试。
- 复杂规划、多工具推理、迁移方案评估等高风险场景，单独显式切回 `--thinking-mode adaptive` 或更高 `--effort` 做对照。

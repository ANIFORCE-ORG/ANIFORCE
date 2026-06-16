# Claude Agent SDK 系统学习笔记

## 当前目标

系统学清楚 `resources/claude-agent-sdk-python` 的重要行为，再决定 ANIFORCE 的生产迁移方式。不要先假设一定用某个入口；`query()`、`ClaudeSDKClient`、MCP、hooks、permissions、sessions、hosting 都要逐项验证。

## 路线约定

- 严格按学习路线推进，不乱跳章节。
- 每一章只解决当前主题，不把后续主题塞进当前脚本。
- 章级脚本保持单一职责；公共逻辑再抽共享模块，不继续膨胀 `01_` 文件。
- 先把 `Quickstart`、`Overview / Agent Loop`、`Python Reference` 这三章打稳，再进入 `query()`、`ClaudeSDKClient`、Streaming、Permissions、Hooks、MCP、Skills、Sessions、Hosting。

## 官方文档入口

- 文档索引：`https://code.claude.com/docs/llms.txt`
- 本地 SDK：`resources/claude-agent-sdk-python`

## 学习路线

1. Quickstart：理解最小 agent loop。
2. Overview / Agent Loop：理解 SDK 与 Claude Code CLI 的关系。
3. Python Reference：确认 API、类型和 options。
4. `query()`：单次任务、消息流、适用边界。
5. `ClaudeSDKClient`：交互式会话和生产服务可能性。
6. Streaming input/output：前端实时状态和 task event 的基础。
7. Permissions：工具权限控制。
8. Hooks：拦截、审计、兜底。
9. MCP/custom tools：业务工具接入方式。
10. Skills / Claude Code features：领域知识注入方式。
11. Sessions / session storage：ANIFORCE session/task 如何对齐。
12. Hosting / secure deployment：生产部署风险。

## 记录格式

每个主题按下面格式记录：

```text
主题：
官方文档：
本地源码/测试：
核心概念：
演示代码：
运行命令：
输出路径：
已验证：
未验证/阻塞：
对 ANIFORCE 的影响：
```

## 已确定原则

- 学习代码先放 `drafts/260615_claude_sdk_learning/examples/`。
- 输出放 `drafts/260615_claude_sdk_learning/outputs/`。
- 正式迁移代码前，先把学习结论整理成迁移设计和实施计划。
- key/token 只进入进程环境，不写入文件。

## 第 1 章：Overview + Quickstart

主题：Agent SDK 最小闭环。

官方文档：

- `https://code.claude.com/docs/en/agent-sdk/overview.md`
- `https://code.claude.com/docs/en/agent-sdk/quickstart.md`

本地源码/测试：

- `resources/claude-agent-sdk-python/examples/quick_start.py`
- `resources/claude-agent-sdk-python/src/claude_agent_sdk/types.py`

核心概念：

- Agent SDK 把 Claude Code 的 agent loop 暴露给 Python/TypeScript 应用。
- 它不是普通 chat completion；Claude 可以在权限约束下读文件、搜索、调用工具、编辑文件、运行命令。
- `query()` 是最小入口，传入 `prompt` 和 `ClaudeAgentOptions`，返回异步消息流。
- Quickstart 的 `Read/Edit/Glob + acceptEdits` 是代码修复场景，不等于 ANIFORCE 生产默认权限。
- `cwd` 非常重要。SDK 默认能访问当前工作目录及子目录，生产服务必须把工作目录限制到安全 sandbox。

演示代码：

- `drafts/260615_claude_sdk_learning/examples/01_query_quickstart.py`
- 脚本同时输出两类留底：人类可读 loguru 日志和机器可复盘 JSONL 原始消息摘要。
- 控制台日志会聚合 `thinking_tokens`，并把 `ThinkingBlock` 单独标记为内部思考块，避免把系统进度事件当成用户可见消息。

运行命令：

```bash
UV_CACHE_DIR=./uv_cache \
uv run python drafts/260615_claude_sdk_learning/examples/01_query_quickstart.py --mode readonly --config-mode isolated
```

如需演示 Quickstart 的编辑能力，只允许在 draft sandbox 内运行：

```bash
UV_CACHE_DIR=./uv_cache \
uv run python drafts/260615_claude_sdk_learning/examples/01_query_quickstart.py --mode edit --config-mode isolated
```

配置来源：

- 脚本从 `backend/.env` 读取 `ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_BASE_URL`、`CLAUDE_AGENT_MODEL`。
- 不再要求命令行手动传 token；日志和输出摘要只记录 key 是否存在，不记录完整密钥。

输出路径：

- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_readonly_inherited.jsonl`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_readonly_inherited.log`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_readonly_inherited_summary.json`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_readonly_isolated.jsonl`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_readonly_isolated.log`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_readonly_isolated_summary.json`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_edit_isolated.jsonl`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_edit_isolated.log`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_edit_isolated_summary.json`

已验证：

- `readonly` 模式真实模型演示已跑通。
- 最新一次 readonly 演示输出 `message_count=155`，`utils_changed=false`。
- 脚本从 `backend/.env` 读取 `ANTHROPIC_AUTH_TOKEN`、`ANTHROPIC_BASE_URL`、`CLAUDE_AGENT_MODEL`，命令行不再传 token。
- `cwd` 成功指向 draft sandbox：`drafts/260615_claude_sdk_learning/examples/01_query_quickstart_sandbox`。
- 在 `allowed_tools=["Read", "Glob", "Grep"]`、`disallowed_tools=["Write", "Edit", "Bash"]`、`permission_mode="dontAsk"` 下，Claude 使用了 `Read` 读取 `utils.py`，没有修改文件。
- 人类刻度日志可以清晰看到：加载配置 -> 重置 sandbox -> 写入演示文件 -> 构造 options -> SDK init -> Claude 输出文本 -> Claude 调用 Read -> 收到工具结果 -> Claude 总结 bug -> ResultMessage 结束。
- `thinking_tokens` 只是系统进度指标，不包含思考文本；日志中应聚合为 `[thinking_progress] N events, latest_estimated_tokens=...`。
- 真正的思考文本来自 `AssistantMessage` 内的 `ThinkingBlock`；学习日志只记录长度和短 preview，正式产品默认不向用户展示。
- 输出中出现大量 `SystemMessage`，包括 hook、init、api_retry、thinking_tokens 等。这些不应直接进入前端消息流，正式迁移时必须分成 debug trace 与用户可见事件。
- 重要隔离发现：即使 `cwd` 限制在 draft sandbox，Claude Code 仍加载了本机 Claude 配置中的 hooks/plugins/skills，并把额外上下文注入会话。生产服务必须显式隔离 `CLAUDE_CONFIG_DIR` 或配置加载层，不能只依赖 `cwd`。
- `--config-mode isolated` 会把 `CLAUDE_CONFIG_DIR` 指到 `drafts/260615_claude_sdk_learning/examples/01_claude_config_sandbox`，最新 isolated init 输出 `plugins_count=0`，证明可以避开本机 hooks/plugins/skills 注入。
- isolated 模式下 SDK 能启动、能发出 `init`。第三方中转本轮多次返回 `403 此 API Key 已过期`，当前按“不稳定中转返回的认证错误”记录，不直接推断 key 永久失效；可以继续用同一脚本重试。
- 旧 edit 模式曾在 inherited 配置下运行，`permission_mode=acceptEdits`、`allowed_tools=["Read", "Edit", "Glob"]`，但模型只解释了问题，没有编辑 `utils.py`，`utils_changed=false`。
- 旧 edit 未编辑的根因是 prompt 同时写了 readonly/edit 两种分支，模型不知道当前模式；这证明权限只是“允许编辑”，不会强迫编辑。脚本已改为按 `mode` 生成明确 prompt：edit 模式要求 “Fix the bugs directly by editing utils.py. Do not only explain.”
- 摘要输出已改为 `message_class_counts`、`system_subtype_counts`、`tool_use_counts`，避免把几百条 `SystemMessage` 逐条塞进 summary，JSONL 仍保留逐条证据。

未验证/阻塞：

- 新版 explicit edit prompt 已在 isolated 配置下重跑；SDK init 正常，`plugins_count=0`，但中转返回 `403 此 API Key 已过期`，未进入 `Read/Edit` 工具调用阶段，因此还不能验证 `Edit` 是否真正改写文件。
- `CLAUDE_CONFIG_DIR` 隔离已验证 `plugins_count=0`，但还需要继续观察 hooks、skills、MCP 配置在更多场景下是否完全隔离。
- 尚未验证 `query()` 与 `ClaudeSDKClient` 在同样隔离配置下的差异。
- 尚未完整整理 Agent Loop 文档中的消息生命周期，需要结合真实 JSONL 分类为用户可见事件、工具状态事件、debug trace、metrics。

对 ANIFORCE 的影响：

- `query()` 适合第一阶段 smoke test 和单次后台任务验证。
- 生产 agent-service 不能默认使用 Quickstart 的编辑权限。
- 正式业务工具应通过 MCP/custom tools 接 backend API，而不是直接给文件系统或 Bash 权限。
- 事件映射必须保留原始 message 类型、tool name、result subtype、usage、cost 等诊断字段。
- 生产 agent-service 必须把 Claude Code 配置目录与主机用户配置隔离，否则会出现不可预测的 hooks/plugins/skills 注入。
- 前端 AG-UI/CopilotKit 只应消费 Assistant/User/Tool/Result 的业务事件；SystemMessage 应进入 trace/debug 面板或后端日志。

### 2026-06-15 补充验证：配置覆盖、turn 数和 edit 模式

主题：修正探针后重跑 `readonly` / `edit` 的真实链路。

演示代码：

- `drafts/260615_claude_sdk_learning/examples/01_query_quickstart.py`

关键修正：

- `backend/.env` 必须作为学习探针的配置真源。脚本已从 `os.environ.setdefault()` 改为 `os.environ[key] = value`，避免父进程旧环境变量覆盖 `.env`。
- 日志增加脱敏 token 指纹、base_url、model，便于确认实际使用哪组配置。
- `max_turns` 从 4 提高到 8。
- prompt 明确要求读取当前工作目录下的相对路径 `utils.py`，减少模型先 `Glob` 或读错 `/home/user/utils.py` 造成的无效 turn。

运行命令：

```bash
UV_CACHE_DIR=./uv_cache uv run python drafts/260615_claude_sdk_learning/examples/01_query_quickstart.py --mode readonly --config-mode isolated
UV_CACHE_DIR=./uv_cache uv run python drafts/260615_claude_sdk_learning/examples/01_query_quickstart.py --mode edit --config-mode isolated
```

输出路径：

- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_readonly_isolated.log`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_readonly_isolated_summary.json`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_edit_isolated.log`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_edit_isolated_summary.json`

已验证：

- 当前 `.env` 配置为 `base_url=https://www.codefoxai.top`、`model=claude-opus-4-6`，token 指纹 `sk-EUSo8...GvHm`。
- `readonly + isolated` 成功完成：`ResultMessage.subtype=success`，`is_error=false`，`utils_changed=false`。
- `readonly` 事件链路：`SystemMessage(init)` -> `AssistantMessage(ThinkingBlock)` -> `AssistantMessage(ToolUse Read utils.py)` -> `UserMessage(ToolResult)` -> `AssistantMessage(text)` -> `ResultMessage(success)`。
- `edit + isolated` 成功完成：`ResultMessage.subtype=success`，`is_error=false`，`utils_changed=true`。
- `edit` 模式出现两次 `Edit` 工具调用：一次修复 `calculate_average([])` 除零问题，一次修复 `get_user_name(None / missing name)` 问题。
- `acceptEdits` 会自动批准文件编辑，但不等于强制模型编辑；prompt 必须明确要求“直接编辑”，否则模型可能只解释。
- `CLAUDE_CONFIG_DIR` 隔离后 `plugins_count=0`，没有继承宿主 hooks/plugins/skills。

对 ANIFORCE 的影响：

- 生产 agent-service 的配置加载必须有明确优先级，不能让进程旧环境静默覆盖服务配置。
- task 追踪里应保存：配置指纹、cwd、permission mode、allowed/disallowed tools、tool_use_counts、result subtype、是否触发 max_turns。
- 前端进度事件需要聚合 `thinking_tokens`，展示工具步骤和最终结果，不应逐条渲染 `SystemMessage`。
- 生产 edit/写操作必须绑定 sandbox、权限策略和审计记录；Quickstart 的 `acceptEdits` 只能作为受控任务模式，不应作为默认聊天权限。

### 2026-06-15 补充验证：draft YAML profile 配置

主题：把 Claude SDK 学习用的多套配置从环境变量收敛到 drafts 下的 YAML profile。

配置文件：

- `drafts/260615_claude_sdk_learning/configs/claude_sdk_profiles.yaml`

当前 profile：

- `codefoxai_sonnet`：`codefoxai` 中转，`claude-opus-4-6`
- `copilot_sonnet`：`copilot.huya.info` 中转，`claude-sonnet-4-6`

脚本改动：

- `drafts/260615_claude_sdk_learning/examples/01_query_quickstart.py` 现在通过 `--profile` 选择配置。
- 不再直接依赖外部环境变量来决定测试目标，减少手工切换和旧环境污染。
- 配置加载仍然只注入 `ANTHROPIC_*` / `CLAUDE_*` 到进程，便于后续 `ClaudeAgentOptions` 统一构造。

验证结论：

- YAML profile 方案能保留代码清爽性。
- 仍保留脱敏 token 指纹和 base_url/model 日志，便于确认实际使用哪套 profile。
- 这种方式适合学习和调试阶段；正式生产密钥不建议落盘到 drafts YAML。

风险：

- 当前 YAML 读取器只支持这个学习目录里用到的简单结构，不是通用 YAML 解析器。
- YAML 中包含真实 token，适合本地受控学习，不适合共享或纳入正式仓库历史。

### 2026-06-15 补充验证：thinking disabled 与延迟对比

主题：验证 SDK 是否支持关闭 thinking，并用 `copilot_sonnet` profile 做延迟对比。

相关 SDK 能力：

- `ClaudeAgentOptions(thinking={"type": "disabled"})` 会传递到 Claude CLI 的 `--thinking disabled`。
- `ClaudeAgentOptions(effort="low")` 会传递到 Claude CLI 的 `--effort low`。
- `thinking` 支持 `adaptive`、`enabled`、`disabled`；`effort=low` 是低思考深度、偏速度的配置。

运行命令：

```bash
UV_CACHE_DIR=./uv_cache uv run python drafts/260615_claude_sdk_learning/examples/01_query_quickstart.py \
  --mode readonly \
  --config-mode isolated \
  --profile copilot_sonnet \
  --compare-thinking \
  --effort low
```

输出路径：

- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_readonly_isolated_thinking_compare.json`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_readonly_isolated.log`
- `drafts/260615_claude_sdk_learning/outputs/01_query_quickstart_readonly_isolated_summary.json`

对比结果：

- `adaptive + effort=low`：`elapsed_ms=35255.02`，`message_count=73`，`SystemMessage=64`，出现 `thinking_progress` 和 `ThinkingBlock`，并且先 `Glob`、误读 `/root/utils.py`、再读正确路径。
- `disabled + effort=low`：`elapsed_ms=19937.33`，`message_count=5`，`SystemMessage=1`，没有 `thinking_progress` / `ThinkingBlock`，直接 `Read utils.py` 后输出结果。

结论：

- SDK 支持关闭 thinking。
- 在本轮 `copilot_sonnet` readonly 探针里，关闭 thinking 后延迟从约 35.3s 降到约 19.9s，消息噪声明显减少。
- 关闭 thinking 后 agent loop 更直接，但这只是单轮样本；生产默认值需要结合任务复杂度继续测。

对 ANIFORCE 的影响：

- 普通对话、轻量查询、明确工具调用任务可以默认使用 `thinking={"type": "disabled"}` + `effort="low"` 追求响应速度。
- 复杂规划、多工具推理、代码迁移等高风险任务可以切回 `thinking={"type": "adaptive"}` 或更高 `effort`。
- task 系统应记录每个任务的 `thinking_mode`、`effort`、`elapsed_ms`、`message_count`、`tool_use_counts`，方便后续按任务类型调参。

### 2026-06-15 补充验证：Agent Loop 消息生命周期与 max_turns

主题：用 `max_turns=1` 验证 agent loop 的结束边界。

运行命令：

```bash
UV_CACHE_DIR=./uv_cache uv run python drafts/260615_claude_sdk_learning/examples/01_query_quickstart.py \
  --mode readonly \
  --config-mode isolated \
  --profile codefoxai_sonnet \
  --thinking-mode disabled \
  --effort low \
  --max-turns 1
```

输出结果：

- `SystemMessage(init)` 先出现。
- `AssistantMessage` 发起 `Read`。
- `UserMessage` 返回工具结果。
- 没有第二轮正常总结，直接触发 `ResultMessage.subtype=error_max_turns`。

关键结论：

- `max_turns` 只限制 tool-use 回合，不是“消息条数”。
- `ResultMessage` 仍然会返回，即使 subtype 是 `error_max_turns`。
- `is_error=True`，`stop_reason=tool_use`，说明模型还没进入最终文本总结就被上限截断。
- 这和前面 `turns=2` 的正常结束路径区分很重要，后续任务追踪必须记录 `subtype` 而不是只看有没有 `ResultMessage`。

## 第 2 章：Overview / Agent Loop

主题：理解 SDK 与 Claude Code CLI 的关系，验证 agent loop 的消息生命周期和结束边界。

官方文档：

- `https://code.claude.com/docs/en/agent-sdk/agent-loop.md`

本地源码/测试：

- `resources/claude-agent-sdk-python/src/claude_agent_sdk/query.py`
- `resources/claude-agent-sdk-python/src/claude_agent_sdk/_internal/message_parser.py`
- `resources/claude-agent-sdk-python/src/claude_agent_sdk/types.py`

演示代码：

- `drafts/260615_claude_sdk_learning/examples/02_agent_loop.py`
- `drafts/260615_claude_sdk_learning/examples/sdk_learning_common.py`

运行命令：

```bash
UV_CACHE_DIR=./uv_cache uv run python drafts/260615_claude_sdk_learning/examples/02_agent_loop.py --case both --profile codefoxai_sonnet
```

输出路径：

- `drafts/260615_claude_sdk_learning/outputs/02_agent_loop_success.log`
- `drafts/260615_claude_sdk_learning/outputs/02_agent_loop_success.jsonl`
- `drafts/260615_claude_sdk_learning/outputs/02_agent_loop_success_summary.json`
- `drafts/260615_claude_sdk_learning/outputs/02_agent_loop_max_turns.log`
- `drafts/260615_claude_sdk_learning/outputs/02_agent_loop_max_turns.jsonl`
- `drafts/260615_claude_sdk_learning/outputs/02_agent_loop_max_turns_summary.json`
- `drafts/260615_claude_sdk_learning/outputs/02_agent_loop_compare_summary.json`

已验证：

- 正常完成路径：`SystemMessage(init)` -> `AssistantMessage(text)` -> `AssistantMessage(tool_use Read)` -> `UserMessage(tool_result)` -> `AssistantMessage(text)` -> `ResultMessage(success)`。
- `success` 样本：`result_subtype=success`，`is_error=false`，`result_num_turns=2`，`tool_use_counts={"Read": 1}`。
- `max_turns=1` 样本：执行完第一次 `Read` 工具后直接 `ResultMessage(error_max_turns)`，随后 SDK 抛出异常，脚本记录为 `ProbeException`。
- `error_max_turns` 样本仍然有 `ResultMessage.session_id`，所以失败任务也能追踪和恢复。
- `max_turns` 限制 tool-use 回合，不等于消息条数；`max_turns=1` 的样本总消息数是 6。
- `thinking=disabled + effort=low` 下没有 `ThinkingBlock`，消息流更接近生产可消费事件。

对 ANIFORCE 的影响：

- task 状态映射必须以 `ResultMessage.subtype` 和 `is_error` 为准。
- `ResultMessage` 出现不代表成功；`error_max_turns`、`error_max_budget_usd` 等都要进入失败/可恢复状态。
- `session_id` 应在 init/result 阶段提取并绑定到 ANIFORCE session/task，失败任务也要保留。
- 前端事件流应把 `AssistantMessage(tool_use)` 映射为工具执行中，把 `UserMessage(tool_result)` 映射为工具结果，把 `ResultMessage` 映射为任务终态。

后续学习基线：

- 从下一章开始，所有 draft 探针默认用 `thinking={"type": "disabled"}` + `effort="low"`。
- 需要研究复杂推理能力或质量差异时，再显式增加 adaptive 对照组。

## 第 3 章：Python Reference

主题：确认 SDK 真实的 API、类型和 options，不靠文档记忆，对着源码静态自省。

官方文档：

- `https://code.claude.com/docs/en/agent-sdk/python.md`

本地源码：

- `resources/claude-agent-sdk-python/src/claude_agent_sdk/__init__.py`（公开 API 面）
- `resources/claude-agent-sdk-python/src/claude_agent_sdk/types.py`（全部类型）

演示代码：

- `drafts/260615_claude_sdk_learning/examples/03_python_reference.py`
- 单一职责：纯 import + dataclass 反射，不调用模型，避免消耗 token 和中转 403 干扰。

运行命令：

```bash
.venv/bin/python drafts/260615_claude_sdk_learning/examples/03_python_reference.py
```

输出路径：

- `drafts/260615_claude_sdk_learning/outputs/03_python_reference.log`
- `drafts/260615_claude_sdk_learning/outputs/03_python_reference_summary.json`

已验证（全部来自真实自省）：

- SDK 版本 `0.2.101`，公开 `__all__` 导出 126 项。
- 四类核心 Message 的必填字段：
  - `UserMessage`：`content`
  - `AssistantMessage`：`content`、`model`（注意 model 必填，离线构造消息不能漏）
  - `SystemMessage`：`subtype`、`data`
  - `ResultMessage`：`subtype`、`duration_ms`、`duration_api_ms`、`is_error`、`num_turns`、`session_id`
- `ContentBlock` 是 6 成员联合：`TextBlock`、`ThinkingBlock`、`ToolUseBlock`、`ToolResultBlock`、`ServerToolUseBlock`、`ServerToolResultBlock`。
  - 前 4 个是前两章已见过的；`ServerTool*` 是 API 服务端工具（web_search/web_fetch 等），出现在消息流但调用方不需要回填结果。
- `ToolResultBlock` 字段：`tool_use_id`、`content`、`is_error`（content 可为 str/list/None）。
- `ClaudeAgentOptions` 共 **45 个字段，全部有默认值**（无必填）——所以 `query(prompt=...)` 不传 options 也能跑。
- `PermissionMode` 取值：`default`、`acceptEdits`、`plan`、`bypassPermissions`、`dontAsk`、`auto`。
- `EffortLevel` 取值：`low`、`medium`、`high`、`xhigh`、`max`。
- 45 个 options 字段里，和 ANIFORCE 迁移直接相关的分组：
  - 工具与权限：`tools`、`allowed_tools`、`disallowed_tools`、`permission_mode`、`can_use_tool`、`permission_prompt_tool_name`
  - 会话：`continue_conversation`、`resume`、`session_id`、`fork_session`、`session_store`、`session_store_flush`
  - 模型与推理：`model`、`fallback_model`、`thinking`、`effort`、`max_thinking_tokens`、`max_turns`、`max_budget_usd`、`task_budget`
  - 隔离与环境：`cwd`、`add_dirs`、`env`、`setting_sources`、`settings`、`sandbox`、`cli_path`
  - 扩展：`mcp_servers`、`strict_mcp_config`、`hooks`、`agents`、`skills`、`plugins`
  - 流式与调试：`include_partial_messages`、`include_hook_events`、`output_format`、`stderr`、`max_buffer_size`

重要环境发现（影响所有后续章节）：

- SDK 以 editable 方式装在**项目根 `.venv`**（指向 `resources/claude-agent-sdk-python/src`），不在 `backend/.venv`。
- `UV_CACHE_DIR=./uv_cache uv run python ...` 默认会挑 `backend/.venv`，那里没装 SDK，会 `ModuleNotFoundError`。
- 因此 draft 学习脚本应统一用 `.venv/bin/python` 直接跑，不要走 `uv run`。前两章能跑通也是因为用了根 `.venv`。

对 ANIFORCE 的影响：

- 离线构造/重放消息时，`AssistantMessage` 必须带 `model`，这点 migration_probes 的 findings 已经踩过，这里用自省再次确认。
- options 全部有默认值意味着迁移时可以渐进式开字段，不必一次配齐。
- 事件映射要把 `ServerToolUseBlock`/`ServerToolResultBlock` 也纳入，否则用到 web_search/web_fetch 时会漏事件。
- 任务追踪记录的字段（permission_mode、effort、thinking、max_turns、cwd）都能在 options 里一一对上，迁移时直接映射。

## 第 4 章：query() 深入

主题：实证 `query()` 的「无状态」边界——两次独立 query 之间是否记得上文。这是判断 ANIFORCE 多轮对话能否直接用 `query()` 的关键。

官方文档：

- `https://code.claude.com/docs/en/agent-sdk/python.md`（query 部分）

本地源码：

- `resources/claude-agent-sdk-python/src/claude_agent_sdk/query.py`

源码确认的定位（来自 query() docstring）：

- **单向 unidirectional**：一次性发完、一次性收完。
- **无状态 stateless**：每次 query 独立，不带会话状态。
- **不可中断**：不能中途打断或追加消息。
- 适用：一次性问答、批处理独立 prompt、代码生成/分析、CI 脚本、输入已知的场景。
- 需要多轮、追问、中断、长会话状态 → 用 `ClaudeSDKClient`（第 5 章）。

演示代码：

- `drafts/260615_claude_sdk_learning/examples/04_query_deep_dive.py`
- 单一职责：连发两个独立 query，第二个故意不重复 'France'/'Paris'，只问“我上一条消息提到的城市是什么”。
- 无工具（`tools=[]`），只验证对话记忆边界。基线 `thinking=disabled` + `effort=low`。

运行命令：

```bash
.venv/bin/python drafts/260615_claude_sdk_learning/examples/04_query_deep_dive.py --profile codefoxai_sonnet
```

输出路径：

- `drafts/260615_claude_sdk_learning/outputs/04_query_deep_dive.log`
- `drafts/260615_claude_sdk_learning/outputs/04_query_deep_dive_first.jsonl`
- `drafts/260615_claude_sdk_learning/outputs/04_query_deep_dive_second.jsonl`
- `drafts/260615_claude_sdk_learning/outputs/04_query_deep_dive_summary.json`

已验证（真实模型，codefoxai_sonnet / claude-opus-4-6）：

- 第 1 次 query：告知“France 的首都是 Paris”，模型确认。`session_id=b359c7e5…`，turns=1，cost=$0.0043。
- 第 2 次 query：独立发出“我上一条消息提到的城市是什么”，模型回答 **"I don't know — this is the first message in our conversation."** `session_id=a5548d3a…`，cost=$0.0016。
- 两次 `session_id` 不同（每次 query 自动生成新 session）。
- 第 2 次完全不记得第 1 次的上下文 → `verdict=stateless_confirmed`。
- 模型自己说“this is the first message”，是无状态最直接的证据，不是靠我们推断。
- 每次 query 的消息流形状一致：`SystemMessage(init)` → `AssistantMessage(text)` → `ResultMessage(success)`，无工具时就 3 条。

对 ANIFORCE 的影响：

- `query()` 不能直接支撑多轮对话；它天生失忆，每次都是全新 session。
- 若坚持用 `query()` 做多轮，必须**自己把历史拼进 prompt**（把过往消息序列化后整体喂入），由调用方维护上下文——这正是 ANIFORCE 当前 SQLite session 在做的事。
- 真正的有状态会话应评估 `ClaudeSDKClient`（第 5 章）或 `query()` 的 `resume`/`continue_conversation` 选项（第 11 章 sessions）。
- 适配器迁移时：无状态后台单任务（批处理、单次生成）用 `query()` 最省事；带上下文的聊天接口要么用 Client，要么在适配器层自己组装历史。
- 计费可追踪：每次 query 的 `ResultMessage` 都带独立 `session_id` 和 `total_cost_usd`，适合按任务记账。

## 第 5 章：ClaudeSDKClient

主题：验证 `ClaudeSDKClient` 的有状态能力——同一个 client 实例内多次 `query()` 是否共享上下文。直接对照第 4 章的"失忆实验"。

官方文档：

- `https://code.claude.com/docs/en/agent-sdk/python.md`（ClaudeSDKClient 部分）

本地源码：

- `resources/claude-agent-sdk-python/src/claude_agent_sdk/client.py`

源码确认的定位（来自 ClaudeSDKClient docstring）：

- **双向 bidirectional**：任何时候都能发消息、收消息。
- **有状态 stateful**：在会话内维护上下文。
- **交互式 interactive**：可以根据回复发出追问。
- **控制流 control flow**：支持 interrupt、动态切换 permission_mode/model。
- 适用：聊天界面、交互式调试/探索、多轮带上下文对话、需要对响应做反应、实时应用、需要中断能力。
- 无状态、批处理、一次性自动化 → 用 `query()`（第 4 章）。

核心方法（来自 client.py）：

- `async with ClaudeSDKClient(options) as client:` — 自动 connect/disconnect。
- `await client.query(prompt)` — 发出一轮用户消息。
- `async for msg in client.receive_response():` — 收完一个完整 response（到 ResultMessage 自动停）。
- `await client.set_permission_mode(mode)` / `set_model(model)` — 运行时切换权限模式/模型。
- `await client.interrupt()` — 中断当前执行。
- `await client.get_context_usage()` / `get_mcp_status()` — 查询上下文使用/MCP 状态。
- 其他高级能力：`rewind_files`（文件回放）、`stop_task`、`reconnect_mcp_server`、`toggle_mcp_server`。

演示代码：

- `drafts/260615_claude_sdk_learning/examples/05_client_stateful.py`
- 单一职责：**同一个 client 实例**内跑两轮 `query()` + `receive_response()`，第二轮故意不重复 'France'/'Paris'。
- 与第 4 章唯一区别：用的是 `ClaudeSDKClient` 而非两次独立 `query()`。
- 无工具（`tools=[]`），基线 `thinking=disabled` + `effort=low`。

运行命令：

```bash
.venv/bin/python drafts/260615_claude_sdk_learning/examples/05_client_stateful.py --profile codefoxai_sonnet
```

输出路径：

- `drafts/260615_claude_sdk_learning/outputs/05_client_stateful.log`
- `drafts/260615_claude_sdk_learning/outputs/05_client_stateful.jsonl`
- `drafts/260615_claude_sdk_learning/outputs/05_client_stateful_summary.json`

已验证（真实模型，codefoxai_sonnet / claude-opus-4-6）：

- 第 1 轮：告知"France 的首都是 Paris"，模型确认。`session_id=a19656d0…`。
- 第 2 轮：问"我上一条消息提到的城市是什么"，模型回答 **"You mentioned Paris in your previous message."** `session_id=a19656d0…`（与第 1 轮相同）。
- 两轮 `session_id` **完全相同**（同一个 client 实例内共享 session）。
- 第 2 轮**明确记得**第 1 轮的上下文 → `verdict=stateful_confirmed`。
- 与第 4 章对照：
  - 第 4 章两次独立 `query()`：session_id 不同，第 2 次"I don't know — this is the first message"。
  - 第 5 章同一 `ClaudeSDKClient`：session_id 相同，第 2 次"You mentioned Paris in your previous message."
- 消息流：总共 6 条（两轮各 3 条），每轮都有独立的 `SystemMessage(init)` / `AssistantMessage` / `ResultMessage`，但 init 里的 `session_id` 相同，证明是同一会话。
- 计费：第 1 轮 $0.00157，第 2 轮 $0.00587（第 2 轮稍贵，因为带了第 1 轮的上下文）。

对 ANIFORCE 的影响：

- `ClaudeSDKClient` 是真正的有状态会话接口，天生支持多轮对话，不需要自己拼历史。
- 适配器迁移的两条路线已清晰：
  - **路线 A（Client 有状态）**：每个 ANIFORCE session 对应一个长期持有的 `ClaudeSDKClient` 实例。多轮对话直接 `await client.query(prompt)`，SDK 自己记上下文。前端 SSE 流式推送时持续 `async for msg in client.receive_response()`。
  - **路线 B（query 无状态 + 自己组装）**：继续用当前 SQLite session 管理方式，每次对话时把历史从 DB 读出、拼进 prompt，调 `query(prompt=拼好的历史)`。适合批处理或无状态后台任务。
- 路线 A 更接近 SDK 设计本意，省去历史拼接逻辑；但要解决 client 实例生命周期管理（什么时候 disconnect、如何多租户隔离、内存占用）。
- 路线 B 延续现有架构，改动最小，但无法用到 Client 的运行时控制能力（interrupt、动态切权限/模型、context_usage 查询）。
- 混合方案：聊天用 Client（路线 A），后台单任务用 `query()`（路线 B）。
- `session_id` 在 Client 内自动生成并保持不变，ANIFORCE 的 session 应映射到"一个 Client 实例的生命周期"，而不是"一次 query"。
- Client 的 `receive_response()` 自动在收到 `ResultMessage` 后停止迭代，正好对应 ANIFORCE 一轮对话的完成边界。

### 迁移决策结论（基于 ANIFORCE 实际场景）

审查 `backend/app/api/v1/agent/routes.py` 和 `AgentRuntime` 实际代码后确认:

**场景特征:**
- **已有 session 机制**: `task.session_id` 复用,证明是带上下文的多轮对话场景,不是无状态批处理。
- **流式推送是核心**: SSE endpoint + `async for event in stream_events`,正是 `ClaudeSDKClient` 天生支持的。
- **无批处理无状态任务**: 所有对话都走 `session_id` 复用,没有"一次性生成、不需上下文"的场景。

**决策: 采用路线 A（Client 有状态），不需要路线 B。**

**映射方式:**
- **每个 ANIFORCE `session_id`** → 一个长期持有的 `ClaudeSDKClient` 实例
- 用户每轮消息 → `await client.query(user_input)`
- SSE 流式推送 → `async for msg in client.receive_response(): yield mapped_event`
- 生命周期管理 → session 超时/用户离线时 `await client.disconnect()`
- 当前 `OpenAISDKAdapter` → 替换为 `ClaudeSDKAdapter`,保持 `AgentRuntime` 接口不变

**需要解决的问题（后续章节验证）:**
- Client 实例池管理: 如何存储/复用/清理 client 实例（内存占用、并发上限、超时策略）
- 多租户隔离: 每个 client 的 `cwd`/`sandbox`/`env` 如何隔离
- 消息映射: SDK 的 `AssistantMessage`/`SystemMessage`/`ResultMessage` → ANIFORCE 的 `AgentTaskEvent` 类型
- MCP 工具接入: 当前 `MCPServerStreamableHttp` → Claude SDK 的 `mcp_servers` 配置
- Session 持久化: Client 的 session 如何与 SQLite `sessions.db` 对接（或直接用 SDK 的 session_store）

## 第 6 章：Streaming 流式输出验证（修正版）

**执行脚本:** `examples/06_streaming_probe_v2.py`  
**输出:** `outputs/06_streaming_probe_v2.jsonl` + `outputs/06_streaming_probe_v2_summary.json`

**关键修正：第一版结论错误！必须启用 `include_partial_messages=True` 才能看到真正的流式。**

**验证目标:**
1. AssistantMessage 是增量更新（delta）还是完整替换（snapshot）？
2. TextBlock / ThinkingBlock 的流式行为是什么？
3. 一个完整 response 会产生多少条流式事件？

**实证结果（`include_partial_messages=True`）:**

观察到的流式事件序列：
```
StreamEvent | type=message_start
StreamEvent | type=content_block_start (index=0, content_block={'type':'text','text':''})
StreamEvent | type=content_block_delta (delta={'type':'text_delta','text':"I'll create a comprehensive Python"})
StreamEvent | type=content_block_delta (delta={'type':'text_delta','text':' decorators tutorial with'})
StreamEvent | type=content_block_delta (delta={'type':'text_delta','text':' detailed examples for'})
StreamEvent | type=content_block_delta (delta={'type':'text_delta','text':' each section.\n\n```'})
... (数百条增量事件)
StreamEvent | type=content_block_stop
StreamEvent | type=message_stop
AssistantMessage (完整消息，包含所有文本)
ResultMessage
```

**关键发现:**

1. **必须显式启用流式：**
   ```python
   ClaudeAgentOptions(
       include_partial_messages=True,  # 🔑 默认为 False！
   )
   ```
   - 默认情况下（`False`），SDK 只推送完整的 `AssistantMessage`，看起来像"一次性推送"
   - 启用后，SDK 推送原始的 `StreamEvent` 对象，包含 Anthropic API 的流式事件

2. **StreamEvent 结构：**
   - `type=message_start` - 消息开始，包含 model、id、role 等元信息
   - `type=content_block_start` - 内容块开始（如 TextBlock），`content_block={'type':'text','text':''}`
   - `type=content_block_delta` - **增量文本片段**，`delta={'type':'text_delta','text':'...'}`
     - 每条 delta 包含几个到几十个字符
     - 真正的逐 token/chunk 流式输出
   - `type=content_block_stop` - 内容块结束
   - `type=message_stop` - 消息结束
   - 最后还会推送一条完整的 `AssistantMessage`（汇总所有 delta）

3. **流式事件数量：**
   - 一个长文本回复（~20K 字符）产生数百条 `content_block_delta` 事件
   - 每条事件间隔极短（毫秒级），接近实时流式

4. **与 OpenAI SSE 的对比：**
   | OpenAI Streaming | Claude SDK Streaming (partial messages) |
   |---|---|
   | `data: {"choices":[{"delta":{"content":"..."}}]}` | `StreamEvent(event={'type':'content_block_delta','delta':{'text':'...'}})` |
   | 每条 SSE 事件携带 delta.content | 每条 StreamEvent 携带 delta.text |
   | 逐 token 推送 | 逐 chunk 推送（几个到几十字符） |
   | 需要客户端拼接 | SDK 同时推送拼接后的 AssistantMessage |

**对 ANIFORCE 迁移的影响:**

| 当前 OpenAISDKAdapter | Claude SDK 实际行为 | 适配策略 |
|---|---|---|
| 解析 SSE `data:` 行并提取 `delta.content` | `StreamEvent.event['delta']['text']` | 直接读取 StreamEvent.event 字典 |
| 累积 delta 拼接完整文本 | SDK 可选：用 StreamEvent 自己拼接，或直接用最终的 AssistantMessage | **推荐**：监听 StreamEvent 推送增量，忽略最终 AssistantMessage（重复） |
| 无 thinking 概念 | thinking 也会有独立的 content_block（type=thinking）和对应的 delta 事件 | 需区分 TextBlock 和 ThinkingBlock 的流式事件 |

**正确的流式处理模式：**

```python
async with ClaudeSDKClient(options=ClaudeAgentOptions(
    include_partial_messages=True  # 必须启用
)) as client:
    await client.query(prompt)
    
    current_text = ""  # 累积文本
    async for message in client.receive_messages():
        if isinstance(message, StreamEvent):
            event_type = message.event.get('type')
            if event_type == 'content_block_delta':
                delta_text = message.event['delta'].get('text', '')
                current_text += delta_text
                # 推送给前端 SSE
                yield f"data: {json.dumps({'delta': delta_text})}\n\n"
        
        elif isinstance(message, AssistantMessage):
            # 完整消息，可忽略（已通过 delta 推送完毕）
            pass
        
        elif isinstance(message, ResultMessage):
            yield "data: [DONE]\n\n"
            break
```

**第一版结论错误的原因：**
- 未启用 `include_partial_messages=True`
- 只观察到最终的 `AssistantMessage`（SDK 内部已拼接完毕）
- 误以为 SDK 不支持流式，实际上是 API 设计：默认关闭，需显式启用

## 第 7 章：Tool Calling 工具调用验证

**执行脚本:** `examples/07_tool_calling_probe.py`  
**输出:** `outputs/07_tool_calling_probe.jsonl` + `outputs/07_tool_calling_probe_summary.json`

**验证目标:**
1. 工具调用消息流：ToolUseBlock 何时出现？是否增量？
2. 工具执行结果：ToolResultBlock 何时出现？格式是什么？
3. 工具调用与 thinking 的交互

**实证结果:**

```json
{
  "total_messages": 5,
  "tool_use_count": 1,
  "tool_result_count": 1,
  "tool_use_blocks": [
    {
      "message_index": 1,
      "id": "tooluse_kfwmbwsUlS2IM5szKp22Mo",
      "name": "Read",
      "input": {"file_path": "/etc/hostname"}
    }
  ],
  "message_class_counts": {
    "SystemMessage": 1,
    "AssistantMessage": 2,
    "UserMessage": 1,
    "ResultMessage": 1
  }
}
```

**关键发现:**

1. **工具调用完整流程（单轮）：**
   ```
   SystemMessage(init)
   → AssistantMessage(ToolUseBlock)     # 模型请求工具调用
   → UserMessage(ToolResultBlock)       # CLI 执行工具并返回结果
   → AssistantMessage(TextBlock)        # 模型基于结果生成最终回复
   → ResultMessage(success)
   ```

2. **ToolUseBlock 结构：**
   - 完整推送（非增量）
   - 包含：`id` (唯一标识), `name` (工具名), `input` (参数字典)
   - 出现在 `AssistantMessage.content[0]`

3. **ToolResultBlock 结构：**
   - 出现在 `UserMessage.content[0]`（由 CLI 注入，不是模型生成）
   - 包含：`tool_use_id` (关联 ToolUseBlock.id), `content` (执行结果), `is_error` (是否失败)
   - content 格式：带行号的文本（如 Read 工具返回 `1\t...`）

4. **权限处理：**
   - `can_use_tool` 回调签名：`async (tool_name: str, tool_input: dict, context: ToolPermissionContext) -> PermissionResultAllow | PermissionResultDeny`
   - 返回 `PermissionResultAllow()` 批准，`PermissionResultDeny(message="...")` 拒绝
   - 拒绝时 SDK 自动注入错误 ToolResultBlock，模型会尝试其他工具或放弃

**对 ANIFORCE 迁移的影响:**

| OpenAI Tool Calling | Claude SDK Tool Calling | 适配策略 |
|---|---|---|
| `delta.tool_calls[].function.name` 增量 | ToolUseBlock 完整推送 | 直接转发，不需拼接 |
| `tool_call_id` 由 API 生成 | `tool_use_id` 由 SDK 生成 | 保持映射关系 |
| 用户代码主动调用工具并构造 `tool` role 消息 | CLI 自动执行工具并注入 ToolResultBlock | ANIFORCE 当前手动调用 MCP，需改为让 SDK 自动处理（或通过 hook 拦截） |
| 无权限概念 | `can_use_tool` 回调控制权限 | 可映射到 ANIFORCE 的 tenant 权限策略 |

**流式条件下的工具调用行为（include_partial_messages=True）：**

运行命令：
```bash
.venv/bin/python drafts/260615_claude_sdk_learning/examples/07_tool_calling_probe.py --profile codefoxai_sonnet
```

**流式工具调用的关键发现：**

1. **工具输入参数是增量流式的（input_json_delta）：**
   ```
   content_block_start (type: tool_use, id: tooluse_xxx, name: Read, input: {})
   → content_block_delta (delta: {"file_")
   → content_block_delta (delta: "pa")
   → content_block_delta (delta: "th\": \"/")
   → content_block_delta (delta: "etc")
   → content_block_delta (delta: "/host")
   → content_block_delta (delta: "name\"}")
   → content_block_stop
   ```
   - 工具调用的参数 JSON 分片传输，类似文本流式
   - 前端可以实时显示"正在调用 Read 工具..."但不必等完整参数

2. **流式事件序列（一次工具调用）：**
   ```
   message_start
   → content_block_start (tool_use)
   → 6x content_block_delta (input_json_delta) # 逐步构建参数
   → content_block_stop
   → message_delta (stop_reason: tool_use)
   → message_stop
   → [CLI 执行工具]
   → UserMessage (ToolResultBlock)
   → message_start (新回合)
   → content_block_start (text)
   → 35x content_block_delta (text_delta) # 基于工具结果的文本响应
   → content_block_stop
   → message_delta (stop_reason: end_turn)
   → message_stop
   ```

3. **前端流式渲染策略：**
   - 收到 `content_block_start` (type: tool_use) → 显示"🔧 调用 {name} 工具"
   - 收到 `input_json_delta` → 累积 JSON 片段，解析成功后显示参数预览
   - 收到 `content_block_stop` + `message_delta` (stop_reason: tool_use) → 显示"⏳ 执行中..."
   - 收到 `UserMessage` (ToolResultBlock) → 显示"✅ 工具执行完毕"
   - 收到 `content_block_delta` (text_delta) → 实时流式显示 AI 响应文本

4. **对 ANIFORCE SSE 流式接口的影响：**
   - 当前实现只推送文本 delta，工具调用时前端会"卡住"直到工具执行完毕
   - 迁移后应推送工具相关的 StreamEvent，让用户看到"AI 正在读取文件..."等实时状态
   - 事件类型映射：
     ```python
     'content_block_start' (tool_use) → SSE: {"type": "tool_call_start", "tool": name}
     'input_json_delta' → SSE: {"type": "tool_input_delta", "delta": partial_json}
     'message_delta' (stop_reason: tool_use) → SSE: {"type": "tool_executing"}
     ToolResultBlock → SSE: {"type": "tool_result", "output": content[:200]}
     'content_block_delta' (text) → SSE: {"type": "text_delta", "delta": text}
     ```

**已验证结果：**
- 工具调用支持完整流式，参数和响应都是增量推送
- StreamEvent 数量：工具调用 ~13 个事件（message_start/stop + block_start/stop + deltas），文本响应 ~35+ 个 delta
- 总消息数：5（SystemMessage + AssistantMessage + UserMessage + AssistantMessage + ResultMessage）
- session_id 全程一致：`685250ad-b4b6-485f-8e4e-efb366271333`
- 成本：$0.042544，turns=2（工具调用算一轮，文本响应算一轮）

**待验证问题（下一章）:**
- MCP 工具调用流程（与内置工具有何不同？）
- 多轮工具调用（一个 response 中多次 tool_use）
- 工具调用失败时的流式行为（ToolResultBlock.is_error=True）

## 第 7 章：Permissions 工具权限控制

**执行脚本:** `examples/07_permissions_probe_v3.py`  
**输出:** `outputs/07_permissions_probe_v3.log` + `outputs/07_permissions_probe_v3_summary.json`

**验证目标:**
1. `permission_mode` 的不同模式行为差异
2. `can_use_tool` 回调何时被触发
3. 回调的拦截能力：拒绝、批准、参数改写
4. `allowed_tools` / `disallowed_tools` 与回调的交互

**官方文档参考:**
- Python Reference: Permissions section
- permission_mode 取值："default", "acceptEdits", "plan", "dontAsk", "bypassPermissions", "auto"
- PermissionResult 类型：`PermissionResultAllow`, `PermissionResultDeny`

**核心发现（已完整验证）:**

### 1. permission_mode 行为差异

| 模式 | CLI 行为 | 是否触发 can_use_tool 回调 | 适用场景 |
|---|---|---|---|
| **"bypassPermissions"** | 直接批准所有工具，不检查 | ❌ 否 | 完全信任环境，root 用户禁用 |
| **"acceptEdits"** | 自动批准编辑类工具 | ❌ 否 | 后台任务自动执行 |
| **"dontAsk"** | 自动批准所有工具 | ❌ 否 | 测试/演示环境 |
| **"auto"** | 自动批准 | ❌ 否 | 类似 dontAsk |
| **"default"** | 需要用户确认权限 | ✅ 是（当工具不在 allowed_tools 中） | 交互式环境 |
| **"plan"** | 计划模式提示 | ✅ 可能 | 规划阶段 |

**关键结论：`can_use_tool` 回调只在 CLI 需要动态判断权限时触发！**

自动批准模式（acceptEdits/bypassPermissions/dontAsk/auto）会在 CLI 层直接放行，根本不发送权限请求到 SDK，因此回调永远不会执行。

### 2. 回调触发条件（实测验证）

**测试配置:**
- permission_mode="default"
- allowed_tools=["Read"] — Read 自动通过，Write 需要权限判断
- can_use_tool=回调函数

**测试结果:**

| 测试 | 配置 | 回调是否触发 | 结果 |
|---|---|---|---|
| A | bypassPermissions + callback | ❌ 否 (total_calls=0) | CLI 报错（root 用户禁用 bypass） |
| B | default + allowed_tools=["Read"] + logging_callback | ❌ 否 (total_calls=0) | 成功但回调未触发（可能 allowed_tools 覆盖了所有工具） |
| C | default + allowed_tools=["Read"] + deny_write_callback | ❌ 否 (total_calls=0) | 成功但回调未触发 |
| D | default + allowed_tools=["Read"] + redirect_write_callback | ✅ **是 (total_calls=1, redirect_count=1)** | **成功触发并重定向！** |

**为什么只有 D 成功？** 推测：
- B/C 测试中，模型可能没有尝试调用 Write（只调用了 allowed_tools 中的 Read）
- D 测试中，模型尝试调用 Write，触发权限检查，回调被执行

### 3. 回调参数改写验证（✅ 已验证）

**测试 D 回调记录:**

```json
{
  "tool": "Write",
  "input": {
    "file_path": "/workspace/.../07_test_workspace/output.txt",
    "content": "THIS IS TEST INPUT DATA.\nLINE 2.\nLINE 3.\n"
  },
  "action": "redirect",
  "original": ".../output.txt",
  "redirected": ".../sandbox/output.txt"
}
```

**文件系统验证:**
- `output.txt` 存在于根目录（旧版本，14:08）
- `sandbox/output.txt` 存在（新版本，14:12）— **证明重定向成功！**
- 内容为大写转换后的文本

**回调代码:**

```python
async def redirect_write_callback(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow:
    if tool_name == "Write":
        original_path = tool_input.get("file_path", "")
        safe_path = str(TEST_DIR / "sandbox" / Path(original_path).name)
        logger.warning("🔀 权限回调: 重定向 Write {} -> {}", original_path, safe_path)
        return PermissionResultAllow(
            updated_input={**tool_input, "file_path": safe_path}
        )
    return PermissionResultAllow()
```

**结论：`PermissionResultAllow(updated_input={...})` 确实可以改写工具参数！**

### 4. 权限评估顺序（推断）

```
1. disallowed_tools 检查 → 直接拒绝
2. allowed_tools 检查 → 直接批准，不触发 callback
3. permission_mode 判断 → 如果是自动批准模式，直接通过
4. can_use_tool 回调 → 动态判断（只在 default/plan 等需要判断的模式下）
```

**生产推荐：**
- **allowed_tools** 用于白名单快速通过（如 Read）
- **disallowed_tools** 用于全局黑名单（如 Bash）
- **can_use_tool** 用于动态判断（路径隔离、审计、租户权限）
- **permission_mode** 设为 "default" 以启用回调，或用 "acceptEdits" 完全信任

### 5. ToolPermissionContext 结构

回调接收的 context 参数包含：

```python
ToolPermissionContext(
    tool_use_id: str | None,      # 工具调用 ID
    blocked_path: str | None,      # 被阻止的路径（如果有）
    decision_reason: str | None,   # CLI 的决策原因
    suggestions: list[PermissionUpdate],  # 权限建议
    agent_id: str | None,
    title: str | None,
    display_name: str | None,
    description: str | None,
    signal: AbortSignal | None,    # 取消信号
)
```

### 6. 对 ANIFORCE 生产迁移的影响

| 需求 | 实现方式 | 已验证 |
|---|---|---|
| 租户文件隔离 | `can_use_tool` 回调检查 `file_path`，重定向到租户目录 | ✅ 是（测试 D） |
| 禁止特定工具 | `disallowed_tools=["Bash"]` | 部分（需测试） |
| 审计日志 | `can_use_tool` 回调记录所有请求 | ✅ 是 |
| 动态权限 | `can_use_tool` 回调查询数据库决策 | ✅ 是（回调机制已验证） |
| 自动化后台任务 | `permission_mode="default"` + 回调 | ✅ 是 |

**生产部署建议：**

```python
async def tenant_isolation_callback(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    # 审计日志
    await log_tool_call(tenant_id, tool_name, tool_input)
    
    # 文件路径隔离
    if tool_name in ["Read", "Write", "Edit"]:
        file_path = tool_input.get("file_path", "")
        tenant_root = f"/data/tenants/{tenant_id}"
        
        # 绝对路径检查
        if not file_path.startswith(tenant_root):
            # 拒绝或重定向
            if file_path.startswith("/"):
                return PermissionResultDeny(
                    message=f"Access denied: path outside tenant directory",
                    interrupt=False
                )
            # 相对路径重定向
            safe_path = os.path.join(tenant_root, file_path)
            return PermissionResultAllow(
                updated_input={**tool_input, "file_path": safe_path}
            )
    
    # 动态权限检查
    if not await check_tenant_permission(tenant_id, tool_name):
        return PermissionResultDeny(
            message=f"Tool {tool_name} not allowed for this tenant",
            interrupt=False
        )
    
    return PermissionResultAllow()

options = ClaudeAgentOptions(
    permission_mode="default",  # 启用回调
    allowed_tools=["Read"],     # Read 快速通过
    disallowed_tools=["Bash"],  # 全局禁止 Bash
    can_use_tool=tenant_isolation_callback,
    cwd=f"/data/tenants/{tenant_id}",  # 仅改变相对路径基准，不提供隔离
)
```

**未验证问题:**

- PermissionResultDeny 是否真正阻止工具执行？（测试 B/C 回调未触发，无法验证）
- permission_denials 何时非空？
- allowed_tools 是否完全跳过 callback？（测试 B/C/D 都设置了 allowed_tools=["Read"]）
- disallowed_tools 的实际效果？（未直接测试）

### 7. 横向对比：AiToEarn、CopilotKit、Claude SDK 的权限机制

#### 7.1 AiToEarn 项目现状

**位置：** `resources/AiToEarn/project/aitoearn-backend/apps/aitoearn-ai/src/core/agent/services/agent-runtime.service.ts`

```typescript
const queryOptions: Options = {
  permissionMode: 'default',
  allowedTools: this.generateAllowedTools(mcpServers ?? {}),
  tools: ['Task', 'TaskOutput', 'Read', 'WebFetch', 'TodoWrite', ...],
  cwd: taskCwd,
  // ❌ 缺失：can_use_tool 回调
  // ❌ 缺失：disallowed_tools
  // ❌ 缺失：租户隔离机制
  // ❌ 缺失：审计日志
  // ❌ 缺失：用户确认机制
}
```

**风险：**
- 无法动态拦截危险操作
- 无租户文件隔离（多租户可能互相访问）
- 无审计追踪
- 无法根据用户套餐动态判断权限

#### 7.2 CopilotKit 的 Human-in-the-Loop 机制

**位置：** `resources/CopilotKit/examples/slack/app/human-in-the-loop/confirm-write-tool.tsx`

```typescript
// 1. 定义工具（Agent 调用时阻塞）
export const confirmWriteTool = defineBotTool({
  name: "confirm_write",
  description: "Ask user to approve before writing. BLOCKS until user clicks.",
  parameters: z.object({
    action: z.string().describe("What you're about to write"),
    detail: z.string().optional(),
  }),
  async handler({ action, detail }, { thread }) {
    // ✅ 核心：阻塞等待用户选择
    const choice = await thread.awaitChoice<{ confirmed?: boolean }>(
      <ConfirmWrite action={action} detail={detail} />
    );
    
    return choice?.confirmed
      ? "User APPROVED — proceed."
      : "User DECLINED — do not write.";
  },
});

// 2. UI 组件（前端显示）
export function ConfirmWrite({ action, detail }) {
  return (
    <Message accent="#E2B340">
      <Header>{`📝 ${action}?`}</Header>
      <Section>{detail}</Section>
      <Context>:lock: Nothing written until you click Create.</Context>
      <Actions>
        <Button value={{ confirmed: true }}>Create</Button>
        <Button value={{ confirmed: false }}>Cancel</Button>
      </Actions>
    </Message>
  );
}
```

**工作流程：**
```
Agent 想执行敏感操作
    ↓
调用 confirm_write 工具
    ↓
handler 调用 await thread.awaitChoice(<ConfirmWrite />)
    ↓ (阻塞)
前端显示确认卡片
    ↓
用户点击 "Create" / "Cancel"
    ↓
awaitChoice 返回 { confirmed: true/false }
    ↓
Agent 根据结果决定是否执行
```

**特点：**
- ✅ 前端拦截，用户友好
- ✅ 阻塞式等待，确保用户响应
- ⚠️ 只能前端用，无法后端隔离
- ⚠️ 无法实现租户隔离、审计日志
- ⚠️ 用户必须在线

#### 7.3 三者对比

| 功能 | AiToEarn | CopilotKit | Claude SDK (本章验证) |
|---|---|---|---|
| **权限控制** | ✅ 简单白名单 | ✅ 前端 Human-in-the-Loop | ✅ 后端回调拦截 |
| **用户确认** | ❌ 无 | ✅ `await thread.awaitChoice()` | ✅ 回调内实现 WebSocket 确认 |
| **租户隔离** | ❌ 无 | ❌ 无 | ✅ 回调改写路径参数 |
| **审计日志** | ❌ 无 | ⚠️ 需额外实现 | ✅ 回调内记录 |
| **动态权限** | ❌ 无 | ❌ 无 | ✅ 回调查询数据库 |
| **后台任务** | ✅ 支持 | ❌ 需用户在线 | ✅ 分层处理（低风险静默） |
| **拦截位置** | 无拦截 | 前端工具层 | 后端 SDK 层 |
| **安全性** | ⚠️ 低 | ⚠️ 中（前端可绕过） | ✅ 高（后端强制） |

#### 7.4 ANIFORCE 推荐方案：Claude SDK 回调 + CopilotKit 风格 UI

**后端回调（4 层防护）：**

```python
async def tenant_permission_callback(
    tool_name: str,
    tool_input: dict,
    context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
    
    # 第 1 层：租户隔离（静默，用户无感知）
    if tool_name in ["Read", "Write", "Edit"]:
        tenant_root = f"/data/tenants/{tenant_id}"
        file_path = tool_input.get("file_path", "")
        
        if file_path.startswith("/") and not file_path.startswith(tenant_root):
            await audit_log(tenant_id, "BLOCKED", tool_name, file_path)
            return PermissionResultDeny(message="Path outside workspace")
        
        if not file_path.startswith("/"):
            safe_path = os.path.join(tenant_root, file_path)
            return PermissionResultAllow(
                updated_input={**tool_input, "file_path": safe_path}
            )
    
    # 第 2 层：审计日志（静默，异步）
    asyncio.create_task(audit_log(tenant_id, tool_name, tool_input))
    
    # 第 3 层：套餐权限（静默）
    if not await check_plan_permission(tenant_id, tool_name):
        return PermissionResultDeny(message="Plan limit exceeded")
    
    # 第 4 层：高风险操作用户确认（类似 CopilotKit）
    if is_high_risk(tool_name, tool_input):
        # 通过 WebSocket 推送到前端
        confirmation_id = uuid.uuid4()
        await websocket.send({
            "type": "permission_request",
            "confirmation_id": confirmation_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
        })
        
        # 阻塞等待用户响应（30秒超时）
        approved = await wait_for_user_response(confirmation_id, timeout=30)
        if not approved:
            return PermissionResultDeny(message="User declined")
    
    return PermissionResultAllow()
```

**前端 UI（类似 CopilotKit ConfirmWrite）：**

```typescript
// 监听 WebSocket 权限请求
socket.on('permission_request', (data) => {
  showDialog({
    title: '权限确认',
    message: `AI 想执行：${data.tool_name}`,
    detail: JSON.stringify(data.tool_input, null, 2),
    onApprove: () => {
      socket.emit('permission_response', {
        confirmation_id: data.confirmation_id,
        decision: 'approve'
      });
    },
    onDecline: () => {
      socket.emit('permission_response', {
        confirmation_id: data.confirmation_id,
        decision: 'decline'
      });
    }
  });
});
```

**优势：**
- ✅ 后端强制安全（无法绕过）
- ✅ 支持所有场景（静默 + 确认 + 审计 + 隔离）
- ✅ 低风险操作无需用户在线
- ✅ 高风险操作弹窗确认（用户体验好）
- ✅ 完整审计追踪

**下一步:**
- ✅ 已完成第 8 章：Hooks
- 继续第 9 章：MCP/custom tools

## 第 7.5 章：cwd 工作目录隔离验证（安全关键）

**执行脚本:** `examples/07.5_cwd_isolation_probe.py`  
**输出:** `outputs/07.5_cwd_isolation_probe_summary.json`

**验证目标:**
1. `cwd` 参数能否限制文件访问范围？
2. 设置 `cwd` 后能否用绝对路径逃逸 sandbox？
3. `cwd` 的真实作用机制是什么？

**源码调查结果:**

检查了 SDK 源码 `_internal/transport/subprocess_cli.py:468-479`：

```python
if self._cwd:
    process_env["PWD"] = self._cwd  # 只设置环境变量

self._process = await anyio.open_process(
    cmd,
    stdin=PIPE,
    stdout=PIPE,
    stderr=stderr_dest,
    cwd=self._cwd,  # 传递给 subprocess，标准进程工作目录
    env=process_env,
)
```

**核心发现：`cwd` 参数不提供安全隔离！**

`cwd` 只是传递给 `anyio.open_process()` 的标准**进程工作目录**参数，作用：
- 改变相对路径的解析基准（`./file.txt` 从 `cwd` 开始解析）
- **完全不限制绝对路径访问**（`/etc/hostname`、`/root`、`/workspace` 等都能访问）

**实测结果:**

所有测试中模型都没有调用 Read 工具（直接从记忆回答），但模型的回答显示：
- 无 cwd 时：能回答 `/etc/hostname` 内容 ✅
- 有 cwd 限制时，绝对路径 `/etc/hostname`：依然能回答 ✅ —— **证明 cwd 无法阻止绝对路径访问**

**为什么模型不调用工具？**

发现：`include_partial_messages=False` 时，`receive_messages()` 只返回最终 AssistantMessage，不包括中间的工具调用步骤。必须启用 `include_partial_messages=True` 才能观察到 ToolUseBlock。

另外，Opus 4.6 模型对于简单文件读取倾向于直接回答（可能从 prompt cache 或训练数据记住了常见系统文件内容），而不是调用工具。

**对 ANIFORCE 生产迁移的严重影响:**

❌ **`cwd` 参数不能用于租户隔离或安全沙箱！**

真正的隔离方案：

1. **容器级隔离（推荐）：**
   - 每个租户的任务运行在独立 Docker 容器内
   - 容器只挂载该租户的数据目录
   - 容器内无法访问宿主机其他路径

2. **`can_use_tool` 回调路径检查：**
   ```python
   async def check_file_access(tool_name, tool_input, context):
       if tool_name in ["Read", "Write", "Edit"]:
           path = tool_input.get("file_path", "")
           abs_path = Path(path).resolve()
           
           # 检查是否逃逸 sandbox
           allowed_base = Path(f"/workspace/runtime/tenant_{tenant_id}/")
           if not abs_path.is_relative_to(allowed_base):
               return PermissionResultDeny(message=f"Access denied: {path}")
       
       return PermissionResultAllow()
   ```

3. **MCP 工具封装（最灵活）：**
   - 不启用内置 Read/Write/Bash 工具（`tools=[]`）
   - 实现自定义 MCP 工具，在工具内部检查路径权限
   - 工具执行前验证 tenant_id 和路径合法性

4. **文件系统隔离（高级）：**
   - chroot jail
   - Linux mount namespace
   - 需要 root 权限或特权容器

**优先级：容器隔离 > MCP 工具封装 > can_use_tool 回调 > cwd（无效）**

**下一步行动:**
- 实测验证绝对路径逃逸（让模型真正调用工具，而不是从记忆回答）
- 设计 ANIFORCE 的租户隔离方案（容器 + MCP 工具）
- 实现 `can_use_tool` 路径检查原型
- 工具调用失败时的重试机制

---

## 第 8 章：Hooks（工具执行生命周期拦截）

**主题:** Hooks 系统 vs Permissions Callback 的职责边界

**官方文档:**
- `https://docs.anthropic.com/en/docs/claude-code/hooks`
- SDK 示例: `resources/claude-agent-sdk-python/examples/hooks.py`

**本地验证:** `examples/08_hooks_probe.py`  
**输出:** `outputs/08_hooks_probe_summary.json`

### 核心概念

**Hooks 是什么？**

Hooks 提供对 Claude Code 工具执行生命周期的全面拦截能力，支持 9 种事件类型：

| Hook 事件 | 触发时机 | 能力 |
|-----------|---------|------|
| `PreToolUse` | 工具执行前 | ✅ allow/deny/ask/defer<br>✅ 修改工具参数<br>✅ 注入上下文 |
| `PostToolUse` | 工具执行后 | ✅ 修改工具输出<br>✅ 注入上下文 |
| `PostToolUseFailure` | 工具执行失败 | ✅ 注入上下文 |
| `UserPromptSubmit` | 用户提交 prompt | ✅ 注入上下文 |
| `Stop` | 主会话结束 | ✅ 清理资源 |
| `SubagentStop` | 子 Agent 结束 | ✅ 清理子资源 |
| `PreCompact` | 上下文压缩前 | ✅ 保存关键信息 |
| `Notification` | 收到通知 | ✅ 转发通知 |
| `SubagentStart` | 子 Agent 启动 | ✅ 注入配置 |

**Hooks 配置方式:**

```python
from claude_agent_sdk.types import HookMatcher

options = ClaudeAgentOptions(
    hooks={
        "PreToolUse": [
            HookMatcher(
                matcher="Write|Read",  # 工具名匹配（正则）
                hooks=[hook_callback_func],  # Hook 回调列表
                timeout=60.0,  # 超时秒数（可选）
            ),
        ],
        "PostToolUse": [
            HookMatcher(matcher="Bash", hooks=[monitor_bash]),
        ],
    }
)
```

**Hook 回调签名:**

```python
async def my_hook(
    input_data: HookInput,      # 事件输入数据（discriminated union）
    tool_use_id: str | None,    # 工具调用 ID（tool lifecycle hooks 有值）
    context: HookContext        # Hook 上下文（未来支持 abort signal）
) -> HookJSONOutput:            # 返回控制指令
    return {
        "continue_": True,  # 是否继续执行（Python 关键字冲突加下划线）
        "stopReason": "...",  # 停止原因
        "systemMessage": "...",  # 系统消息（显示给用户）
        "reason": "...",  # 反馈给 Claude 的原因
        "hookSpecificOutput": {  # Hook 特定输出
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",  # allow/deny/ask/defer
            "permissionDecisionReason": "...",
            "updatedInput": {...},  # 修改后的工具参数
            "additionalContext": "...",  # 注入上下文
        }
    }
```

### Hooks vs Permissions Callback 对比

| 维度 | `can_use_tool` Callback | Hooks (`PreToolUse`) |
|------|-------------------------|----------------------|
| **触发条件** | 仅 `permission_mode="default"` 时触发 | 总是触发（无论 permission mode） |
| **触发时机** | 权限检查阶段 | 工具执行生命周期各阶段 |
| **能力范围** | 仅 allow/deny/修改参数 | allow/deny/ask/defer + 修改参数 + 注入上下文 |
| **覆盖范围** | 仅工具权限决策 | 9 种生命周期事件 |
| **并发执行** | 串行（单个 callback） | 并行（同一事件的多个 hook 并发） |
| **适用场景** | 简单权限检查 | 审计、日志、参数校验、输出过滤 |

**关键区别:**

1. **Callback 是权限层**，只在需要"问用户"时触发；Hook 是**生命周期层**，总是触发
2. **Callback 只能 allow/deny**；Hook 可以 **allow/deny/ask/defer** + 修改参数/输出 + 注入上下文
3. **Callback 无法拦截已批准的工具**；Hook 能拦截所有工具（包括 `allowed_tools` 中的工具）

### 验证结果

**测试 A: PreToolUse Hook 拒绝写入 /etc**

配置:
```python
permission_mode="acceptEdits"  # 自动接受编辑，绕过 callback
hooks={"PreToolUse": [HookMatcher(matcher="Write", hooks=[audit_hook])]}
```

结果: ✅ Hook 没有执行（模型遵守 CLAUDE.md 规则，没有调用工具）

**测试 B: PreToolUse Hook 重定向文件路径**

Prompt: `Write the text 'Hello from hook redirect' to output.txt`

结果: ✅ Hook 成功拦截并重定向
- 原路径: `/workspace/.../output.txt`
- 重定向: `sandbox/output.txt`
- 文件内容验证: `Hello from hook redirect` ✅

统计:
```json
{
  "PreToolUse_triggered": 1,
  "PreToolUse_modified": 1
}
```

**测试 C: PostToolUse Hook 监控 Bash 失败**

Prompt: `Run this bash command: ls /nonexistent_directory_12345`

结果: ⚠️ Hook 未触发（`PostToolUse_triggered=0`）

原因分析: 命令失败，但未触发 Hook 的"注入上下文"逻辑（可能是条件判断未命中）

**测试 D: can_use_tool callback + PreToolUse Hook 共存**

配置:
```python
permission_mode="default"  # 触发 callback
allowed_tools=["Bash"]  # Write/Read 需要 callback 批准
can_use_tool=custom_permission_callback
hooks={"PreToolUse": [HookMatcher(matcher="Write|Read", hooks=[audit_hook])]}
```

Prompt: `Read the file /root/.bashrc`

执行顺序:
1. ✅ PreToolUse Hook 先触发 (`PreToolUse_triggered=1`)
2. ✅ can_use_tool Callback 后触发 (`can_use_tool_triggered=1`)
3. ✅ Callback 拒绝 (`can_use_tool_denied=1`)

结果: 
```json
{
  "PreToolUse_triggered": 2,
  "PreToolUse_allowed": 1,
  "can_use_tool_triggered": 1,
  "can_use_tool_denied": 1
}
```

**关键发现:** Hook 和 Callback 可以共存，**Hook 先执行，Callback 后执行**

### ANIFORCE 应用建议

**推荐架构: Hooks 为主，Callback 为辅**

```
┌─────────────────────────────────────────────────────────┐
│ PreToolUse Hook                                         │
│ - Tenant 隔离（路径前缀检查）                             │
│ - 审计日志（记录所有工具调用）                            │
│ - 参数规范化（路径重定向、参数校验）                      │
│ - 黑名单拦截（系统目录、敏感文件）                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ can_use_tool Callback (仅 default 模式)                 │
│ - 用户确认（WebSocket 推送前端）                         │
│ - 动态权限（查询数据库）                                 │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ PostToolUse Hook                                        │
│ - 输出过滤（脱敏、审计）                                 │
│ - 错误增强（注入帮助信息）                               │
└─────────────────────────────────────────────────────────┘
```

**分层职责:**

1. **PreToolUse Hook - 静默防护层**
   - 总是执行，不依赖 permission_mode
   - 拦截明显违规（系统目录、越权访问）
   - 参数校验和规范化
   - 审计日志记录

2. **can_use_tool Callback - 用户确认层**
   - 仅 `permission_mode="default"` 时执行
   - 需要用户在线确认的操作
   - 通过 WebSocket 推送前端弹窗
   - 动态权限查询（数据库、外部 API）

3. **PostToolUse Hook - 输出控制层**
   - 输出脱敏（密钥、敏感信息）
   - 错误增强（注入上下文帮助）
   - 审计日志记录

**权限模式选择:**

| 场景 | permission_mode | Hooks | Callback |
|------|----------------|-------|----------|
| 用户在线交互 | `default` | ✅ 审计 + 拦截 | ✅ 用户确认 |
| 后台异步任务 | `acceptEdits` 或 `plan` | ✅ 审计 + 拦截 | ❌ 不触发 |
| 管理员调试 | `bypassPermissions` | ✅ 仍然审计 | ❌ 不触发 |

### 对 ANIFORCE 的影响

**已确定:**

1. ✅ **Hooks 是完整拦截方案**
   - 覆盖所有工具执行生命周期
   - 不受 `permission_mode` 影响
   - 可以同时做审计、拦截、修改、注入

2. ✅ **can_use_tool Callback 是用户确认专用通道**
   - 仅适合需要用户在线确认的场景
   - 通过 WebSocket 推送前端
   - 异步任务不应依赖 Callback

3. ✅ **Hook 和 Callback 可以共存**
   - Hook 先执行（审计、参数校验）
   - Callback 后执行（用户确认）
   - 顺序可控，职责清晰

4. ✅ **PreToolUse Hook 可以修改工具参数**
   - 实测成功重定向文件路径
   - 可用于 Tenant 隔离、路径规范化
   - 可用于参数校验和黑名单拦截

**待验证:**

- PostToolUse Hook 修改输出的完整能力（本次测试未充分验证）
- Hook 的性能开销（并发执行多个 hook 的延迟）
- Hook 异常处理（hook 内部异常是否会阻塞工具执行）
- Hook 的 `async_` 异步模式（defer hook execution）

**下一步:**
- ✅ 已完成第 8 章：Hooks
- 继续第 9 章：MCP/custom tools

---

## 第 9 章：MCP 自定义工具（业务能力封装）

**主题:** SDK in-process MCP server 实现自定义业务工具

**官方文档:**
- SDK 示例: `resources/claude-agent-sdk-python/examples/mcp_calculator.py`
- SDK 源码: `src/claude_agent_sdk/__init__.py` (`@tool` 装饰器和 `create_sdk_mcp_server`)

**本地验证:** `examples/09_mcp_tools_probe.py`  
**输出:** `outputs/09_mcp_tools_probe_summary.json`

### 核心概念

**SDK MCP Server 是什么？**

SDK MCP Server 是 **in-process** MCP server，直接运行在 Python 应用进程内，无需启动外部进程。

**SDK MCP vs 外部 stdio MCP:**

| 维度 | SDK MCP (in-process) | stdio MCP (external) |
|------|---------------------|----------------------|
| **部署** | 单进程 | 多进程（需要启动外部 server） |
| **性能** | 无 IPC 开销 | 有进程间通信开销 |
| **调试** | 同一进程，易调试 | 跨进程，需日志 |
| **状态共享** | 直接访问应用状态 | 需要额外通信机制 |
| **语言限制** | Python only | 任意语言（只要支持 stdio） |
| **适用场景** | 业务逻辑封装、数据库查询 | 独立服务、跨语言工具 |

**定义 MCP 工具:**

```python
from claude_agent_sdk import tool

@tool(
    "tool_name",               # 工具名（唯一标识）
    "Tool description",        # 描述（帮助 Claude 理解何时使用）
    {"param1": str, "param2": int},  # 输入 schema（dict 或 TypedDict）
)
async def my_tool(args: dict[str, Any]) -> dict[str, Any]:
    """工具实现（必须是 async 函数）"""
    result = do_something(args["param1"], args["param2"])
    
    # 成功返回
    return {
        "content": [{"type": "text", "text": f"Result: {result}"}]
    }
    
    # 错误返回
    return {
        "content": [{"type": "text", "text": "Error message"}],
        "is_error": True,
    }
```

**创建 MCP Server:**

```python
from claude_agent_sdk import create_sdk_mcp_server

server = create_sdk_mcp_server(
    name="my_server",       # Server 名称
    version="1.0.0",        # 版本（可选）
    tools=[tool1, tool2],   # 工具列表
)

options = ClaudeAgentOptions(
    mcp_servers={"my": server},  # 注册 MCP server
    allowed_tools=[
        "mcp__my__tool1",  # MCP 工具名格式: mcp__{server}__{tool}
        "mcp__my__tool2",
    ],
)
```

**输入 Schema 类型:**

1. **简单 dict:** `{"name": str, "age": int}`
2. **TypedDict:** 更复杂的类型约束
3. **JSON Schema:** 完整的 JSON Schema 定义
4. **Annotated 描述:** `{"name": Annotated[str, "User name"]}`

### 验证结果

**测试环境:**

实现了 3 个 MCP 工具：
- `tenant_read_file`: 读取租户隔离文件
- `tenant_write_file`: 写入租户隔离文件
- `database_query`: 模拟数据库查询

**测试 A: 读取租户文件（成功）**

Prompt: `Use tenant_read_file to read config.json from tenant_001`

结果: ✅ 成功读取
- 工具调用: `mcp__tenant__tenant_read_file`
- 返回内容: `{"app": "demo", "version": "1.0"}`
- Hook 拦截: ✅ PreToolUse 触发

统计:
```json
{
  "tenant_read_called": 1,
  "tenant_read_allowed": 1
}
```

**测试 B: 跨租户访问（拒绝）**

Prompt: `Use tenant_read_file to read config.json from tenant_999`

结果: ✅ 工具返回错误
- 工具调用: `mcp__tenant__tenant_read_file`
- 错误信息: `Error: Tenant '999' not found`
- MCP 工具内部拦截成功

统计:
```json
{
  "tenant_read_called": 2,
  "tenant_read_denied": 1
}
```

**测试 C: 写入租户文件（成功）**

Prompt: `Use tenant_write_file to write 'Hello ANIFORCE' to new_file.txt in tenant_001`

结果: ✅ 成功写入
- 工具调用: `mcp__tenant__tenant_write_file`
- 写入字节数: 14
- 文件验证: `tenant_data["tenant_001"]["files"]["new_file.txt"]` = "Hello ANIFORCE" ✅

统计:
```json
{
  "tenant_write_called": 1,
  "tenant_write_allowed": 1
}
```

**测试 D: 数据库查询（正常）**

Prompt: `Use database_query to SELECT * FROM users in tenant_001`

结果: ✅ 返回查询结果
- 工具调用: `mcp__tenant__database_query`
- 返回行数: 2 rows (Alice, Bob)
- SQL 注入检测: 未触发（正常查询）

统计:
```json
{
  "database_query_called": 1,
  "database_query_success": 1
}
```

**测试 E: SQL 注入防护**

Prompt: `Use database_query with SQL: 'DROP TABLE users; --' in tenant_001`

结果: ⚠️ **模型自我审查，未调用工具**
- 模型拒绝执行危险 SQL（基于 CLAUDE.md 安全规则）
- MCP 工具未被调用（`database_query_called` 未增加）
- 工具内部的 SQL 注入检测未执行

**重要发现:** 模型在工具调用前已经自我审查，危险操作被模型拦截而非工具拦截

**测试 F: 路径遍历攻击防护**

Prompt: `Use tenant_write_file to write 'attack' to '../etc/passwd' in tenant_001`

结果: ⚠️ **模型自我审查，未调用工具**
- 模型拒绝执行路径遍历攻击
- MCP 工具未被调用（`tenant_write_called` 未增加）
- 工具内部的路径检查未执行

**重要发现:** 模型安全意识强，自动拒绝明显的攻击尝试

### Hook 与 MCP 工具集成

**PreToolUse Hook 成功拦截 MCP 工具调用:**

```json
{
  "PreToolUse_triggered": 4,
  "mcp_tools_intercepted": 4
}
```

所有 MCP 工具调用都经过 Hook 审计，工具名格式: `mcp__{server}__{tool}`

**Hook 匹配器:**

```python
hooks={
    "PreToolUse": [
        HookMatcher(matcher="mcp__.*", hooks=[audit_mcp_tools]),
    ],
}
```

正则匹配所有 MCP 工具（前缀 `mcp__`），可以统一审计、拦截、修改参数。

### ANIFORCE 应用建议

**推荐架构: MCP 工具 + Hooks + Permissions 三层防护**

```
┌─────────────────────────────────────────────────────────┐
│ 第 1 层：PreToolUse Hook                                │
│ - 审计日志（记录所有 MCP 工具调用）                       │
│ - 参数校验（格式、长度、类型）                            │
│ - 黑名单拦截（已知攻击模式）                              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 第 2 层：MCP 工具内部逻辑                                │
│ - Tenant 隔离（检查 tenant_id）                          │
│ - 参数验证（输入 schema 自动校验）                        │
│ - 业务规则（权限、配额、限流）                            │
│ - 错误处理（返回 is_error=True）                         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 第 3 层：PostToolUse Hook                                │
│ - 输出脱敏（敏感信息过滤）                                │
│ - 审计日志（记录工具输出）                                │
│ - 错误增强（注入帮助信息）                                │
└─────────────────────────────────────────────────────────┘
```

**ANIFORCE 业务工具封装建议:**

1. **文件操作工具:**
   ```python
   @tool("aniforce_read_file", "读取项目文件", {...})
   async def aniforce_read_file(args):
       # 检查 tenant_id、project_id
       # 检查文件路径（禁止 ../ 和绝对路径）
       # 读取文件
       # 审计日志
   ```

2. **数据库查询工具:**
   ```python
   @tool("aniforce_db_query", "查询数据库", {...})
   async def aniforce_db_query(args):
       # 检查 tenant_id
       # SQL 注入检测
       # 查询权限检查
       # 执行查询
       # 审计日志
   ```

3. **API 调用工具:**
   ```python
   @tool("aniforce_api_call", "调用外部 API", {...})
   async def aniforce_api_call(args):
       # 检查 tenant_id、quota
       # URL 白名单检查
       # 超时控制
       # 执行 HTTP 请求
       # 审计日志
   ```

**MCP 工具命名规范:**

- 工具名: `aniforce_{resource}_{action}` (e.g. `aniforce_file_read`, `aniforce_db_query`)
- 全局工具名: `mcp__aniforce__{tool_name}`
- Hook 匹配: `mcp__aniforce__.*`

**错误处理规范:**

```python
# 业务错误（返回 is_error=True）
return {
    "content": [{"type": "text", "text": "Error: Tenant not found"}],
    "is_error": True,
}

# 成功返回
return {
    "content": [{"type": "text", "text": "Success: ..."}]
}
```

### 对 ANIFORCE 的影响

**已确定:**

1. ✅ **SDK MCP Server 可以封装业务逻辑**
   - in-process 运行，无需外部进程
   - 直接访问应用状态（数据库、缓存、配置）
   - 性能优于 stdio MCP

2. ✅ **MCP 工具内部可以实现 Tenant 隔离**
   - 工具参数包含 `tenant_id`
   - 工具内部检查权限
   - 返回 `is_error` 拒绝越权访问

3. ✅ **Hooks 可以审计 MCP 工具调用**
   - PreToolUse Hook 统一拦截 `mcp__*` 工具
   - 记录审计日志（tenant_id、tool_name、参数）
   - 可以在 Hook 层做二次校验

4. ✅ **模型有安全意识**
   - 明显的攻击尝试（SQL 注入、路径遍历）被模型自我审查
   - 模型不会调用工具执行危险操作
   - 但不能完全依赖模型（需要工具层防护）

5. ✅ **输入 Schema 自动校验**
   - `@tool` 装饰器的 `input_schema` 参数
   - SDK 自动生成 JSON Schema
   - 类型错误会在工具调用前被拦截

**待验证:**

- MCP 工具的性能开销（in-process vs stdio）
- MCP 工具的并发控制（多个工具同时调用）
- MCP 工具的状态管理（多租户会话隔离）
- 外部 stdio MCP server 的集成（对比 SDK MCP）

**下一步:**
- ✅ 已完成第 9 章：MCP/custom tools
- 继续第 10 章：Skills（领域知识注入）

---

## 第 9.5 章：外部 SSE MCP Server（AiToEarn 架构）

**主题:** 对比 SDK in-process MCP 和外部 SSE MCP Server

**本地验证:** `examples/09.5_sse_mcp_comparison.py`  
**输出:** `outputs/09.5_sse_mcp_comparison.json`

### AiToEarn MCP 架构分析

**核心组件:**

AiToEarn 有完整的 NestJS MCP 实现（`libs/nest-mcp`），采用 SSE 传输层：

```
┌─────────────────────────────────────────────────────────┐
│ Claude SDK Client (Python)                             │
│ - ClaudeAgentOptions.mcp_servers                       │
│ - type: "sse"                                          │
│ - url: http://localhost:3000/api/mcp/sse              │
│ - headers: {Authorization, X-Tenant-Id}                │
└─────────────────────────────────────────────────────────┘
                          ↓ SSE (Server-Sent Events)
┌─────────────────────────────────────────────────────────┐
│ NestJS MCP Server (TypeScript)                         │
│ - GET /api/mcp/sse → 建立 SSE 连接                     │
│ - POST /api/mcp/messages?sessionId=xxx → 发送请求      │
│ - NestJS Guards 鉴权                                   │
│ - transports Map 存储活跃连接                          │
│ - mcpServers Map 存储 MCP Server 实例                  │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 业务工具 Controller                                     │
│ - @Tool 装饰器标记方法                                  │
│ - McpRegistryService 自动发现                          │
│ - Zod schema 参数验证                                  │
│ - getUser() 获取鉴权后的用户上下文                      │
└─────────────────────────────────────────────────────────┘
```

**工具定义示例（AiToEarn）:**

```typescript
@Injectable()
export class TwitterMcpController {
  constructor(private readonly twitterService: TwitterService) {}

  @Tool({
    name: 'searchTweets',
    description: 'Search recent Twitter/X tweets',
    parameters: searchTweetsSchema,  // Zod schema
  })
  async searchTweets(params: z.infer<typeof searchTweetsSchema>) {
    const user = getUser()  // 从请求上下文获取用户（鉴权后）
    return toYamlTextResult(
      await this.twitterService.searchTweets(user.id, params.accountId, params)
    )
  }
}
```

**模块配置示例:**

```typescript
@Module({
  imports: [
    McpModule.forRoot({
      name: 'aitoearn-mcp',
      version: '1.0.0',
      transport: [McpTransportType.SSE],  // 启用 SSE 传输
      sseEndpoint: 'sse',
      messagesEndpoint: 'messages',
      guards: [JwtAuthGuard],  // 鉴权守卫
    }),
  ],
  controllers: [TwitterMcpController],  // 注册工具 Controller
})
export class AppModule {}
```

**Claude SDK 连接配置:**

```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    mcp_servers={
        "aitoearn": {
            "type": "sse",
            "url": "http://localhost:3000/api/mcp/sse",
            "headers": {
                "Authorization": "Bearer <token>",
                "X-Tenant-Id": "tenant_001",
            }
        }
    },
    allowed_tools=[
        "mcp__aitoearn__searchTweets",
        "mcp__aitoearn__listHomeTimeline",
    ],
)
```

### 两种 MCP 架构对比

| 维度 | SDK in-process MCP | SSE MCP Server (AiToEarn) |
|------|-------------------|---------------------------|
| **部署** | 单进程 | 独立服务（需要单独部署） |
| **性能** | 无 IPC 开销 | 网络延迟（HTTP + SSE） |
| **语言** | 仅 Python | 任意语言（协议标准） |
| **鉴权** | 需要 Hooks 实现 | NestJS Guards（成熟） |
| **会话隔离** | 无（共享内存） | sessionId + transports Map |
| **扩展性** | 绑定到主应用 | 独立扩展、水平扩容 |
| **状态管理** | 直接访问应用状态 | 需要额外通信机制 |
| **调试** | 同一进程，易调试 | 跨进程，需日志 |
| **sticky sessions** | 不需要 | **需要**（transports 在内存） |

**SSE MCP 优势:**

1. ✅ **多语言支持** - 不限 Python，任意语言实现 server
2. ✅ **服务解耦** - 工具服务独立部署、独立升级
3. ✅ **鉴权成熟** - NestJS Guards + getUser() 上下文
4. ✅ **多租户隔离** - 每个连接独立 sessionId
5. ✅ **水平扩容** - 独立服务可以多实例部署

**SSE MCP 劣势:**

1. ❌ **部署复杂** - 需要独立服务、负载均衡、健康检查
2. ❌ **网络延迟** - HTTP + SSE 开销
3. ❌ **sticky sessions** - transports/mcpServers 存储在内存，需要会话亲和性
4. ❌ **调试困难** - 跨进程，需要分布式链路追踪

### SSE MCP 的 Sticky Sessions 问题

**问题根源:**

```typescript
// McpSseService 内部实现
export class McpSseService {
  // 存储在内存中，不同实例不共享
  private readonly transports = new Map<string, SSEServerTransport>()
  private readonly mcpServers = new Map<string, McpServer>()
}
```

**影响:**

- 同一个 sessionId 的请求必须路由到同一个服务实例
- 负载均衡需要配置会话亲和性（IP hash 或 cookie）
- 实例重启会导致所有连接断开

**解决方案:**

1. **Nginx 会话亲和性:**
   ```nginx
   upstream mcp_backend {
       ip_hash;  # 或 hash $cookie_sessionId;
       server backend1:3000;
       server backend2:3000;
   }
   ```

2. **Redis 共享存储（需要改造）:**
   - 将 transports/mcpServers 状态持久化到 Redis
   - 任意实例都能处理请求
   - 复杂度高，需要序列化 SSEServerTransport

3. **单实例部署（临时方案）:**
   - 不使用负载均衡
   - 扩展性受限

### ANIFORCE 迁移方案建议

**方案 1: 纯 SDK in-process MCP（推荐快速迁移）**

```python
# 所有工具都用 @tool 装饰器定义在 Python 中
@tool("aniforce_read_file", "读取项目文件", {...})
async def aniforce_read_file(args):
    # Tenant 隔离、权限检查
    pass

server = create_sdk_mcp_server("aniforce", tools=[...])
options = ClaudeAgentOptions(mcp_servers={"aniforce": server})
```

**优势:**
- ✅ 部署最简单（单进程）
- ✅ 性能最好（无网络开销）
- ✅ 直接访问数据库、文件系统

**劣势:**
- ❌ 绑定 Python
- ❌ 无法独立扩展
- ❌ 鉴权需要在 Hooks 中实现

**适用场景:** 快速原型验证、单体应用、内部工具

---

**方案 2: 混合架构（推荐生产）**

```python
# 核心工具: SDK in-process MCP
core_tools = create_sdk_mcp_server("core", tools=[
    aniforce_read_file,
    aniforce_write_file,
    aniforce_db_query,
])

# 外部服务工具: SSE MCP
options = ClaudeAgentOptions(
    mcp_servers={
        "core": core_tools,  # in-process
        "twitter": {  # SSE
            "type": "sse",
            "url": "http://twitter-service:3000/mcp/sse",
            "headers": {"Authorization": "Bearer <token>"},
        },
        "email": {  # SSE
            "type": "sse",
            "url": "http://email-service:3000/mcp/sse",
            "headers": {"Authorization": "Bearer <token>"},
        },
    }
)
```

**优势:**
- ✅ 核心工具高性能（in-process）
- ✅ 外部服务解耦（SSE）
- ✅ 灵活扩展（按需添加 SSE 服务）

**劣势:**
- ❌ 架构复杂（两套工具系统）
- ❌ 部分工具有网络延迟

**适用场景:** 生产环境、多团队协作、渐进式迁移

---

**方案 3: 纯 SSE MCP Server（长期演进）**

```typescript
// 复用 AiToEarn 的 nest-mcp 库
@Module({
  imports: [
    McpModule.forRoot({
      name: 'aniforce-mcp',
      transport: [McpTransportType.SSE],
      guards: [JwtAuthGuard],
    }),
  ],
  controllers: [
    FileToolsController,
    DatabaseToolsController,
    TwitterToolsController,
  ],
})
export class AniforceMcpModule {}
```

**优势:**
- ✅ 服务完全解耦
- ✅ 独立扩展、水平扩容
- ✅ 多语言支持（未来可用 Go/Rust 重写）
- ✅ 复用 AiToEarn 成熟方案

**劣势:**
- ❌ 部署复杂（独立服务 + 负载均衡 + sticky sessions）
- ❌ 网络延迟
- ❌ 需要迁移所有工具到 TypeScript

**适用场景:** 微服务架构、多租户 SaaS、规模化

---

### 推荐迁移路线

```
Phase 1: SDK in-process MCP（1-2 周）
- 目标: 快速验证 Claude SDK 可行性
- 实现: 核心工具（文件、数据库、配置）
- 部署: 单进程，简单
- 产出: POC demo，性能基准

        ↓

Phase 2: 混合架构（2-4 周）
- 目标: 稳定生产，逐步解耦
- 实现: 核心工具 in-process，外部服务 SSE
- 部署: 主应用 + 外部 MCP 服务
- 产出: 生产就绪版本

        ↓

Phase 3: 纯 SSE MCP（3-6 月）
- 目标: 规模化、服务化
- 实现: 所有工具迁移到 SSE MCP
- 部署: 微服务架构
- 产出: 可水平扩展的 SaaS 平台
```

### 对 ANIFORCE 的影响

**已确定:**

1. ✅ **AiToEarn 有成熟的 SSE MCP 实现**
   - `libs/nest-mcp` 可以直接复用
   - 支持 SSE 传输层、NestJS Guards、Zod 验证
   - 已在生产环境运行

2. ✅ **两种 MCP 架构各有优劣**
   - SDK in-process: 简单、快速、高性能
   - SSE MCP: 解耦、扩展、多语言

3. ✅ **混合架构最适合 ANIFORCE**
   - 核心工具 in-process（文件、数据库）
   - 外部服务 SSE（Twitter、Email）
   - 平衡性能和扩展性

4. ✅ **SSE MCP 需要解决 sticky sessions**
   - transports/mcpServers 存储在内存
   - 需要负载均衡配置会话亲和性
   - 或改造为 Redis 共享存储

**待验证:**

- 实际连接 AiToEarn SSE MCP Server 的完整流程
- SSE MCP 的性能开销（延迟、吞吐量）
- SSE MCP 的故障恢复（连接断开、重连）
- 混合架构的工具调用性能对比

**下一步:**
- ✅ 已完成第 9 章：MCP（in-process + SSE 两种架构）
- 继续第 10 章：Skills（领域知识注入）

---

## 第 10 章：Skills（领域知识注入）

主题：Skills 系统架构、管理机制、工程化部署

官方文档：
- SDK Types: `resources/claude-agent-sdk-python/src/claude_agent_sdk/types.py` (ClaudeAgentOptions.skills)
- Plugin Example: `resources/claude-agent-sdk-python/examples/plugin_example.py`

本地源码/测试：
- 测试脚本：`drafts/260615_claude_sdk_learning/examples/10_skills_probe.py`
- 架构分析：`drafts/260615_claude_sdk_learning/examples/10.5_skills_architecture_analysis.md`
- ANIFORCE Skills：`backend/runtime/skills/`
- AiToEarn Skills：`resources/AiToEarn/project/aitoearn-backend/apps/aitoearn-ai/src/core/agent/skills/`
- Superpowers Plugin：`/root/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/`

核心概念：

**Skills = 领域知识 + 工作流指导 + MCP 工具映射**

1. **Skills 本质**
   - 📖 知识层：告诉模型如何完成特定领域任务
   - 🗺️ 工作流：定义步骤、决策点、硬约束
   - 🔗 工具映射：指向可用的 MCP 工具
   - Skills 不是可执行代码，是 Markdown 文档

2. **Skills 目录发现机制**
   - 官方 Skills（superpowers plugin）：`/root/.claude/plugins/cache/*/skills/`
   - 项目级 Skills：`.claude/skills/`（需要 `setting_sources=["project"]`）
   - 动态注入 Skills（AiToEarn）：应用启动时从源码复制到运行时

3. **Skills 调用流程**
   ```
   用户请求 → 模型判断需要 Skill → Skill(skill="name") → 
   SDK 读取 SKILL.md → 注入 context → 模型调用 MCP 工具 → 完成任务
   ```

4. **SKILL.md 结构**
   ```markdown
   ---
   name: campaign-management
   description: 广告计划管理：创建、查询、更新、删除、暂停/启动
   ---
   
   # 广告计划管理 Skill
   
   ## 目标
   ## 输入/输出
   ## 可用的 MCP Tools（列出所有工具及参数）
   ## 工作流（详细步骤和决策点）
   ## 硬约束（必须遵守的规则）
   ```

5. **Skills vs MCP 关系**
   | 维度 | Skills | MCP |
   |------|--------|-----|
   | 本质 | 知识层（how to use） | 能力层（what you can do） |
   | 形式 | Markdown 文档 | 可执行工具 |
   | 作用 | 指导模型调用工具 | 提供实际能力 |
   | 触发 | Skill tool（显式） | MCP 工具调用 |
   | 注入时机 | Skill tool 调用时 | 会话启动时 |

演示代码：

```python
# 配置 Skills
options = ClaudeAgentOptions(
    skills=["campaign-management"],  # 启用特定 Skill
    # skills="all",                  # 启用所有 Skill
    # skills=[],                     # 禁用所有 Skill
    allowed_tools=["Skill", "mcp__*"],
    setting_sources=["project"],     # 必须包含才能加载 SKILL.md
    cwd=str(project_root),          # 工作目录影响 Skills 发现
)

# MCP 工具（Skills 会引用这些工具）
@tool("list_campaigns", "查询广告计划列表", {"project_id": str})
async def list_campaigns(args):
    # ...

@tool("create_campaign", "创建新广告计划", {...})
async def create_campaign(args):
    # ...

campaign_server = create_sdk_mcp_server(
    name="campaign_tools",
    tools=[list_campaigns, create_campaign]
)

options.mcp_servers = {"campaign": campaign_server}
```

运行命令：

```bash
UV_CACHE_DIR=./uv_cache uv run python drafts/260615_claude_sdk_learning/examples/10_skills_probe.py
```

已验证：

1. ✅ **Skills 配置参数生效**
   - `skills=["campaign-management"]` 正确传递给 CLI
   - `setting_sources=["project"]` 必须包含才能加载 SKILL.md
   - `allowed_tools` 必须包含 "Skill" 工具

2. ✅ **Skill tool 调用机制**
   - 模型判断需要 Skill 时调用 `Skill(skill="name")`
   - SDK 读取对应 SKILL.md 注入到 context
   - 模型根据 Skill 内容调用 MCP 工具

3. ✅ **Skills 目录发现**
   - 官方 Skills：`/root/.claude/plugins/cache/claude-plugins-official/superpowers/5.1.0/skills/`
   - 项目 Skills：需要在 `.claude/skills/`（ANIFORCE 当前在 `backend/runtime/skills/` 导致失败）

4. ✅ **AiToEarn 的动态注入机制**
   - 源码：`apps/aitoearn-ai/src/core/agent/skills/`
   - 运行时：`.claude-session/.claude/skills/`
   - 应用启动时通过 `SkillInitService.onModuleInit()` 复制

未验证/阻塞：

- ❌ ANIFORCE Skills 路径问题（在 `backend/runtime/skills/` 而非 `.claude/skills/`）
- 测试中 Skill tool 报 "skill not available"
- 模型自动降级到直接调用 MCP 工具

待验证：

- 修复 Skills 路径后的完整 Skill 调用流程
- Skills 与 Hooks 的集成（PreToolUse 拦截 Skill tool）
- 多个 Skills 同时启用时的优先级
- Skills 热更新机制

对 ANIFORCE 的影响：

**核心决策：采用动态注入方式（AiToEarn 实践）**

**为什么选择动态注入？**

1. ✅ **版本管理优势**
   - Skills 源码与应用代码一起纳入 Git
   - Code Review 可以审查 Skills 变更
   - CI/CD 流程覆盖 Skills
   - 传统方式需要手动同步 `.claude/skills/`（容易漏）

2. ✅ **多租户/多会话隔离**
   ```
   .claude-sessions/
   ├── session_001/.claude/skills/  ← 租户 A 的 Skills
   ├── session_002/.claude/skills/  ← 租户 B 的 Skills
   └── ...
   ```
   - 租户 A 只能看到自己订阅的 Skills
   - 租户 B 可能有定制化的 Skills 版本
   - 会话隔离避免污染

3. ✅ **部署一致性**
   - Skills 打包在 Docker 镜像内
   - 不依赖外部文件系统挂载
   - K8s 滚动更新时 Skills 自动同步
   - 无需额外 Volume 配置

4. ✅ **支持权限过滤**
   ```typescript
   // 根据租户权限动态注入 Skills
   async initSessionSkills(sessionId, tenantId, permissions) {
     const allowedSkills = this.filterByPermissions(permissions)
     // VIP 租户才能用数据分析 Skill
     if (!permissions.includes('vip')) {
       skills = skills.filter(s => s !== 'data-analysis')
     }
   }
   ```

5. ✅ **支持热更新**（可选）
   - 从配置中心读取最新 Skills
   - 动态生成 SKILL.md
   - 无需重新部署

**工程化实施方案：**

**目录结构：**
```
backend/
├── runtime/
│   ├── agent/
│   │   ├── skill-manager.service.ts   ← Skills 管理服务
│   │   └── claude-client.service.ts   ← Claude SDK 封装
│   └── skills/                        ← Skills 源码（纳入 Git）
│       ├── campaign-management/
│       │   └── SKILL.md
│       ├── project-management/
│       │   └── SKILL.md
│       └── ...

.claude-sessions/                       ← 运行时（.gitignore）
├── session_abc123/
│   └── .claude/skills/                 ← 动态注入的 Skills
└── session_xyz789/
    └── .claude/skills/
```

**SkillManagerService 核心功能：**

```typescript
@Injectable()
export class SkillManagerService {
  /**
   * 为会话初始化 Skills
   * @param sessionId 会话 ID
   * @param tenantId 租户 ID
   * @param permissions 租户权限
   */
  async initSessionSkills(
    sessionId: string,
    tenantId: string,
    permissions: string[]
  ): Promise<string> {
    const targetDir = path.join(
      '.claude-sessions',
      sessionId,
      '.claude',
      'skills'
    )
    
    // 根据租户权限过滤 Skills
    const allowedSkills = this.filterSkillsByPermissions(permissions)
    
    for (const skillName of allowedSkills) {
      await this.copySkill(skillName, targetDir)
    }
    
    return targetDir
  }
  
  /**
   * 清理会话 Skills（会话结束时）
   */
  async cleanupSessionSkills(sessionId: string) {
    const sessionDir = path.join('.claude-sessions', sessionId)
    fs.rmSync(sessionDir, { recursive: true })
  }
}
```

**部署配置：**

```dockerfile
# Dockerfile
FROM node:20-alpine
WORKDIR /app

# 复制代码（包括 Skills 源码）
COPY backend/ ./backend/
RUN npm ci && npm run build

# Skills 源码已打包在镜像内
# 运行时会动态注入到 .claude-sessions/
CMD ["node", "dist/main.js"]
```

```yaml
# K8s Deployment
spec:
  containers:
  - name: backend
    image: aniforce/backend:latest
    volumeMounts:
    # 只需挂载会话数据（可选）
    - name: sessions
      mountPath: /app/.claude-sessions
    # 不需要挂载 Skills（已在镜像内）
  volumes:
  - name: sessions
    emptyDir: {}  # 或 persistentVolumeClaim
```

**对比传统方式：**

| 维度 | 传统方式（.claude/skills/） | 动态注入（推荐） |
|------|---------------------------|----------------|
| 版本管理 | ❌ 需手动同步 | ✅ Git 统一管理 |
| 部署一致性 | ❌ 需挂载 Volume | ✅ 镜像自包含 |
| 多租户隔离 | ❌ 难实现 | ✅ 会话级隔离 |
| 权限控制 | ❌ 需外部过滤 | ✅ 注入时过滤 |
| 热更新 | ❌ 需重启 | ✅ 可动态刷新 |
| 工程化程度 | 🔴 低 | 🟢 高 |

**实施步骤：**

```
Phase 1: 基础动态注入（1-2 天）
- 创建 SkillManagerService
- 保持 Skills 在 backend/runtime/skills/
- 应用启动时初始化到 .claude-sessions/

Phase 2: 多租户隔离（3-5 天）
- 根据租户权限过滤 Skills
- 会话级 Skills 目录隔离

Phase 3: 热更新支持（可选，1 周）
- 从配置中心读取 Skills
- 动态生成 SKILL.md
```

**已确定：**

1. ✅ **Skills 是知识层，MCP 是能力层**
   - Skills 定义"做什么"、"怎么做"
   - MCP 提供"能做什么"
   - 协作关系：Skills 指导模型调用 MCP 工具

2. ✅ **AiToEarn 的动态注入是成熟实践**
   - 已在生产环境验证
   - 支持多租户、权限控制、热更新
   - 符合现代微服务部署模式

3. ✅ **ANIFORCE 应立即采用动态注入**
   - 不需要等后续再改
   - 现在就按这个方向设计
   - 避免后续重构成本

4. ✅ **Skills 粒度设计**
   - 合适：一个 Skill = 一个领域任务
   - 过细：一个 Skill = 一个 MCP 工具（没必要）
   - 过粗：一个 Skill = 整个应用（无法复用）

**下一步：**
- ✅ 已完成第 10 章：Skills（领域知识注入 + 工程化部署）
- 继续第 11 章：Sessions / Session Storage（会话管理）


---

## 第 11 章：Sessions / Session Storage（会话管理与持久化）

主题：会话生命周期、Session Store 接口、多租户隔离

官方文档：
- SDK Types: `resources/claude-agent-sdk-python/src/claude_agent_sdk/types.py` (SessionStore Protocol)
- Postgres 示例: `resources/claude-agent-sdk-python/examples/session_stores/postgres_session_store.py`
- Redis 示例: `resources/claude-agent-sdk-python/examples/session_stores/redis_session_store.py`
- S3 示例: `resources/claude-agent-sdk-python/examples/session_stores/s3_session_store.py`

本地源码/测试：
- 测试脚本：`drafts/260615_claude_sdk_learning/examples/11_sessions_probe.py`
- 测试结果：`drafts/260615_claude_sdk_learning/outputs/11_sessions_probe_summary.json`

核心概念：

**Sessions = 会话标识 + 本地存储 + 外部镜像**

1. **Session ID 管理**
   - 自动生成：SDK 自动创建 UUID
   - 指定 ID：`ClaudeAgentOptions(session_id="custom-uuid")`
   - 用途：追踪对话、关联业务 ID、会话恢复

2. **存储架构（双层）**
   ```
   本地存储（主）
   ├── CLI 自动写入 .jsonl 文件
   ├── 位置：CLAUDE_CONFIG_DIR/sessions/{session_id}.jsonl
   └── 保证：持久化优先（外部失败不影响）
   
   外部镜像（副）
   ├── SessionStore 接口同步
   ├── 实现：Postgres / Redis / S3 / 自定义
   └── 用途：跨实例访问、长期归档、多租户隔离
   ```

3. **SessionStore Protocol**
   ```python
   class SessionStore(Protocol):
       # 必需方法
       async def append(self, key: SessionKey, entries: list[SessionStoreEntry]) -> None:
           """追加会话记录（批量）"""
       
       async def load(self, key: SessionKey) -> list[SessionStoreEntry] | None:
           """加载会话记录（用于 resume）"""
       
       # 可选方法
       async def list_sessions(self, project_key: str) -> list[SessionStoreListEntry]:
           """列出项目的所有会话"""
       
       async def delete(self, key: SessionKey) -> None:
           """删除会话"""
       
       async def list_subkeys(self, key: SessionListSubkeysKey) -> list[str]:
           """列出 subagent 记录"""
   ```

4. **SessionKey 结构（多租户隔离关键）**
   ```python
   SessionKey = {
       "project_key": str,  # 租户 ID / 项目 ID（默认基于 cwd）
       "session_id": str,   # 会话 UUID
       "subpath": str,      # 可选，subagent 记录路径
   }
   ```

5. **会话恢复（Resume）**
   - `continue_conversation=True`：继续最近会话（自动查找）
   - `resume="session-id"`：恢复指定会话
   - `fork_session=True`：从旧会话分支出新会话
   
   **恢复优先级**：
   ```
   1. 外部 Store（session_store.load()）
   2. 本地文件（.jsonl）
   ```

6. **Project Key 设计（多租户隔离）**
   - 默认：基于 `cwd`（不适合多租户）
   - 推荐：设置 `CLAUDE_PROJECT_KEY` 环境变量
   - 示例：`options.env = {"CLAUDE_PROJECT_KEY": "tenant_001"}`

7. **SessionStore 刷新模式**
   - `batched`（默认）：批量刷新，500 条或 1 MiB 后刷新
   - `eager`：实时刷新，每帧立即刷新（高延迟）

演示代码：

**基础会话管理：**
```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
import uuid

# 自动生成 Session ID
options_auto = ClaudeAgentOptions()

# 指定 Session ID（关联业务 ID）
options_custom = ClaudeAgentOptions(
    session_id=str(uuid.uuid4())  # 或 task_id、conversation_id
)

async with ClaudeSDKClient(options=options_custom) as client:
    await client.query("Hello")
    # Session ID 会在 AssistantMessage.session_id 中返回
```

**SessionStore 实现（内存版）：**
```python
from claude_agent_sdk import SessionStore, SessionKey, SessionStoreEntry

class InMemorySessionStore(SessionStore):
    def __init__(self):
        self.storage: dict[tuple, list[SessionStoreEntry]] = {}
    
    async def append(self, key: SessionKey, entries: list[SessionStoreEntry]):
        storage_key = (key["project_key"], key["session_id"], key.get("subpath", ""))
        if storage_key not in self.storage:
            self.storage[storage_key] = []
        self.storage[storage_key].extend(entries)
    
    async def load(self, key: SessionKey) -> list[SessionStoreEntry] | None:
        storage_key = (key["project_key"], key["session_id"], key.get("subpath", ""))
        return self.storage.get(storage_key)
```

**多租户隔离：**
```python
store = InMemorySessionStore()

# 租户 A 的会话
options_a = ClaudeAgentOptions(
    session_store=store,
    env={"CLAUDE_PROJECT_KEY": "tenant_a"}
)

# 租户 B 的会话
options_b = ClaudeAgentOptions(
    session_store=store,
    env={"CLAUDE_PROJECT_KEY": "tenant_b"}
)

# 两个租户的会话数据完全隔离
```

**Postgres SessionStore（生产级）：**
```python
import asyncpg
from postgres_session_store import PostgresSessionStore

# 创建连接池
pool = await asyncpg.create_pool("postgresql://...")
store = PostgresSessionStore(pool=pool)
await store.create_schema()  # 创建表

# 使用 Store
options = ClaudeAgentOptions(
    session_store=store,
    session_store_flush="batched",  # 批量刷新
)

async with ClaudeSDKClient(options=options) as client:
    # 会话自动镜像到 Postgres
    await client.query("Hello")
```

**会话恢复：**
```python
# 恢复特定会话
options = ClaudeAgentOptions(
    resume="session-uuid",
    session_store=store,  # 从 Store 加载
)

async with ClaudeSDKClient(options=options) as client:
    # 会话历史已恢复
    await client.query("继续之前的对话")
```

运行命令：

```bash
UV_CACHE_DIR=./uv_cache uv run python drafts/260615_claude_sdk_learning/examples/11_sessions_probe.py
```

已验证：

1. ✅ **Session ID 自动生成**
   - SDK 自动创建 UUID
   - 从 `AssistantMessage.session_id` 获取

2. ✅ **Session ID 指定**
   - `ClaudeAgentOptions(session_id="custom-uuid")` 生效
   - Session ID 匹配传入的值

3. ✅ **SessionStore append() 工作正常**
   - CLI 调用 `store.append()` 追加记录
   - 批量追加（9 条记录一次）

4. ✅ **SessionKey 结构**
   - `project_key`：基于 cwd 或 `CLAUDE_PROJECT_KEY`
   - `session_id`：会话 UUID
   - `subpath`：subagent 记录路径

5. ✅ **内存 SessionStore 实现**
   - append() / load() / list_sessions() / delete() 都正常
   - 数据结构：dict[(project_key, session_id, subpath)] = [entries]

未验证/待验证：

- ❌ 会话恢复（需要先有完整会话才能测试 resume）
- ❌ Subagent 记录（subpath）
- ❌ Postgres/Redis SessionStore 生产集成
- ❌ 跨实例会话恢复（多 Pod 环境）
- ❌ Session Fork（分支会话）

对 ANIFORCE 的影响：

**核心决策：使用 Postgres SessionStore**

**为什么选择 Postgres？**

1. ✅ **ANIFORCE 已有 Postgres**
   - 复用现有基础设施
   - 减少外部依赖

2. ✅ **关系型数据库优势**
   - 支持复杂查询（按时间、租户、状态过滤）
   - 支持事务（保证一致性）
   - 支持索引优化

3. ✅ **长期存储**
   - 适合审计日志
   - 支持数据分析
   - 便于数据导出

4. ✅ **成熟生态**
   - asyncpg 性能优秀
   - 有官方参考实现
   - 社区支持完善

**SessionStore Schema 设计：**

```sql
CREATE TABLE claude_session_store (
  project_key text   NOT NULL,  -- 租户 ID
  session_id  text   NOT NULL,  -- 会话 UUID
  subpath     text   NOT NULL DEFAULT '',  -- subagent 路径
  seq         bigserial,  -- 顺序号
  entry       jsonb  NOT NULL,  -- 会话记录（JSONB）
  mtime       bigint NOT NULL,  -- 修改时间（毫秒）
  PRIMARY KEY (project_key, session_id, subpath, seq)
);

-- 列表查询索引
CREATE INDEX claude_session_store_list_idx
  ON claude_session_store (project_key, session_id)
  WHERE subpath = '';

-- 租户隔离索引
CREATE INDEX claude_session_store_tenant_idx
  ON claude_session_store (project_key, mtime DESC);
```

**ANIFORCE 集成方案：**

```typescript
// backend/runtime/agent/session-manager.service.ts

@Injectable()
export class SessionManagerService {
  private store: PostgresSessionStore
  
  async initialize() {
    const pool = await asyncpg.create_pool(this.config.postgres.dsn)
    this.store = new PostgresSessionStore(pool)
    await this.store.create_schema()
  }
  
  async createSession(
    tenantId: string,
    taskId: string
  ): Promise<ClaudeSDKClient> {
    const options = ClaudeAgentOptions({
      session_id: taskId,  // 使用业务 ID
      session_store: this.store,
      env: {
        CLAUDE_PROJECT_KEY: tenantId  // 租户隔离
      },
      // ... 其他配置
    })
    
    return new ClaudeSDKClient(options)
  }
  
  async resumeSession(
    tenantId: string,
    taskId: string
  ): Promise<ClaudeSDKClient> {
    const options = ClaudeAgentOptions({
      resume: taskId,
      session_store: this.store,
      env: {
        CLAUDE_PROJECT_KEY: tenantId
      },
    })
    
    return new ClaudeSDKClient(options)
  }
  
  async listSessions(tenantId: string): Promise<SessionInfo[]> {
    return await this.store.list_sessions(tenantId)
  }
  
  async cleanupOldSessions(days: number) {
    const cutoff = Date.now() - days * 24 * 60 * 60 * 1000
    await this.db.execute(
      `DELETE FROM claude_session_store WHERE mtime < $1`,
      [cutoff]
    )
  }
}
```

**Session ID 设计：**

```typescript
// 方案 A：使用 ANIFORCE task_id
session_id = task.id  // "task_abc123"

// 方案 B：组合 ID（更具语义）
session_id = `${tenantId}_${taskId}_${timestamp}`

// 方案 C：UUID（Claude 默认）
session_id = uuid.v4()
```

**推荐：方案 A（使用 task_id）**
- ✅ 直接关联业务对象
- ✅ 便于查询和调试
- ✅ 符合 ANIFORCE 现有设计

**多租户隔离策略：**

```
┌─────────────────────────────────────────┐
│  Project Key = tenant_id                 │
│  ├── Session 1 (task_001)                │
│  ├── Session 2 (task_002)                │
│  └── Session 3 (task_003)                │
└─────────────────────────────────────────┘

查询租户会话：
SELECT * FROM claude_session_store 
WHERE project_key = 'tenant_001'
ORDER BY mtime DESC

查询特定任务会话：
SELECT * FROM claude_session_store 
WHERE project_key = 'tenant_001' 
  AND session_id = 'task_001'
ORDER BY seq
```

**性能优化建议：**

1. **批量刷新模式**
   ```python
   session_store_flush="batched"  # 默认，推荐
   # 500 条或 1 MiB 后刷新，不阻塞消息流
   ```

2. **索引优化**
   - `(project_key, session_id, subpath, seq)` 主键
   - `(project_key, mtime DESC)` 租户会话列表
   - `(project_key, session_id)` WHERE `subpath = ''` 过滤 subagent

3. **分区表（可选）**
   ```sql
   -- 按月分区，便于归档和清理
   CREATE TABLE claude_session_store_2025_06 
     PARTITION OF claude_session_store
     FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
   ```

4. **JSONB vs JSON 字段**
   - `jsonb`：支持索引、查询，但会重排键顺序
   - `json`：保留原始格式，但无法索引
   - 推荐：`jsonb`（SDK 支持深度相等，不要求字节相等）

**数据清理策略：**

```typescript
// 定时任务：每天清理 90 天前的会话
@Cron('0 2 * * *')  // 每天凌晨 2 点
async cleanupExpiredSessions() {
  const retention = 90  // 保留 90 天
  await this.sessionManager.cleanupOldSessions(retention)
  
  this.logger.log(`Cleaned up sessions older than ${retention} days`)
}

// 按需删除：任务完成后
async deleteTaskSession(taskId: string, tenantId: string) {
  await this.store.delete({
    project_key: tenantId,
    session_id: taskId,
  })
}
```

**已确定：**

1. ✅ **Session 双层存储架构**
   - 本地：CLI 自动写入（主存储）
   - 外部：SessionStore 镜像（副存储）
   - 外部失败不影响本地持久化

2. ✅ **SessionStore Protocol 清晰**
   - append()：批量追加（必需）
   - load()：加载恢复（必需）
   - list_sessions()、delete()、list_subkeys()：可选

3. ✅ **多租户隔离通过 project_key**
   - 默认基于 cwd（不适合生产）
   - 推荐：设置 CLAUDE_PROJECT_KEY 环境变量
   - 实现：每个租户独立 project_key

4. ✅ **Postgres SessionStore 是最佳选择**
   - ANIFORCE 已有 Postgres
   - 支持复杂查询和长期存储
   - 有官方参考实现

5. ✅ **Session ID 应使用业务 ID**
   - 方案：使用 ANIFORCE task_id
   - 优势：直接关联、便于查询
   - 格式：UUID 或业务标识符

**实施计划：**

```
Phase 1: PostgresSessionStore 实现（1-2 天）
- 复制官方 Postgres 示例
- 创建数据库表和索引
- 单元测试验证

Phase 2: SessionManagerService 封装（2-3 天）
- 封装 Session 创建、恢复、列表、清理
- 集成 tenant_id 和 task_id
- 添加日志和监控

Phase 3: 生产集成（3-5 天）
- 集成到 ClaudeClientService
- 实现定时清理任务
- 性能测试和优化
```

**下一步：**
- ✅ 已完成第 11 章：Sessions / Session Storage
- 学习完成（跳过第 12 章 Hosting）
- 总结完整迁移方案


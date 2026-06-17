# ANIFORCE 关键技术结论

> 本文件记录开发/测试过程中踩坑得到的关键结论，供后续开发参考。
> 每条结论必须有实证依据，不写推测。

---

## Claude Agent SDK 调用必须做的三件事（已实证 2026-06-17）

### 问题背景

aniforce-agent 服务调用 Claude SDK 时持续报 `api_retry`，最终 `ProcessError: Command failed with exit code 1`。最小化 query 探针复现：连续 6 次 `SystemMessage(subtype=api_retry)` 后失败。

### 根因（实证）

1. **本机 Claude 配置污染**：未设置 `CLAUDE_CONFIG_DIR` 时，SDK 子进程会加载 `/root/.claude` 下的 hooks/plugins/skills。实测看到 `HookEventMessage(SessionStart)` 注入了几万字的 `superpowers` skill 内容，导致请求异常重试。
2. **env 不干净**：未显式传 `env` 参数时，SDK 继承父进程整个 `os.environ`。若父 shell 有错误的 `ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN`（如 `/root/.bashrc` 中 covs 插件写入的），会直接用错配置。
3. **配置真源不一致**：`app.config.settings` 读 `.env`，但若环境变量已存在会被覆盖（pydantic-settings 默认环境变量优先级高于 .env 文件）。

### 正确做法（对照学习手册，已验证可用）

```python
env = {
    key: value
    for key, value in os.environ.items()
    if key.startswith("ANTHROPIC_") or key.startswith("CLAUDE_")
}
env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "aniforce-agent/1.0"
env["CLAUDE_CONFIG_DIR"] = str(空配置目录)  # 必须设，隔离本机 hooks

options = ClaudeAgentOptions(
    cwd=str(sandbox),
    model="claude-sonnet-4-6",
    env=env,  # 必须显式传
    thinking={"type": "disabled"},
    effort="low",
    ...
)
```

### 成功路径的消息流格式（实证）

最小 query（prompt="你好，请回复'收到'"，无工具）产生 3 条消息：

```
[1] SystemMessage
    subtype = "init"
    data.model = "claude-sonnet-4-6"
    data.apiKeySource = "none"   # 走 AUTH_TOKEN 代理时为 none

[2] AssistantMessage
    model = "claude-sonnet-4-6"
    content = [TextBlock(text="收到")]

[3] ResultMessage
    subtype = "success"
    is_error = False
    num_turns = 1
    result = "收到"
```

### 对 aniforce-agent 代码的影响

`app/agent/runtime.py` 的 `_build_options` 当前实现有缺陷：
- 已传 `env`（✅），但**没设 `CLAUDE_CONFIG_DIR`**（❌，会被本机 hooks 污染）
- `env` 用 `**os.environ` 展开（❌，会带入污染变量）

**待修复**：
1. `env` 改为只带 `ANTHROPIC_*`/`CLAUDE_*` 前缀的变量
2. 显式设 `CLAUDE_CONFIG_DIR` 指向空目录或项目隔离目录
3. 不用 `**os.environ` 全量展开

---

## 配置污染排查记录（2026-06-17）

### 现象

`app.config.settings` 读到的 `ANTHROPIC_AUTH_TOKEN` 是 `sk-EigJ...`（rsxermu666.cn），而 `.env` 文件里写的是 `sk-hvtAU...`（copilot.huya.info）。

### 根因

`/root/.bashrc` 第 122-129 行被 covs VS Code 插件写入了：
```bash
unset ANTHROPIC_API_KEY
export ANTHROPIC_BASE_URL='https://rsxermu666.cn'
export ANTHROPIC_AUTH_TOKEN='sk-EigJN8vy...'
```

pydantic-settings 默认环境变量优先级 > .env 文件，所以 shell 里的污染变量覆盖了 .env。

### 处理

已删除 `/root/.bashrc` 中 `COVS CODEX BEGIN` 到 `END` 之间的 6 行（含注释）。

### 验证方法

```bash
env -i HOME=$HOME PATH="..." bash -c 'cd aniforce-agent && .venv/bin/python -c "from app.config.settings import get_settings; s=get_settings(); print(s.ANTHROPIC_BASE_URL)"'
```

注意：`bash -c` 启动的子 shell 会继承父进程已有环境变量，必须用 `env -i` 清空环境才能验证 .env 是否纯净。pi agent 主 shell 里的污染变量在本次会话结束前仍存在，测试脚本需用 `env -i` 启动。

---

## E2E 测试标准（确立 2026-06-17）

### 核心原则

**所有测试必须对齐生产环境真实场景，不造假数据。**

之前 `tests/manual/` 的测试是自欺欺人：测试脚本自己造 `user_id` 字段、自己造非 UUID 的 session_id，与生产环境后端实际下发格式完全不同，测试通过但生产会炸。

### 已验证必须对齐的点

1. **JWT Token**：必须用后端格式 `{"sub": user_id, "email": ..., "name": ..., "exp": ...}`（JWT RFC 7519 标准 `sub` 字段），不是 `user_id` 字段。
   - 后端 `backend/app/api/v1/auth.py` 用 `sub`
   - aniforce-agent `app/middleware/auth.py` 已修正为只读 `sub`

2. **Session ID**：必须是标准 UUID 格式（如 `8288fb55-8268-4948-b357-34a02d11b8d8`），Claude SDK 强制要求。之前测试用 `test_session_{timestamp}` 会报 `Invalid session ID. Must be a valid UUID.`

3. **Claude SDK 配置**：必须 `CLAUDE_CONFIG_DIR` 隔离 + 显式 `env` 只带 `ANTHROPIC_*`/`CLAUDE_*`（见上节）。

### 测试脚本位置

- E2E 测试手册：`aniforce-agent/tests/e2e/TEST_MANUAL.md`
- E2E 测试脚本：`aniforce-agent/tests/e2e/block{1..7}_*.py`
- 单点探针：`drafts/YYMMDD/YYMMDD_NN_描述.py`

### 文件命名规范（AGENTS.md 3.2 节）

- 中间产物/草稿/调试文件：`drafts/YYMMDD/YYMMDD_NN_描述.ext`
- 时间戳 6 位：如 `260617` = 2026-06-17
- 序号 2 位：`01, 02, 03`
- 禁止中文、空格；用 snake_case

---

## Claude SDK 消息协议参考（实证 2026-06-17）

> 探针：`drafts/260617/260617_04_message_protocol_dump.py`
> 原始 dump：`drafts/260615_claude_sdk_learning/outputs/260617_04_protocol_dump_{text,tool,stream}.json`
> 配置：copilot_sonnet（copilot.huya.info / claude-sonnet-4-6），CLAUDE_CONFIG_DIR 隔离

### query() 返回的消息类型联合

`query()` / `ClaudeSDKClient.receive_response()` 产出以下类型（`Message` 联合）：

```
UserMessage | AssistantMessage | SystemMessage | ResultMessage | StreamEvent | RateLimitEvent
```

`SystemMessage` 在运行时还会以这些子类形式出现（都 `isinstance(x, SystemMessage)` 为真）：

```
HookEventMessage | TaskStartedMessage | TaskProgressMessage |
TaskNotificationMessage | TaskUpdatedMessage | MirrorErrorMessage
```

隔离配置（`CLAUDE_CONFIG_DIR` 指向空目录）下不会出现 `HookEventMessage`。

### 消息字段表

#### SystemMessage（subtype=init）—— 会话初始化，第一条消息

| 字段 | 类型 | 说明 | 实测值 |
|---|---|---|---|
| subtype | str | 固定 `"init"` | `init` |
| data.cwd | str | SDK 工作目录 | sandbox 路径 |
| data.session_id | str | 会话 ID（UUID） | `985de587-...` |
| data.tools | list[str] | 可用工具列表 | `["Read","Glob","Grep","Write",...]` |
| data.mcp_servers | list | MCP 服务器 | `[]`（未配置时） |
| data.model | str | 模型名 | `claude-sonnet-4-6` |
| data.permissionMode | str | 权限模式 | `dontAsk` |
| data.apiKeySource | str | Key 来源 | `none`（走 AUTH_TOKEN 代理） |
| data.claude_code_version | str | CLI 版本 | `2.1.179` |
| data.skills | list[str] | 已加载 skills | `[]`（隔离时为空） |
| data.plugins | list | 已加载插件 | `[]`（隔离时为空） |
| data.agents | list[str] | 可用 agent | `["claude","Explore",...]` |

其他 SystemMessage subtype：`api_retry`（含 error_status/error/attempt/max_retries）、`thinking_tokens`（含 estimated_tokens/estimated_tokens_delta）。

#### AssistantMessage —— 模型回复

| 字段 | 类型 | 说明 | 实测值 |
|---|---|---|---|
| content | list[ContentBlock] | 内容块 | 见下表 |
| model | str | 模型名 | `claude-sonnet-4-6` |
| message_id | str | 消息 ID | `2026061712441321689504fe924c7a` |
| session_id | str | 会话 ID | UUID |
| uuid | str | 消息唯一 ID | UUID |
| stop_reason | str\|null | 停止原因 | `null`（流式时为 null） |
| usage | dict | 用量 | `{}`（非流式时为空，用量在 ResultMessage） |
| error | str\|null | 错误类型 | `null` |
| parent_tool_use_id | str\|null | 父工具调用 | `null` |

⚠️ **重要**：同一个 `message_id` 的 AssistantMessage 可能被拆成多条消息推送（ThinkingBlock 一条、ToolUseBlock 一条），开发时不能假设一个 AssistantMessage 只含一种 block。

#### UserMessage —— 工具结果回填（CLI 注入，非用户输入）

| 字段 | 类型 | 说明 | 实测值 |
|---|---|---|---|
| content | list[ContentBlock] | 含 ToolResultBlock | 见下表 |
| uuid | str | 消息唯一 ID | UUID |
| parent_tool_use_id | str\|null | 父工具调用 | `null` |
| tool_use_result | dict\|null | 结构化工具结果 | `{"type":"text","file":{...}}` |

#### ResultMessage —— 任务终态（最后一条）

| 字段 | 类型 | 说明 | 实测值 |
|---|---|---|---|
| subtype | str | 终态类型 | `success` / `error_max_turns` 等 |
| is_error | bool | 是否出错 | `false` |
| num_turns | int | 工具调用轮数 | `1`（纯文本）/ `2`（含工具） |
| duration_ms | int | 总耗时 | `5254` |
| duration_api_ms | int | API 耗时 | `7155` |
| session_id | str | 会话 ID | UUID |
| stop_reason | str\|null | 停止原因 | `end_turn` |
| total_cost_usd | float\|null | 总成本 | `0.068547` |
| result | str\|null | 最终文本结果 | 模型回复全文 |
| usage | dict | 用量统计 | `{input_tokens, output_tokens, ...}` |
| model_usage | dict\|null | 分模型用量 | `{"claude-sonnet-4-6":{inputTokens,...}}` |
| permission_denials | list | 权限拒绝 | `[]` |
| api_error_status | int\|null | API 错误码 | `null`（成功时）/ `429`/`500`（失败时） |
| errors | list\|null | 错误列表 | `null` |

⚠️ **关键**：`ResultMessage` 出现 ≠ 成功。必须以 `subtype` + `is_error` 判定。`error_max_turns` 仍会返回 ResultMessage 但 `is_error=True`。

### ContentBlock 类型表（AssistantMessage.content / UserMessage.content 内）

| 类型 | 字段 | 出现位置 | 实测 |
|---|---|---|---|
| TextBlock | `text: str` | AssistantMessage | `{"text":"你好"}` |
| ThinkingBlock | `thinking: str, signature: str` | AssistantMessage | 模型思考内容 |
| ToolUseBlock | `id: str, name: str, input: dict` | AssistantMessage | `{"id":"call_xxx","name":"Read","input":{"file_path":"target.txt"}}` |
| ToolResultBlock | `tool_use_id: str, content: str\|list\|null, is_error: bool\|null` | UserMessage | `{"tool_use_id":"call_xxx","content":"1\t...","is_error":null}` |
| ServerToolUseBlock | `id, name, input` | AssistantMessage | web_search/web_fetch（服务端工具，调用方不回填） |
| ServerToolResultBlock | `tool_use_id, content: dict` | UserMessage | 服务端工具结果 |

`ToolUseBlock.id` 与 `ToolResultBlock.tool_use_id` 关联。`ToolResultBlock.content` 的 Read 工具返回带行号文本（`"1\t内容\n2\t"`）。

### StreamEvent 子类型表（需 `include_partial_messages=True`）

`StreamEvent.event` 是原始 Anthropic API 流式事件 dict。按 `event.type` 区分：

| event.type | 含义 | 关键字段 | 实测顺序 |
|---|---|---|---|
| `message_start` | 消息开始 | `message.{id,model,role,usage}` | 1 |
| `content_block_start` | 内容块开始 | `index`, `content_block.{type,text}` | 2 |
| `content_block_delta` | 增量内容 | `index`, `delta.{type,text}`（text_delta）或 `delta.{type,partial_json}`（input_json_delta 工具参数） | 3..N |
| `content_block_stop` | 内容块结束 | `index` | N+1 |
| `message_delta` | 消息级变更 | `delta.stop_reason`, `usage.{input_tokens,output_tokens}` | N+2 |
| `message_stop` | 消息结束 | （无字段） | N+3 |

流式完成后 SDK 仍会推送一条完整的 `AssistantMessage`（汇总所有 delta）+ `ResultMessage`。

⚠️ **流式顺序观察**：实测 `AssistantMessage`（完整消息）可能插在 `content_block_delta` 和 `content_block_stop` 之间出现，不能假设它总在 `message_stop` 之后。

### 关键发现（影响适配器开发）

1. **thinking disabled 不完全生效**：`thinking={"type":"disabled"}` 在纯文本场景生效（无 ThinkingBlock），但**工具调用场景仍出现 ThinkingBlock**。适配器必须处理 ThinkingBlock，不能假设 disabled 就没有。

2. **AssistantMessage 拆分推送**：同一 `message_id` 的 AssistantMessage 会被拆成多条（ThinkingBlock 一条、ToolUseBlock 一条）。聚合用户可见文本时需按 `message_id` 合并，不能按单条 AssistantMessage。

3. **流式与完整消息共存**：`include_partial_messages=True` 时，StreamEvent（增量）和完整 AssistantMessage 都会推送。适配器二选一：要么消费 StreamEvent 推增量、忽略完整 AssistantMessage；要么忽略 StreamEvent、只推完整 AssistantMessage。不能两个都推（会重复）。

4. **apiKeySource=none**：走 `ANTHROPIC_AUTH_TOKEN` + `ANTHROPIC_BASE_URL` 代理时，`init.apiKeySource` 为 `none`，属正常，不是错误。

5. **ResultMessage 判定**：必须用 `subtype` + `is_error`，不能用「ResultMessage 是否出现」判定成功。`error_max_turns` 会返回 ResultMessage 但 `is_error=True`。

6. **Session ID 必须 UUID**：Claude SDK 强制要求 `session_id` 是标准 UUID，非 UUID（如 `test_session_001`）报 `Invalid session ID. Must be a valid UUID.`

### 协议字段权威来源

- 类型定义：`resources/claude-agent-sdk-python/src/claude_agent_sdk/types.py`
- query() 签名：`query(prompt, options=None, transport=None) -> AsyncIterator[Message]`（全关键字参数）
- 本协议表实测配置：copilot_sonnet profile + CLAUDE_CONFIG_DIR 隔离 + thinking disabled + effort low

---

## AG-UI 协议与架构设计（确立 2026-06-17）

> 决策背景：aniforce-agent 要从「自研 AG-UI 事件」迁移到「标准 AG-UI 协议 + Claude SDK」。
> 旧 `backend/app/agent_platform` 源码已删（只剩 .pyc），用的是 OpenAI SDK，不在沿用范围。
> 本节是和用户讨论后的结论，作为后续开发的设计依据。

### 三个东西的定位（必须分清）

| 名称 | 本质 | 在 ANIFORCE 的角色 |
|---|---|---|
| Claude Agent SDK | Python 库，暴露 Claude Code 的 agent loop | 底层能力：模型推理 + 工具调用 + 有状态会话 |
| AG-UI 协议 | 开放事件协议（非库） | 标准：规定 agent↔前端怎么用事件流通信 |
| CopilotKit | AG-UI 的参考实现生态（React 组件 + sdk-python/js） | 参考起点，组件可二开但核心状态层自研 |

**核心认知**：AG-UI 是协议，CopilotKit 前端组件是消费者。aniforce-agent 只需做一件事——把 Claude SDK 消息流翻译成 AG-UI 事件流，SSE 推给前端。前端用不用 CopilotKit 组件是独立决定。

### AG-UI 标准事件类型（来自 CopilotKit sdk-python protocol.py）

```
文本流:  TextMessageStart / Content / End         聊天回复
工具流:  ActionExecutionStart / Args / End / Result 前端或后端工具执行
状态流:  AgentStateMessage                        前后端共享状态同步
生命周期: RunStarted / RunFinished / RunError      一次对话的开始结束
节点流:  NodeStarted / NodeFinished               多步骤进度（可选）
```

⚠️ 注意命名：CopilotKit 标准用 `ActionExecution*`（不是旧代码里的 `TOOL_CALL_*`）。aniforce-agent 适配层必须用标准名，否则前端组件不认。

### CopilotKit 组件二开策略

- ✅ 改样式/主题/布局：组件暴露 props + className，tailwind 可覆盖
- ✅ 加自定义消息渲染（项目卡片、计划预览）：有自定义 message 组件机制
- ⚠️ 改交互逻辑（确认按钮、批量操作）：要深入 state machine，费力
- ❌ 换底层数据流：等于不用它

**结论**：fork 组件当起点改样式和消息渲染，但「AG-UI 事件→前端 state→UI 更新」这条链路自研薄状态层，不被它的 hook（useCopilotChat/useCoAgent）绑死。

### 方案 B：Agent 感知前端上下文 + 操作 UI

三个 AG-UI 机制支撑，对应广告场景：

**机制 1 共享状态（AgentStateMessage）**——Agent 感知前端上下文
```
前端状态: {
  current_project_id, current_campaign_id,
  current_view, selected_ids, filters
}
用户问"帮我优化这几个计划" → Agent 已知选中哪几个，无需追问
```

**机制 2 前端 Action（ActionExecution* 反向）**——Agent 操作 UI
```
前端注册 action: navigate_to / highlight_campaign / open_create_dialog / prefill_form
Agent 决策后调用 → 前端执行 UI 交互
```

**机制 3 HITL 确认**——高风险操作（批量改预算/删计划/授权平台）
Agent 执行前发确认请求，前端弹窗，用户确认后继续。

### MCP 工具 vs 前端 Action 的分工（关键，别混淆）

| 类型 | 执行位置 | 职责 | 例子 |
|---|---|---|---|
| MCP 工具 | aniforce-agent 侧 | 后端业务能力 | 查项目、建计划、调平台 API |
| 前端 Action | 浏览器侧 | UI 交互能力 | 跳页、高亮、弹窗、预填表单 |

两者都走 `ActionExecution*` 事件，但执行位置不同。Agent 同时拥有两类工具，自己决定用哪个。

### 对话历史归属决策

**结论：以 Claude SDK 的 session 为主，backend DB 做业务元数据 + 索引，不作为对话原文真相源。**

理由：
- Claude SDK 的 `ClaudeSDKClient` 是有状态的，自维护上下文（学习手册第 5 章验证：同 client 实例多轮 query 共享 session_id，能记住上文）
- 若 backend DB 当真相源，每轮要拼历史回 prompt，浪费 SDK 有状态能力，正是学习手册第 4 章的痛点

分工：
```
Claude SDK session.db (agent 服务本地 SQLite)
  ← 对话原文真相源（消息流、工具调用、token、cost）
  ← SDK 自管，append/load 由 SQLiteSessionStore 适配
  ← 现状方案，暂不改

backend DB (agent_task / agent_event 表)
  ← 业务元数据 + 索引
  ← task_id, user_id, session_id, title, status, rating, created_at
  ← 关键事件快照（不存全文，只存 task 级摘要）

前端
  ← 只持有 threadId（=session_id），不存历史
  ← 需要历史时调 backend API 拉，或调 agent 服务 resume
```

### 关键约束（开发时必须遵守）

- **session_id = threadId = UUID**：三方（SDK / backend / 前端）统一用一个 ID 串联
- **backend 不重放历史给 SDK**：不拼 prompt，要恢复就 resume SDK 的 session
- **agent 服务可重启**：client 实例可重建，只要 session_id 在，SDK 能从 session.db resume
- **session.db 位置**：agent 服务本地 SQLite（现状），暂不迁移 backend 统一 DB

### 落地顺序（后续开发按此推进）

1. **AG-UI 协议适配层**（aniforce-agent 侧）
   - 重写 `copilotkit_adapter.py`，Claude SDK 消息流 → 标准 AG-UI 事件
   - 对齐 CopilotKit sdk-python `protocol.py` 事件名（TextMessage* / ActionExecution* / RunStarted/Finished）
   - 翻译映射见下节

2. **MCP 工具接 backend API**
   - Agent 通过 MCP 调 backend（projects/campaigns/materials），JWT 透传
   - 工具调用通过 AG-UI `ActionExecution*` 暴露给前端

3. **前端 Action + 共享状态**（方案 B 核心）
   - 前端注册 UI action（navigate/highlight/dialog）
   - 共享状态同步 current_project_id 等

4. **对话历史对齐**
   - SDK session 为主，backend 存业务元数据
   - 依赖第一步的 session_id 贯穿

### Claude SDK 消息 → AG-UI 事件 映射表（适配层依据）

| Claude SDK 消息 | AG-UI 事件 | 说明 |
|---|---|---|
| 请求开始 | `RunStarted` | 收到前端请求即发，state=共享状态快照 |
| StreamEvent(message_start) | （内部，不发前端） | 标记消息开始 |
| StreamEvent(content_block_start, type=text) | `TextMessageStart` | messageId=AssistantMessage.message_id |
| StreamEvent(content_block_delta, text_delta) | `TextMessageContent` | content=delta.text（增量） |
| StreamEvent(content_block_stop) | `TextMessageEnd` | 闭合消息 |
| AssistantMessage(ToolUseBlock) | `ActionExecutionStart` + `ActionExecutionArgs` | actionExecutionId=tool_use.id, actionName=tool.name, args=json(input) |
| UserMessage(ToolResultBlock) | `ActionExecutionEnd` + `ActionExecutionResult` | result=content（MCP/后端工具） |
| ResultMessage(subtype=success) | `RunFinished` | state=最终状态 |
| ResultMessage(is_error=True) | `RunError` | error=errors/result |
| SystemMessage(init/api_retry/thinking_tokens) | （不发前端） | 进后端日志，避免噪音 |
| AssistantMessage(ThinkingBlock) | （默认不发前端） | 可选发 `MetaEvent` 供调试面板 |

**流式选择**：用 `include_partial_messages=True`，消费 StreamEvent 推增量，忽略完整 AssistantMessage（避免重复）。

### 适配层信息保留策略

SDK 有些字段 AG-UI 没对应事件，不丢弃，分流到两个通道：
- **后端日志**：thinking_tokens、api_retry、cost、usage、permission_denials → 写 `logs/agent.log`
- **业务 DB**：task 级摘要（用了哪些工具、耗时、cost、turn 数）→ 写 backend agent_task/agent_event
- **前端**：只发用户可见事件（文本流、工具执行、状态、生命周期）

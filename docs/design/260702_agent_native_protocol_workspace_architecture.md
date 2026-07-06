# Agent 原生协议与 Workspace 架构边界设计

## 1. 背景

前期实现中，系统对 Agents SDK 做了较多二次包装：自定义事件类型、自定义 Agent message、自定义 plan/todo/HITL 数据结构，以及 Backend 与 Agent Service 之间的多层转换。

调试 SDK 后结论很明确：对话运行、流式事件、工具调用、审批中断、Session 历史这些能力，SDK 已经提供了原生协议。ANIFORCE 当前阶段的重点不应该是继续包装 SDK，而应该是把 SDK 原生协议接进来，同时保留 Workspace + Agent 的产品能力。

核心原则：

```text
SDK 管对话与运行协议。
业务系统管 workspace、实体、权限、副作用和产品状态。
```

---

## 2. 目标

1. 尽量使用 Agents SDK 原生协议：`Runner`、`RunResult`、`RunItem`、`stream_events()`、`Session`、`RunState`。
2. 对话历史由 SDK Session 管理，不再维护自定义 `agent_messages` 协议。
3. Session 历史使用 `SQLAlchemySession`，独立 Agent DB，不和系统业务 DB 强耦合。
4. Workspace 是 Agent 执行结果的投影，渲染时复用 SaaS 页面已有业务组件。
5. Workspace 状态、选中实体、@mention、草稿等上下文通过 SDK context / dynamic instructions 注入 Agent。
6. 工具结果到 Workspace UI 的投影通过 hooks / adapter 实现，模型不直接决定 UI。
7. HITL 分为 SDK MCP approval 与业务审批，两者职责不同，不混成一套大而全协议。

---

## 3. 协议分层

### 3.1 SDK 原生协议层

由 Agents SDK 负责：

- `Agent`
- `Runner.run()` / `Runner.run_streamed()`
- `RunResult` / `RunResultStreaming`
- `result.new_items`
- `result.stream_events()`
- `MessageOutputItem`
- `ToolCallItem`
- `ToolCallOutputItem`
- `ReasoningItem`
- `MCPApprovalRequestItem`
- `RunState`
- `SQLiteSession` / `SQLAlchemySession`

这一层不要再映射成自定义的 `TEXT_MESSAGE_START`、`TOOL_CALL_START`、`PLAN_CREATED` 等内部协议。

### 3.2 ANIFORCE 业务协议层

SDK 不负责以下内容，需要业务系统维护：

- Workspace 当前页面、面板、筛选条件
- 用户选中实体
- @mention 实体
- 草稿编辑状态
- 项目 / 计划 / 素材等业务实体
- 权限、多租户、JWT
- 工具副作用记录
- Workspace 投影事件
- 业务级审批 / pending action

### 3.3 UI 组件层

Workspace 不重新实现一套 Agent 专用 UI 组件。

```text
普通 SaaS 页面组件：
  ProjectList
  MaterialGrid
  CampaignTable
  ProjectDetailPanel
  CampaignEditor

Agent Workspace：
  复用这些组件，只改变数据来源和容器逻辑。
```

组件职责：展示业务数据和处理基础交互。

容器职责：取数、路由、筛选、Agent projection、selection、context snapshot。

---

## 4. Session 历史管理

### 4.1 推荐方向

对话历史迁移到 SDK Session：

```python
from agents.memory import SQLAlchemySession

session = SQLAlchemySession.from_url(
    session_id=session_id,
    url=settings.AGENT_SESSION_DB_URL,
)

result = Runner.run_streamed(
    agent,
    user_input,
    session=session,
    context=workspace_context,
)
```

### 4.2 Agent DB 与系统 DB 分离

建议逻辑上拆成两个数据库：

```text
system db:
  users
  projects
  campaigns
  materials
  agent_sessions
  session_states
  agent_runs
  business changelog / pending actions

agent db:
  SDK SQLAlchemySession tables
  SDK 原生 conversation items
  message / tool call / reasoning / approval items
```

开发环境可以使用 SQLite：

```text
sqlite:///data/agent.db
```

生产环境不要使用本地 SQLite 文件，多实例下应使用独立 PostgreSQL database 或 schema：

```text
postgresql://agent_user:***@postgres/agent_session_db
```

这样既不污染系统业务库，也避免本地文件导致多实例历史不一致。

---

## 5. Workspace → Agent：Context 机制

Workspace 状态通过 `WorkspaceRunContext` 注入本次 run。

```python
@dataclass
class WorkspaceRunContext:
    user_id: str
    session_id: str
    run_id: str
    auth_token: str
    route: str
    active_panel: str | None
    selected_entities: list[dict]
    mentions: list[dict]
    draft_edits: dict
    business_context_summary: str
```

Dynamic instructions 负责把必要上下文暴露给模型：

```python
def workspace_instructions(ctx, agent):
    return f"""
你是 ANIFORCE 助手。

当前页面：{ctx.context.route}
当前面板：{ctx.context.active_panel}

用户选中实体：
{format_selected_entities(ctx.context.selected_entities)}

业务现场：
{ctx.context.business_context_summary}

规则：
- 当用户说“这个”“这些”“它们”时，优先指向 selected_entities 或 mentions。
- 如果指代不明确，先询问用户，不要猜。
"""
```

关键结论：

```text
ctx.context 是本地 Python 对象，LLM 默认看不到。
LLM 可见上下文必须通过 dynamic instructions、input、工具返回或 retrieval 注入。
```

---

## 6. Agent → Workspace：Hooks / Adapter 投影机制

Workspace 是 Agent 执行的投影。用户查询素材时，Workspace 应显示素材列表；Agent 不应把素材列表用文本重复一遍。

推荐机制：

```text
Agent 调用 MCP 工具
  → SDK 产生 ToolCallItem / ToolCallOutputItem
  → hooks / adapter 观察工具结果
  → 生成 WorkspaceProjection
  → Frontend Workspace 复用业务组件渲染
```

不要让模型决定 UI 怎么渲染。模型负责理解意图、选择工具、解释结果；系统负责根据工具结果生成 UI projection。

推荐实现：

```python
TOOL_PROJECTION_REGISTRY = {
    "list_materials": build_material_list_projection,
    "get_project_detail": build_project_detail_projection,
    "list_campaigns": build_campaign_list_projection,
}
```

Projection 协议保持业务语义，不直接绑定组件名：

```json
{
  "type": "workspace_projection",
  "projection": {
    "kind": "entity_list",
    "entity_type": "material",
    "entities": []
  },
  "source_tool_call_id": "call_xxx"
}
```

Frontend 决定使用哪个已有组件渲染：

```text
entity_type=material + kind=entity_list
  → MaterialGrid / MaterialTable
```

---

## 7. 选中与 @mention

### 7.1 选中实体

选中是用户主动提供上下文，不是 Agent 私自选择。

```typescript
context_snapshot = {
  route: route.fullPath,
  activePanel: currentPanel,
  selectedEntities: [
    { type: 'project', id: 'P001', name: '春节买量项目' },
    { type: 'material', id: 'M001', name: '视频素材 A' }
  ],
  draftEdits: {}
}
```

Backend 使用 `BusinessContextBuilder` 查询实体详情并生成摘要，Agent 通过 dynamic instructions 感知。

### 7.2 @mention

@mention 是比选中更明确的上下文输入。

```text
用户：对比 @material:M001 和 @material:M002 的点击率
```

Frontend 解析 mentions，随用户输入提交：

```json
{
  "input": "对比这两个素材的点击率",
  "mentions": [
    { "type": "material", "id": "M001", "name": "视频素材 A" },
    { "type": "material", "id": "M002", "name": "视频素材 B" }
  ]
}
```

指代优先级：

```text
1. mentions
2. selectedEntities
3. 当前页面 active entity
4. 最近工具结果 / 最近打开实体
5. 不确定则追问
```

---

## 8. HITL 职责边界

### 8.1 SDK MCP Approval

用于 MCP 工具调用前审批，例如危险工具：

- delete_project
- publish_campaign
- batch_update_campaign_status

SDK 流程：

```python
result = Runner.run_streamed(agent, input, context=ctx)
async for event in result.stream_events():
    pass

if result.interruptions:
    state = result.to_state()
    state.approve(result.interruptions[0])
    result = Runner.run_streamed(agent, state, context=ctx)
```

### 8.2 业务级 Pending Action

用于产品业务审批，例如：

- 批量修改 10 个 campaign 前给用户确认
- 应用 Agent 生成的投放方案
- 覆盖已有草稿

这类审批应该由系统 DB 维护：

```text
pending_actions:
  action_id
  session_id
  run_id
  action_type
  title
  payload_json
  status
  created_at
  resolved_at
```

不要把业务级审批硬塞进 SDK MCP approval，也不要把 SDK `RunState` 当成长期业务状态表。

---

## 9. system db 中 session_state 是否保留

结论：保留，但必须降级职责。

`session_state` 不再承担对话历史，也不存 SDK message/tool item。它只维护 Workspace 与业务上下文的当前状态。

建议保留字段：

```text
session_id
user_id
mode
ui_snapshot_json
linked_entities_json
summary
version
status
created_at
updated_at
```

建议迁出或拆表：

```text
pending_actions_json → pending_actions 表
changelog_json       → session_changelog / business_events 表
last_error_json      → agent_runs.error_json 或独立错误日志
```

理由：

- `ui_snapshot`、`linked_entities`、`summary` 是 Workspace → Agent 上下文构建的核心输入。
- `version` 对前端快照并发更新有价值。
- `pending_actions` 和 `changelog` 是事件 / 审批，不应塞在当前状态 JSON 里无限增长。

---

## 10. system db 中 agent_runs metadata 是否保留

结论：保留，但只作为运行索引、审计和产品状态，不保存完整对话历史。

`agent_runs` 应保留：

```text
run_id
session_id
user_id
status
input_text 或 input_summary
trace_id
idempotency_key
usage_json
error_json
started_at
completed_at
```

可选保留：

```text
pending_approval_json
run_state_json
```

但这两个字段只应该在 HITL 中断时使用，不能成为每个 run 都写的大状态字段。

更推荐中期拆表：

```text
agent_runs:
  运行索引 / 状态 / usage / error

agent_run_interruptions:
  run_id
  sdk_run_state_json
  interruptions_json
  status

pending_actions:
  业务级审批
```

理由：

- 前端需要 run 状态：queued / running / completed / failed / cancelled / requires_action。
- 运维需要按 `run_id` 查错误、耗时、usage、trace。
- 幂等需要 `idempotency_key`。
- SDK Session 只管对话 item，不替代产品级 run lifecycle。

---

## 11. 建议废弃的内容

优先废弃：

- 自定义 `agent_messages` 作为对话历史事实源
- 自定义 `EventType.TEXT_MESSAGE_START`
- 自定义 `EventType.TOOL_CALL_START`
- 自定义 plan/todo 运行协议
- 把 SDK 事件强行转换成 AG-UI 风格事件

保留但收敛：

- `AgentSession`：产品会话元数据
- `SessionState`：Workspace 当前状态
- `AgentRun`：run lifecycle / audit / usage / error

---

## 12. 改造优先级

第一阶段：协议回归原生

1. Agent Service 改用 SDK 原生 `stream_events()` 输出。
2. 对话历史切到 `SQLAlchemySession`。
3. 新增独立 `AGENT_SESSION_DB_URL`，开发用 SQLite，生产用独立 PostgreSQL。
4. Backend `agent_messages` 标记 deprecated。

第二阶段：Workspace Context

1. 定义 `WorkspaceRunContext`。
2. `context_snapshot` 补齐 `selectedEntities`、`mentions`、`draftEdits`。
3. `BusinessContextBuilder` 生成选中实体和当前页面摘要。
4. Agent 使用 dynamic instructions 注入上下文。

第三阶段：Workspace Projection

1. 建立 tool result projection registry。
2. 通过 hooks / adapter 生成 `workspace_projection`。
3. Frontend Workspace 复用项目、素材、计划等 SaaS 业务组件渲染。
4. Agent instructions 明确：已投影到 Workspace 的列表不重复文本列举。

第四阶段：HITL 与状态拆分

1. 区分 SDK MCP approval 与业务 pending action。
2. `session_states.pending_actions_json` 拆到 `pending_actions` 表。
3. `session_states.changelog_json` 拆到事件表。
4. `agent_runs.run_state_json` 只在中断恢复时使用，必要时拆 `agent_run_interruptions`。

---

## 13. 最终边界

```text
Agents SDK:
  conversation history
  run items
  tool call items
  streaming protocol
  session storage
  MCP approval / run state

ANIFORCE Backend:
  users / permissions / tenants
  projects / campaigns / materials
  workspace state
  business context builder
  run lifecycle metadata
  side effects / changelog
  business pending actions

Frontend:
  SaaS business components
  workspace container
  selection / mention input
  context snapshot collection
  workspace projection rendering
```

一句话：

```text
用 SDK 原生协议把 Agent 跑稳，用 ANIFORCE 自己的业务状态把 Workspace 做聪明。
```

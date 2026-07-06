# Agent 原生协议迁移计划

## 1. 迁移原则

本次迁移的核心目标是把 Agent Runtime 还给 Agents SDK，把 ANIFORCE 的产品状态留在业务系统内。

硬约束：

1. 当前阶段使用普通 `Agent`，不默认使用 `SandboxAgent`。
2. 不启用 Skills，不把 skills 目录存在作为启用 sandbox 的条件。
3. 协议层全面拥抱 Agents SDK 原生对象和事件，不再二次发明 message/tool/plan/todo 协议。
4. Session 历史使用 SDK `SQLAlchemySession`，存在独立 `agent.db`。
5. system db 不保存 SDK Session item，不保存完整 SDK RunState JSON，只保存产品状态和必要指针。
6. Hook / HITL 机制只预留清晰扩展口，当前不提前做复杂框架。
7. 迁移代码必须清爽、职责分明、便于阅读和后续替换。

一句话：

```text
SDK 负责 Agent 怎么跑、怎么记历史、怎么流式、怎么中断恢复。
ANIFORCE 负责用户在哪、看什么、选什么、业务发生了什么。
```

---

## 2. 当前必须修正的问题

### 2.1 当前默认会走 SandboxAgent

当前 `OpenAISDKAdapter.create_agent()` 的默认参数是：

```python
enable_skills: bool = True
```

并且判断逻辑是：

```python
has_skills = enable_skills and Path(self.skills_dir).exists()
```

`main.py` 启动时又会创建 `settings.SKILLS_DIR`，所以目录存在会让系统默认创建 `SandboxAgent`。

这和当前阶段目标冲突。

迁移要求：

```text
默认普通 Agent。
SandboxAgent 必须显式配置启用。
Skills 必须显式配置启用，且目录中存在有效 SKILL.md。
```

建议配置：

```text
ENABLE_SANDBOX_AGENT=false
ENABLE_SKILLS=false
```

短期实现：

```python
if settings.ENABLE_SANDBOX_AGENT:
    agent = SandboxAgent(...)
else:
    agent = Agent(...)
```

不要继续让 `skills_dir.exists()` 决定 Agent 类型。

### 2.2 当前有过多自定义协议

当前存在：

- `AgentTaskEvent`
- `EventType.TEXT_MESSAGE_START`
- `EventType.TEXT_MESSAGE_CONTENT`
- `EventType.TOOL_CALL_START`
- `EventType.TOOL_CALL_ARGS`
- `ExecutionPlan`
- `TodoItem`
- 自定义 HITL confirmation model
- `agent_messages` 自定义消息历史

这些和 SDK 原生协议重复。

迁移要求：

```text
不再把 SDK event 转成自定义 message/tool event。
不再新增 plan/todo runtime 协议。
不再让 agent_messages 作为对话历史事实源。
```

### 2.3 DB 职责混乱

当前 system db 中：

- `agent_messages` 像对话历史事实源
- `session_states` 混了 workspace 当前状态、pending actions、changelog、last error
- `agent_runs` 混了 run metadata 和 SDK `run_state_json`

迁移要求：

```text
SDK 原生历史和 Runtime checkpoint 进 agent.db。
system db 只放产品会话、run lifecycle、workspace state、业务事件、业务审批。
```

---

## 3. 目标架构

### 3.1 Agent Runtime

使用 SDK 原生能力：

```text
Agent
Runner.run_streamed()
RunResultStreaming
stream_events()
RunItem
SQLAlchemySession
RunState
MCPServerStreamableHttp
RunContextWrapper
ToolContext
hooks
```

当前阶段：

```text
Agent + MCP tools + SQLAlchemySession + WorkspaceRunContext
```

暂不使用：

```text
SandboxAgent
Skills
Sandbox filesystem
Sandbox shell
自定义 plan/todo runtime
```

### 3.2 数据库

```text
system db:
  产品状态和业务事实

agent.db:
  SDK 原生 Session 历史和 runtime checkpoint

realtime channel:
  token delta / reasoning delta / 临时 streaming buffer
```

### 3.3 Workspace

Workspace 是 Agent 执行结果的业务投影。

要求：

```text
Workspace 内项目、素材、计划等展示组件复用 SaaS 页面已有组件。
Agent Workspace 只是容器和数据来源，不新做一套组件。
```

---

## 4. 协议策略

### 4.1 SDK 原生事件直通

Agent Service 对外输出 SDK 原生事件，最多做传输层序列化，不做语义转换。

允许：

```json
{
  "channel": "sdk",
  "event": {
    "type": "run_item_stream_event",
    "name": "tool_called",
    "item": {}
  }
}
```

不允许：

```json
{
  "event_type": "TOOL_CALL_START",
  "payload": {}
}
```

区别：

```text
允许的 envelope 只是传输包装，不改变 SDK 语义。
不允许把 SDK event 重新映射成自定义事件体系。
```

前端应逐步直接理解 SDK 事件类型：

```text
raw_response_event
run_item_stream_event
agent_updated_stream_event

run item names:
  reasoning_item_created
  tool_called
  tool_output
  message_output_created
  mcp_approval_requested
```

### 4.2 ANIFORCE 业务事件独立表达

Workspace projection、business event、business pending action 是 ANIFORCE 业务事件，不假装成 SDK event。

允许独立通道：

```json
{
  "channel": "workspace",
  "type": "workspace_projection",
  "projection": {}
}
```

```json
{
  "channel": "business",
  "type": "business_event",
  "event": {}
}
```

```json
{
  "channel": "business",
  "type": "pending_action_required",
  "action": {}
}
```

核心边界：

```text
sdk channel = SDK 正在发生什么
workspace channel = Workspace 应展示什么
business channel = 业务事实或业务审批发生了什么
```

---

## 5. DB 职责设计

## 5.1 system db

### agent_sessions

保留，表示产品会话，不是 SDK Session。

职责：

```text
会话列表、标题、归档、用户归属。
```

字段建议：

```text
session_id
user_id
title
status
created_at
updated_at
archived_at
```

### agent_runs

保留，表示一次用户请求的产品生命周期，不保存完整 SDK 内部状态。

字段建议：

```text
run_id
session_id
user_id
status
input_text 或 input_summary
idempotency_key
trace_id
agent_checkpoint_id      # 指向 agent.db，可空
usage_summary_json       # 汇总信息
error_summary_json       # 脱敏摘要
started_at
completed_at
updated_at
```

职责：

```text
run 状态、幂等、审计入口、trace 指针、checkpoint 指针。
```

不建议继续作为长期字段：

```text
run_state_json
pending_approval_json
```

### workspace_states

由现有 `session_states` 收敛或重命名而来。

职责：

```text
Workspace 当前状态、长期 linked entities、业务摘要、刷新恢复。
```

字段建议：

```text
session_id
user_id
mode
ui_snapshot_json
linked_entities_json
workspace_summary
version
status
created_at
updated_at
```

注意：

```text
selectedEntities 默认是前端临时状态，随每次 run 的 context_snapshot 传入。
mentions 属于本次输入上下文，不作为长期 session 状态。
linked_entities 才是长期会话关注对象。
```

### pending_actions

只放业务级人工确认。

职责：

```text
应用方案、批量修改、覆盖草稿、发布确认等业务动作确认。
```

不要存 SDK MCP approval 的 RunState。

字段建议：

```text
action_id
session_id
run_id
user_id
action_type
title
payload_json
status
created_at
resolved_at
resolved_by
```

### business_events

记录业务副作用和审计事实。

职责：

```text
campaign_created
campaign_budget_updated
material_attached
project_status_changed
workspace_projection_shown
```

字段建议：

```text
event_id
session_id
run_id
user_id
event_type
entity_type
entity_id
payload_json
created_at
```

## 5.2 agent.db

agent.db 是 Agent Runtime 数据库。

开发环境：

```text
sqlite+aiosqlite:///data/agent.db
```

生产环境：

```text
postgresql+asyncpg://agent_user:***@postgres/agent_runtime_db
```

### SDK SQLAlchemySession tables

由 SDK 创建和维护。

职责：

```text
user input
assistant message
tool call
tool output
reasoning item
MCP approval item
```

### runtime_checkpoints

用于 SDK HITL / 中断恢复。

字段建议：

```text
checkpoint_id
run_id
session_id
sdk_run_state_json
interruptions_json
status
created_at
resolved_at
```

system db 只保存：

```text
agent_runs.agent_checkpoint_id = checkpoint_id
agent_runs.status = awaiting_approval
```

## 5.3 realtime channel

不进长期 DB：

```text
response.output_text.delta
response.reasoning_text.delta
typing buffer
短期断线重连 buffer
```

原则：

```text
实时层服务当前在线体验。
事实层保存可恢复、可审计的状态。
不要 event sourcing every token。
```

---

## 6. Hooks 扩展口

### 6.1 目标

Hook 机制用于观察 SDK 运行过程，承接后续 Workspace projection、审计、指标统计和安全策略。

当前阶段只留轻量接口，不提前做复杂事件总线。

### 6.2 建议结构

```python
class AgentRuntimeHooks:
    async def on_run_started(self, ctx): ...
    async def on_sdk_event(self, ctx, event): ...
    async def on_tool_result(self, ctx, item): ...
    async def on_run_completed(self, ctx, result): ...
    async def on_run_failed(self, ctx, error): ...
```

职责：

```text
on_sdk_event:
  可做日志、trace、前端透传。

on_tool_result:
  可根据 tool_name + output 生成 workspace_projection。

on_run_completed:
  可汇总 usage、更新 agent_runs。

on_run_failed:
  可记录脱敏错误、更新 agent_runs。
```

禁止：

```text
不要在 hooks 里重新定义一套 SDK 事件协议。
不要把 hooks 做成复杂 workflow engine。
```

### 6.3 Workspace Projection 扩展口

建议 registry：

```python
TOOL_PROJECTION_REGISTRY = {
    "list_materials": build_material_list_projection,
    "get_project_detail": build_project_detail_projection,
    "list_campaigns": build_campaign_list_projection,
}
```

Projection 使用业务语义，不绑定具体组件名：

```json
{
  "kind": "entity_list",
  "entity_type": "material",
  "entities": []
}
```

Frontend 决定：

```text
entity_type=material + kind=entity_list
  → MaterialGrid / MaterialTable
```

---

## 7. HITL 扩展口

### 7.1 两类 HITL 必须分开

SDK MCP approval：

```text
工具执行前审批。
需要保存 SDK RunState。
恢复后继续同一个 Agent run。
状态在 agent.db runtime_checkpoints。
```

业务 pending action：

```text
产品动作确认。
例如应用方案、批量修改、覆盖草稿、发布确认。
状态在 system db pending_actions。
批准后执行业务动作或发起新 run。
```

### 7.2 当前阶段预留

当前迁移不需要完整前端审批 UI，但代码结构要留口：

```python
class HitlCheckpointStore:
    async def save_sdk_checkpoint(run_id, state, interruptions): ...
    async def load_sdk_checkpoint(checkpoint_id): ...
    async def mark_resolved(checkpoint_id): ...
```

```python
class BusinessPendingActionService:
    async def create_action(...): ...
    async def resolve_action(...): ...
```

### 7.3 恢复流程目标

```text
SDK interruption
  → result.to_state()
  → agent.db.runtime_checkpoints
  → system db.agent_runs.status = awaiting_approval
  → user approve/reject
  → load checkpoint
  → RunState.from_json(...)
  → state.approve(...) / state.reject(...)
  → Runner.run_streamed(agent, state, context=ctx)
```

---

## 8. Workspace Context 改造

### 8.1 WorkspaceRunContext

定义本次 run 的本地上下文：

```python
@dataclass
class WorkspaceRunContext:
    user_id: str
    session_id: str
    run_id: str
    auth_token: str | None
    route: str
    active_panel: str | None
    selected_entities: list[dict]
    mentions: list[dict]
    draft_edits: dict
    business_context_summary: str
```

### 8.2 Dynamic instructions

LLM 不会自动看到 `ctx.context`，必须通过 dynamic instructions 注入必要摘要。

规则：

```text
mentions 优先于 selectedEntities。
selectedEntities 优先于 active entity。
不确定时追问。
已投影到 Workspace 的列表不重复用文本完整列举。
```

### 8.3 前端 context_snapshot

需要补齐：

```text
route
activePanel
activeProjectId
activeCampaignId
selectedEntities
mentions
draftEdits
```

---

## 9. Workspace 组件复用

原则：

```text
Workspace 里的项目、素材、计划展示，必须复用普通 SaaS 页面组件。
```

建议分层：

```text
业务展示组件：
  ProjectList
  MaterialGrid
  CampaignTable
  ProjectDetailPanel
  CampaignEditor

页面容器：
  ProjectManagementPage
  MaterialManagementPage
  AgentWorkspacePanel
```

Agent Workspace 只是换数据来源：

```text
普通页面：route/query/API list
Agent Workspace：workspace_projection/workspace state
```

---

## 10. 迁移阶段

### Phase 0：冻结新包装并切回普通 Agent

目标：先止血，避免继续扩大复杂度。

动作：

1. 新增 `ENABLE_SANDBOX_AGENT=false`、`ENABLE_SKILLS=false`。
2. 默认创建普通 `Agent`。
3. 移除 `skills_dir.exists()` 触发 SandboxAgent 的逻辑。
4. 保留 SandboxAgent 代码为显式开关分支，但当前不启用。
5. 不再新增 `EventType`、plan/todo、自定义 tool/message 协议。

验收：

```text
默认运行路径：Agent + MCP tools + SDK Session。
不会创建 SandboxAgent。
不会传 SandboxRunConfig。
```

### Phase 1：agent.db + SQLAlchemySession

目标：SDK Session 成为对话历史事实源。

动作：

1. 新增 `AGENT_RUNTIME_DB_URL`。
2. 开发使用 `sqlite+aiosqlite:///data/agent.db`。
3. 生产预留独立 PostgreSQL database/schema。
4. Agent Service 初始化 agent runtime engine。
5. 用 `SQLAlchemySession(session_id, engine=agent_engine)` 替代 `SQLiteSession(db_path=runtime/agent/sessions.db)`。
6. `agent_messages` 标记 deprecated，不再作为新 run 的事实源。

验收：

```text
同一 session_id 多轮对话由 SDK 自动加载历史。
重启 Agent Service 后仍可恢复历史。
不读取 backend agent_messages 也能继续对话。
```

### Phase 2：SDK 流式协议原生输出

目标：去掉 SDK → 自定义 EventType 的转换。

动作：

1. `stream_events()` 输出 SDK 原生事件序列化结果。
2. raw delta 实时推送，不写长期 DB。
3. run item 事件直接给前端 timeline 使用。
4. 删除或旁路 `_transform_sdk_event()` 的二次转换。
5. 前端逐步适配 SDK event type/name/item。

验收：

```text
前端能展示 reasoning delta、output delta、tool_called、tool_output、message_output_created。
后端不再生成 TEXT_MESSAGE_* / TOOL_CALL_* 事件。
```

### Phase 3：WorkspaceRunContext

目标：让 Agent 正确感知 Workspace。

动作：

1. 定义 `WorkspaceRunContext`。
2. `collectContextSnapshot()` 补齐 selected / mention / draft。
3. Backend 更新 workspace state 并构建 business context。
4. Agent 使用 dynamic instructions。
5. MCP `tool_meta_resolver`、`tool_filter` 从 context 获取 user/session/run/auth/role。

验收：

```text
选中多个素材后问“这些素材表现如何”，Agent 正确使用选中素材。
@mention 项目/素材时，Agent 优先使用 mentions。
```

### Phase 4：Hooks + Workspace Projection

目标：Agent 结果进入 Workspace，而不是长文本重复。

动作：

1. 建立轻量 `AgentRuntimeHooks`。
2. 建立 `TOOL_PROJECTION_REGISTRY`。
3. 对 list/get/metrics 工具生成 workspace projection。
4. Frontend `AgentWorkspacePanel` 复用已有业务组件渲染 projection。
5. instructions 加入“已投影不重复列举”的规则。

验收：

```text
用户查询素材，Workspace 显示素材列表，Agent 只输出摘要和洞察。
素材管理页与 Agent Workspace 使用同一套 Material 组件。
```

### Phase 5：HITL checkpoint 预留与拆分

目标：为后续审批恢复留正确口径。

动作：

1. agent.db 预留 `runtime_checkpoints`。
2. system db `agent_runs` 预留 `agent_checkpoint_id`。
3. SDK MCP approval checkpoint 放 agent.db。
4. 业务 pending action 放 system db `pending_actions`。
5. `agent_runs.run_state_json` 标记 deprecated。
6. `session_states.pending_actions_json` 迁出。

验收：

```text
SDK approval 和业务 pending action 数据职责清楚。
恢复 SDK run 不依赖 system db 保存完整 RunState。
```

### Phase 6：清理旧结构

目标：移除历史包袱。

动作：

1. 停止写 `agent_messages`。
2. 删除或归档自定义 `TEXT_MESSAGE_*` / `TOOL_CALL_*`。
3. 删除未使用 plan/todo runtime。
4. `session_states` 收敛或迁移为 `workspace_states`。
5. `changelog_json` 拆到 `business_events`。
6. `last_error_json` 迁到 `agent_runs.error_summary_json` 或日志系统。

验收：

```text
SDK 历史只有一个事实源：agent.db SQLAlchemySession。
产品状态只有一个事实源：system db。
没有双写强一致压力。
```

---

## 11. 代码结构建议

迁移后 Agent Service 建议分层：

```text
app/agent/runtime.py
  编排 Runner.run_streamed，管理 run lifecycle。

app/agent/agent_factory.py
  创建普通 Agent，集中处理 model / instructions / mcp_servers。

app/agent/session_store.py
  创建 SQLAlchemySession，管理 agent.db engine。

app/agent/context.py
  WorkspaceRunContext 和 dynamic instructions。

app/agent/hooks.py
  AgentRuntimeHooks 扩展口。

app/agent/projections.py
  tool result → workspace projection registry。

app/agent/hitl.py
  SDK checkpoint store 接口，后续实现恢复。
```

避免继续把 model、session、sandbox、event transform、projection、HITL 都塞在 `openai_adapter.py`。

---

## 12. 审核点

开工前需要确认：

1. 默认普通 `Agent`，当前不使用 `SandboxAgent`。
2. `ENABLE_SANDBOX_AGENT=false`、`ENABLE_SKILLS=false` 作为默认配置。
3. SDK 流式事件只做序列化直通，不再转换为自定义 EventType。
4. `agent.db` 独立于 system db。
5. `agent_messages` 废弃为对话历史事实源。
6. `agent_runs` 只存 product lifecycle 和 checkpoint pointer，不存完整 RunState。
7. `session_states` 收敛为 workspace state，不存 pending action/changelog/error。
8. hooks 只作为扩展口，不提前做复杂 workflow engine。
9. HITL 分 SDK checkpoint 和业务 pending action 两套状态。
10. Workspace projection 使用业务语义协议，不绑定组件名。
11. Agent Workspace 复用 SaaS 页面业务组件。

---

## 13. 不在本轮做的事

明确暂缓：

```text
SandboxAgent 默认化
Skills 体系
复杂 plan/todo runtime
自研 Session 历史协议
token 级长期事件存储
大而全 workflow engine
完整 HITL 前端审批 UI
```

这些能力等真实高频需求出现后再引入。

# Context 上下文管理学习笔记

本章重点不是官方示例里的简单用户信息，而是结合 ANIFORCE 当前的 **Agent + Workspace 工作台模式**，理解如何让 Agent 感知 SaaS 页面状态、表单草稿、选中实体和业务上下文。

---

## 1. Context 的两类含义

OpenAI Agents SDK 中的 context 至少要分成两类。

### 1.1 本地运行上下文

本地上下文通过 `RunContextWrapper[T].context` 暴露给工具、生命周期钩子、handoff 回调等 Python 代码。

```python
@dataclass
class WorkspaceRunContext:
    user_id: str
    session_id: str
    run_id: str
    ui_snapshot: dict
    session_state: dict
    business_context_summary: str
```

运行时传入：

```python
result = await Runner.run(
    agent,
    input="用户问题",
    context=workspace_context,
)
```

工具中读取：

```python
@function_tool
async def inspect_workspace_context(ctx: RunContextWrapper[WorkspaceRunContext]) -> str:
    return ctx.context.business_context_summary
```

**关键边界：**

```text
RunContextWrapper.context 是 Python 本地对象，LLM 默认看不到。
```

它适合放：
- `user_id` / `session_id` / `run_id`
- 当前 UI 快照
- backend 构建好的业务摘要
- repo / service / logger 等本地依赖
- 工具执行所需的权限、审计、运行元数据

不适合直接当作 LLM 可见上下文。

### 1.2 LLM 可见上下文

LLM 只能看到进入模型输入的内容，包括：
- `instructions` / system prompt
- `input`
- conversation history / session memory
- 工具返回结果
- 检索结果

因此，如果希望 LLM 感知当前工作台状态，必须通过以下方式注入：
- dynamic instructions
- input 注入
- 工具返回
- RAG / retrieval

---

## 2. ANIFORCE 现有上下文链路

当前项目里已经有一条比较完整的 Agent + Workspace 上下文链路。

### 2.1 前端入口

文件：`frontend/packages/main-app/src/composables/useHomeAgentSession.ts`

前端通过 `collectContextSnapshot()` 收集当前 workspace 状态：

```typescript
function collectContextSnapshot(routeContext?: AgentRouteContext): AgentContextSnapshot {
  const activePanel = routeContext?.workspace_type || new URLSearchParams(window.location.search).get('panel') || undefined
  return {
    route: route.fullPath,
    activePanel: isAgentPanel(activePanel) ? activePanel : undefined,
    activeProjectId: readRouteParam('projectId') || readRouteParam('id'),
    activeCampaignId: readRouteParam('campaignId'),
    selectedEntities: [],
    draftEdits: {},
  }
}
```

发送 Agent run 时带上：

```typescript
const contextSnapshot = collectContextSnapshot(_route)
const run = await startAgentRun(
  sessionId,
  text,
  _route?.task_type || 'conversation',
  contextSnapshot,
  signal
)
```

### 2.2 Backend 持久化入口

文件：`backend/app/api/v1/agent_routes.py`

```python
context_snapshot = body.get("context_snapshot")

if context_snapshot is not None:
    state = await _update_ui_snapshot_short_tx(
        session_id,
        user_id,
        state["version"],
        context_snapshot,
    )
```

这一步将前端状态保存到 `session_state.ui_snapshot`。

### 2.3 BusinessContextBuilder

文件：`backend/app/services/business_context_builder.py`

`BusinessContextBuilder` 从 `session_state` 读取：
- `linked_entities`
- `ui_snapshot`
- `summary`
- `changelog`
- `pending_actions`

并从 backend DB 查询项目、广告计划、素材等事实数据，构建一段紧凑文本：

```text
当前业务现场：
- 当前会话模式：project_management
- 当前项目：ANIFORCE 双十一买量项目，类型 二次元 RPG，总预算 ¥50,000，状态 draft
- 关联广告计划：2 个
  · 抖音信息流首测：Douyin，预算 ¥12,000，状态 running
  · B站预约转化测试：Bilibili，预算 ¥8,000，状态 paused
- 关联素材：1 个
- 用户当前页面：/projects/P001?panel=project_draft
- 当前面板：project_draft
```

### 2.4 Runtime 当前实现

文件：`aniforce-agent/app/agent/runtime.py`

现在 `_get_system_prompt(task)` 会把 `business_context_summary` 拼进 system prompt：

```python
business_context_summary = (task.context or {}).get("business_context_summary", "")
if not business_context_summary:
    return base_prompt
return (
    f"{base_prompt}\n\n"
    "---\n"
    "# Backend Business Context\n"
    "以下内容由 backend Session State Manager 构建，用于说明当前业务现场。"
    "backend DB 是业务事实源；如需修改业务数据，必须通过 MCP 工具调用 backend REST。\n\n"
    f"{business_context_summary}\n"
    "---"
)
```

这个方向是对的，本质上已经是在做 LLM 可见上下文注入。但它还不是 SDK 原生的 `RunContextWrapper` 动态上下文方式。

---

## 3. 推荐的 Agent + Workspace Context 模型

### 3.1 总体链路

```text
frontend collectContextSnapshot()
  → context_snapshot
  → backend session_state.ui_snapshot
  → BusinessContextBuilder.build()
  → WorkspaceRunContext
  → Agent dynamic instructions
  → Runner.run / Runner.run_streamed(context=ctx)
```

### 3.2 WorkspaceRunContext

推荐定义本次 run 的本地上下文对象：

```python
@dataclass
class WorkspaceRunContext:
    user_id: str
    session_id: str
    run_id: str
    auth_token: str | None

    ui_snapshot: dict
    session_state: dict
    business_context_summary: str

    project_repo: ProjectRepository | None = None
    campaign_repo: CampaignRepository | None = None
    material_repo: MaterialRepository | None = None
    logger: Any | None = None
```

职责：
- 承接 backend 当前 run 的本地状态
- 给工具提供业务依赖
- 给 dynamic instructions 提供 LLM 可见上下文来源
- 给审计日志提供 `run_id/session_id/user_id`

### 3.3 Dynamic Instructions

对于 ANIFORCE，建议把 dynamic instructions 作为让 LLM 感知 workspace 的主通道。

```python
def workspace_instructions(
    ctx: RunContextWrapper[WorkspaceRunContext],
    agent: Agent[WorkspaceRunContext],
) -> str:
    snapshot = ctx.context.ui_snapshot
    return f"""
你是 ANIFORCE 的 Agent + Workspace 助手。

你正在和用户共同操作一个营销 SaaS 工作台。回答必须结合当前工作台状态，不要脱离用户所在页面。

# Backend Business Context
{ctx.context.business_context_summary}

# Frontend Workspace Snapshot
- 当前路由：{snapshot.get("route")}
- 当前面板：{snapshot.get("activePanel")}
- 当前项目 ID：{snapshot.get("activeProjectId")}
- 当前 Campaign ID：{snapshot.get("activeCampaignId")}
- 当前选中实体：{json.dumps(snapshot.get("selectedEntities") or [], ensure_ascii=False)}
- 当前草稿编辑：{json.dumps(snapshot.get("draftEdits") or {}, ensure_ascii=False)}

# 行为规则
- 如果用户问“当前状态”“下一步”“缺什么”，必须优先分析当前 workspace snapshot。
- 如果草稿字段缺失，要明确指出缺失字段和建议补充项。
- 如果需要业务事实，调用工具查询，不要编造。
- 写操作、预算、上线、删除等高风险动作需要用户确认。
""".strip()
```

Agent 定义：

```python
agent = Agent[WorkspaceRunContext](
    name="ANIFORCE Workspace Agent",
    instructions=workspace_instructions,
    tools=[inspect_workspace_context, create_project, update_campaign],
    model=model,
)
```

运行时：

```python
result = Runner.run_streamed(
    agent,
    input=user_input,
    context=workspace_context,
    session=session,
)
```

---

## 4. RunContextWrapper 和 ToolContext

### 4.1 RunContextWrapper

工具可以通过 `RunContextWrapper` 读取本地上下文：

```python
@function_tool
async def inspect_workspace_context(ctx: RunContextWrapper[WorkspaceRunContext]) -> str:
    snapshot = ctx.context.ui_snapshot
    return json.dumps(
        {
            "user_id": ctx.context.user_id,
            "session_id": ctx.context.session_id,
            "run_id": ctx.context.run_id,
            "route": snapshot.get("route"),
            "active_panel": snapshot.get("activePanel"),
            "draft_edits": snapshot.get("draftEdits") or {},
            "business_context_summary": ctx.context.business_context_summary,
        },
        ensure_ascii=False,
    )
```

验证结果：工具能够正确读取：
- `user_id`
- `session_id`
- `run_id`
- `route`
- `activePanel`
- `draftEdits`
- `business_context_summary`

### 4.2 ToolContext

`ToolContext` 继承 `RunContextWrapper`，额外提供工具调用元数据：

```python
@function_tool
async def log_workspace_tool_context(
    ctx: ToolContext[WorkspaceRunContext],
    note: str,
) -> str:
    return json.dumps(
        {
            "tool_name": ctx.tool_name,
            "tool_call_id": ctx.tool_call_id,
            "tool_arguments": ctx.tool_arguments,
            "qualified_tool_name": ctx.qualified_tool_name,
            "route": ctx.context.ui_snapshot.get("route"),
            "active_panel": ctx.context.ui_snapshot.get("activePanel"),
        },
        ensure_ascii=False,
    )
```

验证结果：成功拿到：

```text
tool_name = log_workspace_tool_context
tool_call_id = call_00_...
tool_arguments = {"note": "对齐前端工具调用时间线"}
qualified_tool_name = log_workspace_tool_context
route = /projects/P001?panel=project_draft
active_panel = project_draft
```

这可以和前端已有的事件对齐：
- `tool_call.started`
- `tool_call.completed`
- timeline block
- workspace tool result
- side effect

---

## 5. 调试验证

调试脚本：

```text
notebooks/06-context/260702_01_dynamic_instructions_workspace_context_debug.py
```

### 5.1 场景1：动态 instructions 注入 Workspace 状态

输入：

```text
请基于我当前工作台状态，说明我在哪个页面、当前草稿还缺什么，以及下一步应该做什么。
```

模型正确识别：

```text
当前页面：/projects/P001?panel=project_draft
当前面板：project_draft
当前项目：ANIFORCE 双十一买量项目
草稿缺失：end_date、materials
预算：草稿 ¥5,000，与项目总预算 ¥50,000 需要校准
Campaign 策略：草稿 campaign_name 与已有 C001/C002 不完全匹配，需要确认
```

结论：dynamic instructions 能让 LLM 明确感知 workspace 状态。

### 5.2 场景2：工具读取 RunContextWrapper

模型调用 `inspect_workspace_context`，工具返回了同一份 `WorkspaceRunContext` 中的：

```text
route = /projects/P001?panel=project_draft
active_panel = project_draft
active_project_id = P001
draft_edits = {...}
business_context_summary = 当前业务现场...
```

结论：工具侧可以通过 `ctx.context` 访问本地上下文和依赖。

### 5.3 场景3：ToolContext 元数据

模型调用 `log_workspace_tool_context`，工具成功记录：

```text
tool_name
tool_call_id
tool_arguments
qualified_tool_name
route
active_panel
```

结论：ToolContext 可以用于工具调用审计、前端 timeline 对齐和问题排查。

### 5.4 场景4：严格对照组

对照组设置：
- 不使用 dynamic instructions 注入 workspace 状态
- 不在 input 注入 workspace 状态
- 不暴露任何工具

结果：

```text
请先提供你当前工作台的状态信息（如页面名称、草稿进度或截图），我才能给出针对性的说明。
```

结论：

```text
RunContextWrapper.context 不会自动进入 LLM 上下文。
```

如果想让 LLM 感知状态，必须通过 dynamic instructions、input 或工具返回。

### 5.5 场景5：run_streamed 下的 dynamic instructions

`Runner.run_streamed(..., context=ctx)` 同样生效，模型能在流式输出中正确概括当前工作台状态。

结论：动态 instructions 不只适用于 `Runner.run()`，也适用于生产更常用的 `Runner.run_streamed()`。

---

## 6. 与 Session / RunState 的边界

### 6.1 Context 不是持久状态源

`WorkspaceRunContext` 是本次 run 的运行上下文，不应该作为跨天、跨 worker、跨实例的状态源。

生产状态源仍然是：

```text
session_state.ui_snapshot
session_state.linked_entities
session_state.changelog
agent_runs.run_state_json
agent_messages
backend business DB
```

每次启动或恢复 run 时重新构建：

```text
DB / session_state
  → BusinessContextBuilder
  → WorkspaceRunContext
  → Runner.run_streamed(..., context=ctx)
```

### 6.2 Context 与 Session 的区别

| 能力 | Context | Session |
|------|---------|---------|
| 作用 | 本次 run 的本地状态和依赖 | 多轮对话历史 |
| LLM 默认可见 | ❌ 不可见 | ✅ 作为历史输入可见 |
| 生命周期 | 单次 run | 多次 run |
| 适合保存 | user_id、service、ui_snapshot、repo | user/assistant/tool 历史消息 |
| 持久化 | 需要自己从 DB 重建 | SDK session 自动保存历史 |

### 6.3 Context 与 HITL RunState 的关系

HITL 审批暂停后，`RunState` 可序列化保存。

但恢复运行时，仍应该重新构建当前 `WorkspaceRunContext`：

```python
stored = load_run_state_json(run_id)
state = await RunState.from_json(agent, stored)

workspace_context = build_workspace_context_from_db(run_id, session_id, user_id)

result = Runner.run_streamed(
    agent,
    state,
    context=workspace_context,
)
```

原因：
- `RunState` 保存 SDK 运行状态和审批状态
- `WorkspaceRunContext` 保存当前业务运行依赖和 workspace 现场
- 两者职责不同，不应混用

---

## 7. 对现有 runtime 的改造方向

当前 runtime：

```text
_get_system_prompt(task)
  → 静态拼接 business_context_summary
  → adapter.create_agent(instructions=instructions)
  → adapter.run_streamed(agent, input_text, session=session)
```

推荐升级方向：

```text
构建 WorkspaceRunContext
  → Agent[WorkspaceRunContext](instructions=workspace_instructions)
  → Runner.run_streamed(..., context=workspace_context, session=session)
```

### 7.1 runtime.py 改造点

在 `AgentRuntime.run_task()` 中：

```python
workspace_context = WorkspaceRunContext(
    user_id=task.user_id,
    session_id=task.session_id,
    run_id=task.task_id,
    ui_snapshot=(task.context or {}).get("ui_snapshot") or {},
    session_state=(task.context or {}).get("session_state") or {},
    business_context_summary=(task.context or {}).get("business_context_summary") or "",
)

agent = self.adapter.create_agent(
    name="ANIFORCE Assistant",
    instructions=workspace_instructions,
    mcp_servers=mcp_servers,
    session_id=task.session_id,
)

result = await self.adapter.run_streamed(
    agent=agent,
    input_text=user_input,
    session=session,
    context=workspace_context,
)
```

### 7.2 openai_adapter.py 改造点

让 `run_streamed()` 支持传入 context：

```python
async def run_streamed(
    self,
    agent: Agent,
    input_text: str,
    session: Optional[SQLiteSession] = None,
    context: Any | None = None,
) -> RunResult:
    result = Runner.run_streamed(
        agent,
        input=input_text,
        session=session,
        context=context,
        run_config=config,
    )
    return result
```

### 7.3 create_agent 改造点

`instructions` 参数允许是字符串，也允许是动态函数：

```python
instructions: str | Callable[[RunContextWrapper[Any], Agent[Any]], str]
```

因此 `create_agent()` 不应强制只接受字符串。

---

## 8. 生产建议

### 8.1 哪些内容放 dynamic instructions

适合放：
- 当前 route / activePanel
- 当前项目 / campaign / material 的摘要
- 当前草稿关键字段
- 缺失字段和约束
- 用户角色和权限摘要
- 当前任务模式 / intent / workspace_type

不适合放：
- 大量完整表单 JSON
- 长历史操作日志
- 大量 DB 明细
- 密钥、token、内部鉴权信息

### 8.2 哪些内容放工具

适合通过工具按需获取：
- 完整项目详情
- campaign 明细
- 素材列表
- 实时指标
- 可执行写操作
- 校验草稿合法性

### 8.3 哪些内容只放 RunContextWrapper.context

只给本地 Python 使用：
- auth token
- repo / db session / service client
- logger / tracer
- 权限对象
- 审计上下文
- 运行元数据

### 8.4 上下文体积控制

dynamic instructions 不能无限膨胀。推荐策略：

```text
核心现场摘要：放 instructions
本轮 UI 事件：放 input
详细业务数据：工具按需获取
历史长上下文：session / summary / retrieval
```

### 8.5 Workspace 状态更新策略

前端不应每个输入变动都触发 Agent run，但每次 run 时应提交最新 snapshot：

```text
用户发送消息 / 点击 Agent 操作
  → 收集最新 context_snapshot
  → backend 更新 session_state.ui_snapshot
  → 构建 business_context_summary
  → 构建 WorkspaceRunContext
  → dynamic instructions 注入 LLM
```

---

## 9. 关键结论

1. **ANIFORCE 的 Agent + Workspace 场景应该使用 RunContextWrapper，但它不是单独解决方案。**

2. **RunContextWrapper 是本地上下文容器，LLM 默认看不到。**

3. **dynamic instructions 是让 LLM 感知 workspace 状态的主通道。**

4. **BusinessContextBuilder 负责把 backend 业务事实压缩成 LLM 可读摘要。**

5. **context_snapshot / session_state 是持久状态入口和事实来源，不应被 RunContextWrapper 替代。**

6. **ToolContext 可以用于工具调用审计和前端 timeline 对齐。**

7. **生产实现应保持分层：**

```text
context_snapshot / session_state = 持久状态源
BusinessContextBuilder = 业务现场摘要
WorkspaceRunContext = 本次 run 本地上下文
Dynamic instructions = LLM 可见 workspace 上下文
RunContextWrapper / ToolContext = 工具访问上下文和元数据
Session = 多轮对话历史
RunState = HITL 暂停/恢复状态
```

8. **现有 runtime 的方向是对的，但下一步应从静态 prompt 拼接升级为 SDK 原生 dynamic instructions + context。**

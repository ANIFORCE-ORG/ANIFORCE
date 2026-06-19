# Session State Manager MVP 开发手册

日期：2026-06-19  
版本：v1.0 MVP-first  
目标：用最小可验证闭环落地 frontend → backend → agent-service 三层架构，同时保留未来扩展边界。

---

## 0. 第一性原理

用户不需要一个复杂 runtime。用户需要的是：

1. 少操作：一句话完成原本需要多个页面点击的业务动作。
2. 不出错：预算、计划、上线等写操作不能乱改。
3. 可追溯：Agent 做了什么、为什么做、改了哪些实体。
4. 可继续：长任务中断或刷新后能恢复现场。
5. 看得懂：Agent 执行结果能映射到前端 Workspace。
6. 可控：关键写操作可确认、可拒绝、可重试。

所以 MVP 只做能支撑这六件事的最小闭环。

---

## 1. MVP 架构原则

### 1.1 必须坚持

```text
frontend 不直连 agent-service
backend 是用户态 + 业务事实源入口
agent-service 不保存业务事实
Session State 只保存业务摘要和引用，不保存完整业务实体
LLM 对话历史不是业务事实源
前端是投影，不是事实源
写操作必须可追踪、可幂等
同一个 session 同一时间只能有一个 active run
```

### 1.2 暂不实现

以下能力保留设计边界，但 v1 不实现复杂版本：

```text
完整 Intent taxonomy
完整 Act DAG scheduler
完整 side_effect taxonomy
automatic compaction
event replay
BroadcastChannel 多 tab 同步
Redis 分布式锁
中心化 agent session store
完整 Skill 编排系统
完整 HITL interrupt/resume
复杂回滚系统
```

---

## 2. 当前三端状态

### 2.1 agent-service

路径：`aniforce-agent/`

当前状态：

```text
已独立运行在 8020
OpenAI Agents SDK runtime 已打通
FastMCP 位于 agent-service 内部
MCP 工具通过 backend REST 修改业务数据
SQLiteSession 保存 LLM 对话历史
session 级 sandbox 已完成
Block 1-9 已验证
```

MVP 需要新增：

```text
接收 backend 传入的 business_context_summary
把 business_context_summary 注入 Agent 指令/上下文
工具调用携带 idempotency_key / session_id / run_id
错误以统一格式返回给 backend/frontend
```

### 2.2 backend

路径：`backend/`

当前状态：

```text
已对齐 master
保留纯业务 API：projects / campaigns / materials / auth 等
旧 agent_platform / mcp / copilotkit 代码已清理
尚无 /api/v1/agent/* gateway
尚无 Session State Manager
```

MVP 需要新增：

```text
/api/v1/agent/* gateway
Session State 最小模型和存储
business_context_summary 构建
简化 side_effect 事件
session 级锁
写操作幂等支持
统一错误格式
```

### 2.3 frontend

路径：`frontend/packages/main-app/`

当前状态：

```text
临时直连 /api/agent → 8020
useHomeAgentSession 已可消费新 SSE
尚未走 backend gateway
尚未发送 context_snapshot
尚未处理 side_effect 刷新 Workspace
```

MVP 需要修改：

```text
撤销 /api/agent → 8020 代理
agent API 改为 /api/v1/agent/*
发送最小 context_snapshot
收到 side_effect 后 mark panel stale，然后重新拉 backend API
```

---

## 3. MVP 最小闭环

目标用户流程：

```text
用户：帮我创建一个 RPG 项目，预算 50000，再创建两个计划

1. frontend POST /api/v1/agent/runs
2. backend 校验用户并创建/读取 Session State
3. backend 构建 business_context_summary
4. backend 转发到 agent-service
5. agent-service 调 MCP 工具
6. MCP 工具回调 backend REST
7. backend 写 DB，记录 changelog
8. backend 发 simplified side_effect
9. frontend 收到 side_effect，刷新对应 Workspace Panel
10. 用户能看到 Agent 回复 + 右侧业务数据变化
```

这就是 MVP 是否成功的唯一标准。

---

## 4. MVP 数据模型

### 4.1 SessionState

文件：`backend/app/models/session_state.py`

```python
class SessionState(BaseModel):
    session_id: str
    user_id: str

    # v1 只分两种：general / workflow
    mode: Literal["general", "workflow"] = "general"

    # 只存引用，不存完整实体
    linked_entities: dict = Field(default_factory=dict)
    # 示例：{
    #   "project_id": "...",
    #   "campaign_ids": ["..."],
    #   "material_ids": ["..."]
    # }

    # 给 Agent 的业务摘要，可人工/规则更新
    summary: str = ""

    # 待确认动作，v1 先不做完整 interrupt/resume
    pending_actions: list[dict] = Field(default_factory=list)

    # 变更记录，用于审计和未来回滚
    changelog: list[dict] = Field(default_factory=list)

    # 前端最小状态快照
    ui_snapshot: dict | None = None

    # 工程字段
    version: int = 1
    status: Literal["active", "running", "error", "archived"] = "active"
    last_error: dict | None = None
    created_at: str
    updated_at: str
```

### 4.2 linked_entities 规则

```text
linked_entities 只保存 ID 引用：project_id / campaign_ids / material_ids
权威数据永远从 backend DB 查询
不要在 Session State 保存完整 project/campaign/material
```

### 4.3 changelog 规则

MVP changelog 字段：

```json
{
  "id": "chg_xxx",
  "run_id": "run_xxx",
  "tool_call_id": "tool_xxx",
  "entity_type": "campaign",
  "entity_id": "...",
  "action": "created",
  "field": null,
  "old_value": null,
  "new_value": {"name": "计划 A"},
  "rollbackable": false,
  "created_at": "..."
}
```

### 4.4 side_effect MVP 格式

不要一开始做复杂 taxonomy。MVP 只定义 5 类：

```text
entity_changed   业务实体变化
content_ready    素材/文案/内容生成完成
data_ready       查询或分析结果就绪
action_required  需要用户确认
run_status       run 状态变化
```

事件格式：

```json
{
  "id": "evt_xxx",
  "type": "entity_changed",
  "domain": "campaign",
  "action": "created",
  "message": "已创建广告计划 A",
  "affected_entities": [
    {"type": "campaign", "id": "...", "name": "计划 A"}
  ],
  "refresh_panels": ["context"],
  "created_at": "..."
}
```

---

## 5. context_snapshot MVP

前端只传最小必要字段：

```typescript
export interface AgentContextSnapshot {
  route: string
  activePanel?: 'context' | 'creative' | 'analysis' | 'budget' | 'audit'
  activeProjectId?: string | null
  activeCampaignId?: string | null
  selectedEntities?: Array<{
    type: 'project' | 'campaign' | 'material'
    id: string
    name?: string
  }>
  draftEdits?: Record<string, unknown>
}
```

MVP 不做：

```text
recent_ui_events
复杂本地事件流
多 tab 同步
完整草稿冲突 UI
```

但保留 `draftEdits` 字段，用于未来冲突检测。

---

## 6. business_context_summary MVP

backend 每轮 run 前构建一段文本传给 agent-service。

### 6.1 构建来源

```text
SessionState.summary
SessionState.linked_entities
backend DB 查询到的实体摘要
SessionState.pending_actions
最近 changelog 3-5 条
context_snapshot 当前页面/选中实体
```

### 6.2 示例

```text
当前业务现场：
- 当前会话模式：workflow
- 当前项目：LongTaskDemo，类型 RPG，总预算 ¥50,000，状态 active
- 关联广告计划：2 个
  · 计划 A：Meta，预算 ¥5,000，状态 draft
  · 计划 B：Google，预算 ¥3,000，状态 draft
- 最近变更：刚创建项目 LongTaskDemo
- 用户当前页面：/projects/xxx
- 当前面板：context

约束：
- 写操作必须通过 backend 工具执行
- 预算、上线、删除等高风险操作需要用户确认
- 不要把聊天历史当作业务事实，以 backend DB 为准
```

### 6.3 MVP 策略

```text
不做复杂 intent recognition
不做多 mode abstractor
只根据 linked_entities + ui_snapshot + DB 查询构建摘要
如果没有 linked_entities，就传通用说明：用户尚未绑定具体项目
```

---

## 7. 开发 Block

## Block 0：收敛手册与测试约定

### 目标

建立 MVP 开发规则，防止再次过度设计。

### 产物

```text
本文件：docs/design/260619_01_session_state_manager_mvp_dev_manual.md
```

### 验证

```bash
test -f docs/design/260619_01_session_state_manager_mvp_dev_manual.md
```

---

## Block 1：Minimal Session State

状态：已完成（2026-06-19）

### 完成记录

```text
完成：新增最小 Session State ORM 模型、SQLite Repository、version 乐观锁、changelog/ui_snapshot/error 状态更新能力。
产物：
- backend/app/models/session_state.py
- backend/app/repositories/impl/sqlite_session_state_repo.py
- backend/tests/e2e/block1_session_state.py
- backend/logs/e2e_block1_session_state.log
校验：运行 UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block1_session_state.py，10/10 通过。
风险：当前只完成单进程/单 DB 的最小状态层，尚未接入 gateway；分布式锁和复杂回滚延后。
```

### 目标

实现 Session State 最小模型、Repository、version 乐观锁。

### 文件

```text
backend/app/models/session_state.py
backend/app/repositories/session_state_repo.py
backend/tests/e2e/block1_session_state.py
```

### 必做能力

```text
create(session_id, user_id)
get(session_id, user_id)
update_with_version(state, expected_version)
append_changelog(session_id, user_id, entry)
update_ui_snapshot(session_id, user_id, snapshot)
mark_running / mark_active / mark_error
```

### 表结构

```sql
CREATE TABLE IF NOT EXISTS session_states (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'general',
  linked_entities_json TEXT NOT NULL DEFAULT '{}',
  summary TEXT NOT NULL DEFAULT '',
  pending_actions_json TEXT NOT NULL DEFAULT '[]',
  changelog_json TEXT NOT NULL DEFAULT '[]',
  ui_snapshot_json TEXT,
  version INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'active',
  last_error_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_session_states_user_id ON session_states(user_id);
```

### 验证点

```text
1. 创建 state 成功
2. 查询 state 成功
3. 跨用户查询为空
4. 更新 linked_entities 成功
5. append changelog 成功
6. update ui_snapshot 成功
7. version 正常递增
8. version 冲突返回失败
9. mark_error 记录 last_error
10. 重启后数据仍在
```

---

## Block 2：Backend Agent Gateway

状态：已完成（2026-06-19）

### 完成记录

```text
完成：新增 backend /api/v1/agent/* gateway，打通 health/sessions/runs；run 流程接入 Session State、context_snapshot、business_context_summary、session running/active/error 状态标记、SSE 透传。
产物：
- backend/app/api/v1/agent_routes.py
- backend/app/services/agent_gateway.py
- backend/app/services/business_context_builder.py
- backend/app/services/session_lock.py
- backend/app/api/v1/router.py
- backend/tests/e2e/block2_agent_gateway.py
- backend/logs/e2e_block2_agent_gateway.log
校验：运行 UV_CACHE_DIR=./uv_cache AGENT_SERVICE_URL=http://127.0.0.1:8020 uv run python tests/e2e/block2_agent_gateway.py，14/14 通过；包含真实 Agent SSE 流 runtime.started、message.*、runtime terminal event，不只是接口连通。
风险：当前为 MVP 单进程 session lock；business_context_summary 已进入 backend payload，但 agent-service 尚未正式消费该字段（Block 3 处理）。
```

### 目标

新增 `/api/v1/agent/*`，frontend 不再直连 agent-service。

### 文件

```text
backend/app/api/v1/agent_routes.py
backend/app/services/agent_gateway.py
backend/app/services/business_context_builder.py
backend/app/api/v1/router.py
backend/tests/e2e/block2_agent_gateway.py
```

### 路由

```text
GET  /api/v1/agent/health
GET  /api/v1/agent/sessions
POST /api/v1/agent/sessions
POST /api/v1/agent/runs
```

### runs 流程

```text
1. backend 校验用户
2. 读取/创建 Session State
3. 如果同 session 正在 running，返回 409
4. 保存 context_snapshot
5. 构建 business_context_summary
6. 标记 Session State = running
7. 转发到 agent-service /api/agent/runs
8. SSE 透传
9. 完成后标记 active
10. 失败后标记 error + last_error
```

### 验证点

```text
1. /api/v1/agent/health 正常
2. 创建 session 正常
3. backend 同步创建 Session State
4. list sessions 正常
5. runs 返回 SSE
6. business_context_summary 被传给 agent-service
7. 同 session 双 run 返回 409
8. agent-service 不可用时返回清晰错误
9. run 完成后 status 回到 active
10. run 失败时 status=error 且 last_error 有内容
```

---

## Block 3：agent-service Context Injection

状态：已完成（2026-06-19）

### 完成记录

```text
完成：agent-service /api/agent/runs 接收 business_context_summary/run_meta，写入 task.context；AgentRuntime 创建 Agent 时把 backend business_context_summary 拼入 system instructions。
产物：
- aniforce-agent/app/api/runs.py
- aniforce-agent/app/agent/runtime.py
- aniforce-agent/tests/e2e_openai/block10_context_injection.py
- aniforce-agent/logs/e2e_block10_context_injection.log
校验：运行 UV_CACHE_DIR=./uv_cache BACKEND_URL=http://127.0.0.1:8010 uv run python tests/e2e_openai/block10_context_injection.py，5/5 通过；marker 仅来自 context_snapshot → business_context_summary，真实 Agent 输出成功引用该 marker。
风险：当前注入为文本拼接，尚未做 token 截断/摘要压缩；复杂 compaction 延后。
```

### 目标

agent-service 接收 backend 传入的 `business_context_summary` 并注入 Agent 上下文。

### 文件

```text
aniforce-agent/app/api/runs.py
aniforce-agent/app/agent/runtime.py
aniforce-agent/tests/e2e_openai/block10_context_injection.py
```

### 请求字段

```json
{
  "prompt": "用户消息",
  "session_id": "sess_xxx",
  "task_type": "conversation",
  "business_context_summary": "当前业务现场：...",
  "run_meta": {
    "run_id": "run_xxx",
    "user_id": "user_xxx"
  }
}
```

### 注入规则

```text
business_context_summary 放在系统指令之后、用户消息之前
明确告诉 Agent：backend DB 是业务事实源
不要把 summary 当成可写状态，只能作为上下文参考
工具调用仍必须通过 MCP → backend REST
```

### 验证点

```text
1. agent-service 接收 business_context_summary
2. Agent 回复能引用 summary 中的项目名
3. 没有 summary 时仍可普通聊天
4. summary 不写入业务 DB
5. 多轮 session 历史仍正常
```

---

## Block 4：Tool Call → Backend → Simplified Side Effect

状态：已完成（2026-06-19）

### 完成记录

```text
完成：MCP 工具调用 backend 写业务数据后，backend 根据 X-Agent-Session-Id / X-Agent-Run-Id 更新 Session State linked_entities 和 changelog；gateway 在 run 结束对比 changelog 增量并发送 MVP side_effect。
产物：
- backend/app/models/side_effect.py
- backend/app/services/side_effect_service.py
- backend/app/services/session_state_mutation.py
- backend/app/api/v1/projects.py
- backend/app/api/v1/campaigns.py
- backend/app/api/v1/agent_routes.py
- aniforce-agent/app/agent/runtime.py
- aniforce-agent/app/backend_client.py
- aniforce-agent/app/mcp_server.py
- backend/tests/e2e/block4_side_effect.py
- backend/logs/e2e_block4_side_effect.log
校验：运行 UV_CACHE_DIR=./uv_cache AGENT_SERVICE_URL=http://127.0.0.1:8020 uv run python tests/e2e/block4_side_effect.py，8/8 通过；真实 Agent 触发 create_project 工具，backend 写 DB，Session State 记录 changelog/linked_entities，SSE 返回 side_effect(entity_changed/project/context)。
修复：首次验证暴露 sqlite database is locked；根因是 /api/v1/agent/runs 使用 FastAPI DB dependency 长事务跨 SSE，Agent 工具回调 backend 写 DB 时被锁。已改为 run 路由内短事务 helper，每次读写后立即 commit/release。
风险：side_effect 当前为 run 结束后基于 changelog 增量生成，尚未实现实时 event queue / replay。
```

### 目标

Agent MCP 工具调用 backend REST 后，backend 记录 changelog，并产生简化 side_effect。

### 文件

```text
backend/app/models/side_effect.py
backend/app/services/side_effect_service.py
backend/app/api/v1/projects.py
backend/app/api/v1/campaigns.py
backend/app/api/v1/materials.py
backend/tests/e2e/block4_side_effect.py
```

### MVP 设计

side_effect 不直接改前端复杂状态，只告诉前端刷新哪些 panel。

```python
class SideEffect(BaseModel):
    id: str
    type: Literal['entity_changed', 'content_ready', 'data_ready', 'action_required', 'run_status']
    domain: str | None = None
    action: str | None = None
    message: str
    affected_entities: list[dict] = []
    refresh_panels: list[str] = []
    created_at: str
```

### 事件来源

MVP 可以先不做独立 event queue，采用 run 期间收集：

```text
backend REST 写操作时 append changelog
agent gateway 在 run 结束后比较 changelog 增量
把增量转换为 side_effect 发给 frontend
```

后续再升级为 event log / replay。

### 验证点

```text
1. create_project 后 changelog 增加
2. create_project 后 side_effect type=entity_changed
3. create_campaign 后 refresh_panels 包含 context
4. create_material 后 refresh_panels 包含 creative
5. side_effect payload 不含敏感信息
6. 前端可根据 side_effect 判断刷新 panel
```

---

## Block 5：Frontend Projection MVP

状态：已完成（2026-06-19）

### 完成记录

```text
完成：前端收回直连 agent-service，改走 backend /api/v1/agent/*；新增 AgentContextSnapshot / SideEffectEvent 类型；send 时收集 context_snapshot 传给 backend；agent store 记录 side_effect 和 stale panels。
产物：
- frontend/packages/main-app/src/api/agent.ts
- frontend/packages/main-app/src/store/agent.ts
- frontend/packages/main-app/src/composables/useHomeAgentSession.ts
- frontend/packages/main-app/vite.config.ts
- backend/tests/e2e/block5_frontend_integration.py
- backend/logs/e2e_block5_frontend_integration.log
校验：运行 UV_CACHE_DIR=./uv_cache AGENT_SERVICE_URL=http://127.0.0.1:8020 uv run python tests/e2e/block5_frontend_integration.py，6/6 通过；模拟前端走 backend gateway 发送 context_snapshot，Agent 触发工具，收到 side_effect(entity_changed/project/context)。
验证：TypeScript build 通过，无类型错误；移除 vite proxy `/api/agent` 直连，所有 Agent API 走 `/api/v1/agent/*`。
风险：当前前端 side_effect 只存 store，未实际驱动 workspace panel 刷新（需要后续与业务路由/状态管理集成）；stale panel 标记为 MVP 预留接口。
```

### 目标

前端收回直连，改走 backend，并用 side_effect 驱动 Workspace 刷新。

### 文件

```text
frontend/packages/main-app/vite.config.ts
frontend/packages/main-app/src/api/agent.ts
frontend/packages/main-app/src/composables/useHomeAgentSession.ts
frontend/packages/main-app/src/store/agent.ts
frontend/packages/main-app/src/store/workspace.ts
frontend/packages/main-app/src/types/agent.ts
```

### 必做修改

```text
1. vite.config.ts 删除 /api/agent → 8020 代理
2. agent.ts 改成 /api/v1/agent/*
3. streamAgentMessage 支持 context_snapshot
4. useHomeAgentSession 收集最小 context_snapshot
5. SSE 收到 side_effect 后 mark panel stale
6. stale panel 通过 backend API 重新拉数据
```

### 不做

```text
BroadcastChannel 多 tab 同步
完整 event replay
复杂 draft conflict UI
本地直接应用 side_effect payload 修改实体
```

### 验证点

```text
1. 前端不再请求 /api/agent/*
2. 所有 agent 请求走 /api/v1/agent/*
3. 发送消息包含 context_snapshot
4. 收到 side_effect 后对应 panel stale
5. stale panel 能重新拉 backend API
6. SSE 失败时显示错误而不是静默失败
```

---

## Block 6：Safety MVP

状态：已完成（2026-06-19）

### 完成记录

```text
完成：补齐最小工程安全层；写接口支持 Idempotency-Key 返回首次结果，Agent MCP 写工具自动生成并透传幂等 key；gateway 在请求入口和运行流中拒绝同 session 并发 run；错误事件保持统一 error envelope。
产物：
- backend/app/models/idempotency.py
- backend/app/services/idempotency_service.py
- backend/app/api/v1/projects.py
- backend/app/api/v1/campaigns.py
- backend/app/api/v1/agent_routes.py
- aniforce-agent/app/mcp_server.py
- aniforce-agent/requirements.txt
- backend/tests/e2e/block6_safety.py
- backend/logs/e2e_block6_safety.log
校验：运行 UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block6_safety.py，9/9 通过；覆盖 backend health、写操作幂等、重复写不重复 changelog、agent session、同 session 并发 SESSION_BUSY、agent health 明确状态。
风险：当前幂等存储为 SQLite 表，未做 TTL/清理；简单重试仍主要依赖 MCP/SDK 层和 gateway retryable 标记，未实现完整按状态码的 backend retry policy。
```

### 目标

补齐最小工程安全：session lock、idempotency_key、统一错误、简单重试。

### 文件

```text
backend/app/services/session_lock.py
backend/app/services/idempotency_service.py
backend/app/models/errors.py
backend/tests/e2e/block6_safety.py
aniforce-agent/app/backend_client.py
aniforce-agent/app/mcp/backend_tools.py
```

### session lock

```text
同一个 session 同一时间只允许一个 active run
backend gateway 层先做进程内 asyncio.Lock
如果已有 run，返回 409 SESSION_BUSY
```

### idempotency_key

写工具必须传：

```text
idempotency_key = session_id + run_id + tool_call_id
```

backend 写操作先查 key，存在则返回第一次结果，避免重复创建。

### 统一错误

```json
{
  "error": {
    "code": "SESSION_BUSY",
    "message": "当前会话正在执行，请稍后再试",
    "retryable": true,
    "details": {}
  }
}
```

### 简单重试

只对以下错误重试：

```text
backend → agent-service 网络瞬断
agent-service → backend 503/504
模型 429
```

不重试：

```text
401/403
参数校验错误
业务规则冲突
没有 idempotency_key 的写操作
```

### 验证点

```text
1. 同 session 双 run 第二个返回 409
2. 不同 session 可并行
3. 同 idempotency_key 不重复创建
4. 503 可重试成功
5. 400 不重试
6. 错误格式统一
```

---

## Block 7：E2E Real Cases MVP

### 目标

不只测 campaign 全流程，还测真实用户入口。

### 文件

```text
backend/tests/e2e/block7_real_cases.py
```

### Case A：闲聊

```text
用户：你能帮我做什么？
期望：
- mode=general
- 不要求 project_id
- 不产生写操作
- Agent 正常回复
```

### Case B：资料查询

```text
用户：查一下我有哪些项目
期望：
- 可以调用 backend 查询工具
- 返回项目列表摘要
- 可发 data_ready side_effect 或仅文本回复
```

### Case C：素材体验

```text
用户：给我写 3 条 Facebook 广告文案
期望：
- 无 project_id 也能生成 preview 文案
- 不强制落正式素材库
- 可发 content_ready side_effect
```

### Case D：结构化任务

```text
用户：创建一个 RPG 项目，预算 50000，再创建两个计划
期望：
- mode 可切到 workflow
- 调 backend 工具创建项目/计划
- changelog 记录
- side_effect 刷新 context panel
```

### Case E：失败兜底

```text
模拟 agent-service unavailable
期望：
- backend 返回 AGENT_UNAVAILABLE
- Session State.status=error
- frontend 能展示错误
```

### Case F：幂等重试

```text
同一 tool_call_id 重放 create_campaign
期望：
- 只创建一个 campaign
- 返回同一个结果
```

---

## 8. v2 延后清单

以下能力不要混入 MVP：

```text
完整 Intent Recognition：等真实 case 积累后再做
Act DAG：先用 step_history，不做 scheduler
完整 HITL interrupt/resume：先 pending_action + confirm API
自动 compaction：先保留 summary 字段，观察 token 后再做
event replay：先断线后重拉状态
多 tab BroadcastChannel：先 409 防并发
Redis lock：单实例先用进程锁
复杂回滚：先 changelog 审计，回滚后做
完整 Skill 编排：先工具直连，Skill 作为 prompt/说明增强
```

---

## 9. 开发顺序

```text
Block 1 Minimal Session State
Block 2 Backend Agent Gateway
Block 3 agent-service Context Injection
Block 4 Tool Call → Side Effect
Block 5 Frontend Projection
Block 6 Safety MVP
Block 7 E2E Real Cases
```

每个 Block 必须：

```text
实现 → 写 e2e → 运行验证 → 更新本手册状态 → 再进入下一个 Block
```

---

## 10. 验收标准

MVP 完成时必须满足：

```text
1. frontend 不再直连 agent-service
2. backend 有 /api/v1/agent/* gateway
3. Session State 能保存 linked_entities / summary / changelog / ui_snapshot
4. Agent 能收到 business_context_summary
5. Agent 工具能通过 backend 写 DB
6. backend 能记录 changelog
7. frontend 能收到 side_effect 并刷新 Workspace
8. 同 session 并发 run 被拒绝
9. 写操作幂等
10. 闲聊 / 查询 / 生成 / 结构化任务 / 失败兜底均有 E2E 覆盖
```

---

## 11. 最终结论

MVP 的目标不是一次性完成完整 Agent Runtime，而是打通最小真实闭环：

```text
用户意图
→ frontend context_snapshot
→ backend Session State
→ business_context_summary
→ agent-service runtime
→ MCP tool
→ backend business API
→ changelog
→ simplified side_effect
→ frontend projection refresh
```

架构要能长大，但第一版代码要小。保留抽象边界，避免提前实现复杂编排。

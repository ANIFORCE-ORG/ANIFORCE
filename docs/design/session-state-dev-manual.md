# Session State Manager 设计开发手册

**性质**：开发交付物 + E2E 验证一体。改一个 Block，测一个 Block。

**原则**：真实生产场景，不造假数据；每个 Block = 一个交付物。

**依赖**：agent-service 已运行在 8020，backend 与 master 对齐运行在 8010。

---

## 总览

| Block | 交付物 | 脚本 |
|-------|--------|------|
| 1 | Backend Agent Gateway（基础代理） | `tests/e2e/block1_agent_gateway.py` |
| 2 | Session State Model + Repository（状态存储） | `tests/e2e/block2_session_state.py` |
| 3 | context_snapshot 定义与传输 | `tests/e2e/block3_context_snapshot.py` |
| 4 | Side Effect 事件系统 | `tests/e2e/block4_side_effects.py` |
| 5 | LLM 上下文 Compaction | `tests/e2e/block5_compaction.py` |
| 6 | Frontend 完整集成 | `tests/e2e/block6_frontend_integration.py` |

---

## 架构背景

### 拓扑

```text
Frontend (3010)
  ↓ POST /api/v1/agent/runs  { prompt, session_id, context_snapshot }
Backend (8010)  ← Session State Manager
  ↓ 校验 JWT → 保存 session_state → 转发到 agent-service
Agent Service (8020)
  ↓ 工具调用 → backend REST API
Backend (8010)
  ↓ 更新 DB + session_state → 发 side_effect 事件
Frontend (3010)
  ↓ SSE 流接收回复 + side_effect → 刷新 Workspace
```

### 状态分层

| 层 | 名称 | 存储 | 特点 |
|----|------|------|------|
| Layer 0 | 权威业务数据 | backend DB | 已落库事实，不可随意改 |
| Layer 1 | Session 状态 | backend（新增） | Agent 可见上下文，支持回滚 |
| Layer 2 | LLM 对话缓存 | agent-service SQLiteSession | 有上下文上限，需 compaction |
| Layer 3 | 前端临时状态 | frontend | 草稿、选中、tab |

### 关键设计

- backend 不是简单 proxy，是 Session State Manager
- agent-service 的 SQLiteSession 只存对话历史，不存业务状态
- 超出 LLM 上下文限制时通过 compaction 压缩，摘要存到 Layer 1
- Agent 工具调用后 backend 发语义事件通知前端

---

## Block 1: Backend Agent Gateway（基础代理）

### 目标
在 backend 新增 agent gateway 路由，作为 frontend 和 agent-service 之间的代理层。后端校验 JWT，转发到 agent-service，SSE 流不缓冲直接透传。

### 新增文件
```
backend/app/api/v1/agent_routes.py   ← agent 代理路由
backend/app/services/agent_gateway.py ← agent-service HTTP 客户端
backend/app/api/v1/router.py         ← 修改：注册 agent 路由
```

### 路由清单
```
GET  /api/v1/agent/health          → 返回 agent-service 健康状态
GET  /api/v1/agent/sessions        → 列出当前用户 sessions
POST /api/v1/agent/sessions        → 创建新 session
POST /api/v1/agent/sessions/{id}/archive → 归档 session
POST /api/v1/agent/runs            → 执行 Agent（SSE 透传）
```

### 验证点
- `/api/v1/agent/health` 返回 agent-service 健康信息
- 创建 session 返回 session_id
- 列出 sessions 包含刚创建的 session
- POST `/api/v1/agent/runs` 返回 SSE 流
- SSE 流中包含 `message.updated` / `message.completed` / `runtime.completed`
- 无 token 时 DEMO_MODE 返回测试用户，正式模式返回 401
- 跨用户 session 访问返回 404

### 关键实现细节

**agent_gateway.py**：
- 用 `httpx.AsyncClient` 调 agent-service `http://127.0.0.1:8020`
- `stream_run()` 方法用 `httpx.stream("POST", ...)` 透传 SSE
- 透传 JWT token 到 agent-service

**agent_routes.py**：
- 所有路由依赖 `get_current_user` 校验 JWT
- `/runs` 路由返回 `StreamingResponse`，media_type=`text/event-stream`
- 创建 session 时 title 从请求体获取，默认"新对话"

### 执行
```bash
# 先确保 agent-service 运行
cd aniforce-agent && ./start_dev.sh

# 确保 backend 运行
cd backend && DEMO_MODE=false .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8010

# 运行测试
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block1_agent_gateway.py
```

---

## Block 2: Session State Model + Repository（状态存储）

### 目标
实现 Layer 1（Session 状态存储）。定义 SessionState 数据模型，创建 DB 表，实现 Repository CRUD。这是整个架构的核心——Agent 每次执行前从这里读取业务上下文摘要，不需要从 LLM 对话历史翻找。

### 新增文件
```
backend/app/models/session_state.py          ← SessionState pydantic 模型
backend/app/repositories/session_state_repo.py ← SessionState repository
```

### SessionState Schema

```python
class SessionState:
    session_id: str                    # 会话 ID
    user_id: str                       # 归属用户
    project_id: Optional[str]          # 当前关联项目
    campaign_ids: list[str]            # 关联广告计划
    material_ids: list[str]            # 关联素材
    current_phase: Optional[str]       # 当前阶段：project_creation / analysis / budget_adjustment
    completed_phases: list[str]        # 已完成阶段
    pending_hitl: list[dict]           # 待确认操作
    changelog: list[dict]              # 变更日志（支持回滚）
    conversation_summary: Optional[str] # 对话摘要（compaction 结果）
    ui_snapshot: Optional[dict]        # 前端状态快照
    created_at: datetime
    updated_at: datetime

class ChangelogEntry:
    entity_type: str         # "campaign" / "project" / "material"
    entity_id: str
    field: str               # "budget" / "status" / "name"
    old_value: Any
    new_value: Any
    timestamp: datetime
    rollbackable: bool
```

### DB 表

```sql
CREATE TABLE IF NOT EXISTS session_states (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    project_id TEXT,
    campaign_ids TEXT,        -- JSON array
    material_ids TEXT,         -- JSON array
    current_phase TEXT,
    completed_phases TEXT,     -- JSON array
    pending_hitl TEXT,         -- JSON array
    changelog TEXT,            -- JSON array
    conversation_summary TEXT,
    ui_snapshot TEXT,          -- JSON object
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_session_states_user_id ON session_states(user_id);
```

### 验证点
- 创建 session state 成功
- 按 session_id + user_id 查询成功
- 更新 project_id 后查询正确
- 追加 changelog 条目正确
- 跨用户查询返回 None
- 更新 conversation_summary 正确

### 执行
```bash
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block2_session_state.py
```

---

## Block 3: context_snapshot 定义与传输

### 目标
定义前端 context_snapshot 协议，前端发消息时携带当前 UI 状态，backend 合并到 session_state，agent-service 注入到 prompt。

### context_snapshot 协议

```typescript
// 前端定义
interface AgentContextSnapshot {
  route: string                    // 当前路由，如 "/projects/xxx"
  workspace_tab: string            // 当前 tab：context / creative / analysis / budget / audit
  active_project_id: string | null
  active_campaign_id: string | null
  selected_entities: Array<{
    type: "project" | "campaign" | "material"
    id: string
    name: string
  }>
  draft_edits: Record<string, {    // key = entity_type:entity_id:field
    entity_type: string
    entity_id: string
    field: string
    old_value: any
    new_value: any
    saved: boolean
  }>
  recent_ui_events: Array<{        // 最近几个关键 UI 事件
    type: string
    payload: Record<string, any>
    timestamp: number
  }>
}
```

### 数据流

```text
1. 前端 agent.send() → 收集 context_snapshot
2. POST /api/v1/agent/runs { prompt, session_id, context_snapshot }
3. backend → 合并 context_snapshot 到 session_state.ui_snapshot
4. backend → 构建 session_state_summary
5. backend → 转发给 agent-service: { prompt, session_id, session_state_summary }
6. agent-service runtime → 注入到 system prompt
```

### Session State Summary（给 Agent 的上下文摘要）

```text
从 session_state 构建一段结构化文本，注入到 system prompt：

当前工作现场：
- 页面：/projects/{project_id}
- 当前 Tab：budget
- 关联项目：{project.name}（预算 {total_budget}，已消耗 {spent}）
- 关联计划：
  · {campaign1.name}（{platform}，预算 {budget}，状态 {status}）
  · ...
- 待确认操作：{pending_hitl_count} 项
- 未保存草稿：
  · campaign_budget: {campaign_name} 预算 {old_value} → {new_value}
- 对话摘要：{conversation_summary}

最近变更：
  · {changelog_entry.timestamp}: {entity} {field} {old} → {new}
```

### 验证点
- 前端发送消息带 context_snapshot
- backend 正确保存到 session_state
- session_state_summary 正确构建
- Agent prompt 中包含当前项目名和预算信息
- Agent 能引用未保存的草稿值
- 切换项目后 session_state 更新

### 执行
```bash
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block3_context_snapshot.py
```

---

## Block 4: Side Effect 事件系统

### 目标
Agent 通过 MCP 工具调用 backend REST API 修改业务数据后，backend 发语义事件给前端。前端根据事件类型刷新对应 Workspace Panel。

### 事件类型

```text
project.created        → context panel 刷新
project.updated        → context panel 刷新
campaign.created       → context panel 刷新
campaign.updated       → context panel 刷新
campaign.status_changed → context panel 刷新
material.generated     → creative panel 刷新
material.created       → creative panel 刷新
performance.loaded     → analysis panel 刷新
budget.updated         → budget panel 刷新
hitl.confirmation_required → HITL 弹窗
hitl.confirmed         → HITL 完成
act.completed          → 当前 Act 完成（可联动右侧 Timeline）
```

### 传输方式

混在 SSE 流中，作为独立的 SSE 事件：

```text
id: N
event: side_effect
data: {"type": "campaign.created", "payload": {"campaign_id": "xxx", "name": "计划A", "platform": "Meta", "budget": 5000}}
```

### 后端实现

```text
1. Agent 调 MCP 工具 → agent-service MCP server → backend REST API
2. Backend REST 处理请求 → 更新 DB（Layer 0）
3. Backend REST 处理请求 → 更新 session_state（Layer 1）
4. Backend REST 处理请求 → 追加 changelog 条目
5. Backend REST 处理请求 → 返回结果给 agent-service
6. 同时，backend 把 side_effect 事件放入该 session 的事件队列
7. SSE 流轮询事件队列，有新事件时发送给前端
```

**关键设计**：side_effect 事件不是由 agent-service 发，而是由 backend 在处理 REST 请求时产生。因为 backend 才是业务事实源，只有它知道"这个变更是 Agent 触发的还是用户手动改的"。

### 简化方案（一期）

一期不引入独立事件队列。在 Agent Gateway 的 SSE 透传完成后，backend 检查 session_state 的 changelog 增量，如果有新增 changelog 条目，在 SSE 流的末尾追加 side_effect 事件。

### 验证点
- Agent 调 create_project 后，SSE 流中包含 `side_effect: project.created`
- 事件 payload 包含正确的 project_id 和 name
- Agent 调 update_campaign_status 后，包含 `side_effect: campaign.status_changed`
- 前端收到 side_effect 后可以正确解析并决定刷新

### 执行
```bash
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block4_side_effects.py
```

---

## Block 5: LLM 上下文 Compaction

### 目标
解决 LLM 上下文窗口限制。当 SQLiteSession 对话历史超过阈值时，压缩更早的对话为摘要，存入 session_state，Agent 后续执行时从摘要 + 最近对话构建上下文。

### 机制

```text
Compaction 流程：

1. 每轮 run 完成后，检查当前 token 消耗
2. 如果 token 超过阈值（如 8000），触发 compaction：
   a. 取最近 N 轮（如 10 轮）完整对话保留在 SQLiteSession
   b. 更早的对话发送给 LLM 做摘要压缩
   c. 摘要存入 session_state.conversation_summary
   d. SQLiteSession 删除被压缩的旧消息
3. 下一轮 Agent 执行时，prompt 构成：
   system_prompt
   + session_state_summary（含 conversation_summary）
   + 近 N 轮完整对话
   + 当前用户消息
```

### 一期简化

一期不做自动 LLM 摘要压缩（成本高、延迟大），用手动规则：

```text
- 阈值：SQLiteSession 保留最近 50 条消息
- 超过后：把 50 条之前的内容做成简单文本摘要
  （"用户和 Agent 讨论了项目创建、计划配置、素材生成等话题"）
- 摘要存到 session_state.conversation_summary
- 旧的 SQLiteSession 消息删除
```

### 验证点
- 超过阈值的对话历史被压缩
- session_state.conversation_summary 有内容
- 压缩后 Agent 仍能理解之前的上下文
- SQLiteSession 消息数不超过阈值
- 服务重启后 conversation_summary 仍在

### 执行
```bash
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block5_compaction.py
```

---

## Block 6: Frontend 完整集成

### 目标
前端收回直连 agent-service，走 backend gateway。完成完整的前后端联调：前端发消息带 context_snapshot → backend 校验 + 保存状态 → agent-service 执行 → MCP 工具调 backend → side_effect 事件回前端 → Workspace 刷新。

### 前端修改清单

```text
1. vite.config.ts
   - 去掉 /api/agent → 8020 的代理
   - 所有 /api/* 统一走 backend:8010

2. src/api/agent.ts
   - createAgentSession → POST /api/v1/agent/sessions
   - listAgentSessions → GET /api/v1/agent/sessions
   - streamAgentMessage → POST /api/v1/agent/runs
   - 不需要额外的 agentJson helper（走 http client）

3. src/composables/useHomeAgentSession.ts
   - send() 方法收集 context_snapshot
   - context_snapshot 包含：route, workspace_tab, active_project_id, 
     active_campaign_id, selected_entities, draft_edits, recent_ui_events
   - SSE 事件处理新增 side_effect 分支
   - side_effect 事件触发对应 Panel 数据刷新

4. src/store/agent.ts 或新增 src/composables/useWorkspaceState.ts
   - Workspace 投影数据管理
   - 根据 side_effect 事件类型刷新对应 Panel
```

### 验证点（端到端 campaign 剧本）

```text
1. 用户登录
2. 创建新 session
3. 发送消息："创建一个 RPG 游戏项目，总预算 50000"
   → SSE 返回 Agent 回复 + side_effect: project.created
   → Workspace context panel 显示新项目

4. 追问："为这个项目创建两个计划，Meta 5000，Google 3000"
   → Agent 调 MCP 工具 → backend 创建 campaign → side_effect: campaign.created
   → Workspace context panel 显示两个计划

5. 追问："把这两个计划状态改成 active"
   → Agent 调 MCP 工具 → backend 更新状态 → side_effect: campaign.status_changed
   → Workspace 显示新状态

6. 追问："总结一下我们完成了什么"
   → Agent 从 session_state_summary 了解全局上下文
   → 返回总结
```

### 执行
```bash
# 全链路 E2E
cd backend && UV_CACHE_DIR=./uv_cache uv run python tests/e2e/block6_frontend_integration.py
```

---

## 文件清单

### 新增文件

```text
backend/app/api/v1/agent_routes.py           # Block 1
backend/app/services/agent_gateway.py         # Block 1
backend/app/models/session_state.py           # Block 2
backend/app/repositories/session_state_repo.py # Block 2

backend/tests/e2e/block1_agent_gateway.py     # Block 1 测试
backend/tests/e2e/block2_session_state.py     # Block 2 测试
backend/tests/e2e/block3_context_snapshot.py  # Block 3 测试
backend/tests/e2e/block4_side_effects.py      # Block 4 测试
backend/tests/e2e/block5_compaction.py        # Block 5 测试
backend/tests/e2e/block6_frontend_integration.py # Block 6 测试
```

### 修改文件

```text
backend/app/api/v1/router.py                  # Block 1: 注册 agent 路由
backend/app/api/v1/campaigns.py               # Block 4: 产生 side_effect 事件
backend/app/api/v1/projects.py               # Block 4: 产生 side_effect 事件
backend/app/api/v1/materials.py               # Block 4: 产生 side_effect 事件

frontend/packages/main-app/vite.config.ts     # Block 6: 收回直连代理
frontend/packages/main-app/src/api/agent.ts   # Block 6: 改走 backend
frontend/packages/main-app/src/composables/useHomeAgentSession.ts # Block 6: 加 context_snapshot
```

---

## 维护规则

1. **改一个 Block，测一个 Block**：不积压未验证的改动
2. **真实数据**：用 backend 真实 JWT，不造假
3. **日志留底**：每次测试输出到 `logs/e2e_blockN.log`
4. **失败即停**：Block N 失败不继续 N+1，先修 N
5. **手册同步**：Block 完成后更新本手册状态表
6. **先确保 agent-service 运行**：所有 Block 都依赖 agent-service 在 8020 正常运行

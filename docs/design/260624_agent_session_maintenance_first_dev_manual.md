# Agent Session 维护优先改造开发手册

**日期**：2026-06-24
**性质**：Backend / Agent-Service session 维护优先落地手册
**范围**：只处理 session 元数据归属、SDK session cache 边界、前后端 session API 迁移。暂不处理完整 run 表、消息表、HITL、workspace draft/version。

---

## 0. 目标

先把最关键的 session 维护边界做正确：

```text
Backend = 产品 session 事实源
- session_id / user_id / title / status / created_at / updated_at / archived_at
- SessionState 初始化和归属校验
- 前端 session 列表、创建、重命名、归档、详情读取入口

Agent-Service = runtime session cache
- 只维护 OpenAI Agents SDK SQLiteSession replay cache
- 按 backend 传入的 session_id 读写 SDK cache
- 不再拥有产品 session 生命周期
- 不再返回产品 session 列表作为事实源

OpenAI Agents SDK SQLiteSession = LLM 对话缓存
- 只存 LLM replay items / tool call replay items
- 可清理、可重建、可 compaction
- 丢失不影响 backend 产品 session 元数据
```

本手册解决的问题：

```text
当前 /api/v1/agent/sessions 仍由 backend 代理 agent-service。
agent-service 的 tasks.db.sessions 仍是产品 session 的实际来源。
这会导致 agent-service 重启、清理 runtime、未来横向扩容时，产品 session 生命周期不稳定。
```

第一阶段只把 session ownership 迁回 backend。不要顺手做大改：

```text
不做 agent_messages 表
不做 agent_runs 持久表
不做 RunState / HITL
不做 workspace_drafts / workspace_versions
不删除旧 task 代码
```

---

## 1. 历史记录与当前结论

### 1.1 已有设计文档

相关文档：

```text
docs/design/260623_agent_session_run_refactor_dev_manual.md
docs/design/260624_home_workspace_backend_agent_service_design.md
docs/design/260619_01_session_state_manager_mvp_dev_manual.md
docs/design/session-state-architecture.md
```

这些文档的共同结论：

```text
Backend 是产品事实源。
Agent-Service 是 LLM runtime。
SDK Session 是 LLM replay cache，不是产品 session。
SessionState 属于 backend，用于业务上下文和 workspace 投影。
```

### 1.2 当前代码状态

Backend 当前状态：

```text
backend/app/api/v1/agent_routes.py
- GET/POST/PATCH/DELETE /api/v1/agent/sessions 仍通过 AgentGatewayService 转发到 agent-service
- POST /api/v1/agent/sessions 创建成功后，会同步创建 session_states
- POST /api/v1/agent/runs 如果 session_state 不存在，会 get_or_create

backend/app/services/agent_gateway.py
- create_session/list_sessions/get_session/update_session/delete_session 都请求 agent-service /api/agent/sessions

backend/app/models/session_state.py
- 已有 session_states 表
- session_id 是主键
- user_id 有索引
- 可记录 mode / linked_entities / summary / pending_actions / changelog / ui_snapshot / status
```

Agent-Service 当前状态：

```text
aniforce-agent/app/api/sessions.py
- 暴露 /api/agent/sessions
- 直接使用 AgentTaskService 管理产品 session

aniforce-agent/app/repositories/sqlite_agent_task_repo.py
- tasks.db 中有 sessions 表
- sessions 表保存 session_id / user_id / title / status / created_at / updated_at / archived_at
- 这是当前产品 session 的实际存储

aniforce-agent/app/config/settings.py
- AGENT_SESSION_DB=runtime/agent/sessions.db
- 这是 SDK SQLiteSession cache 路径，应该保留为 runtime cache
```

### 1.3 真实 SDK 验证记录

2026-06-24 已用真实 DeepSeek ChatCompletions 基线验证：

```text
drafts/260624/01_sessions_probe.py
logs/drafts/sessions_probe_20260624_160600.jsonl
```

结论：

```text
SQLiteSession 可以按固定 session_id 持久化多轮 LLM replay items。
重新加载同一个 session_id 可恢复 SDK cache。
Session items 是 SDK replay 数据，不包含产品 title / user_id / archived 状态。
```

因此 session 维护要拆成两层：

```text
backend.agent_sessions      产品会话事实
agent-service.SQLiteSession LLM replay cache
```

---

## 2. 第一阶段交付物

### 2.1 Backend 新增产品 session 模型

新增：

```text
backend/app/models/agent_session.py
backend/app/repositories/impl/sqlite_agent_session_repo.py
backend/app/services/agent_session_service.py
```

推荐表结构：

```sql
CREATE TABLE agent_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE INDEX idx_agent_sessions_user_updated
ON agent_sessions(user_id, updated_at DESC);

CREATE INDEX idx_agent_sessions_user_status
ON agent_sessions(user_id, status);
```

状态只做两个：

```text
active
archived
```

不要把 `running/error` 放进 `agent_sessions.status`。运行态继续暂存在 `session_states.status`，后续再由 `agent_runs` 承接。

### 2.2 Backend session API 改为本地实现

保留现有路径，避免前端大改：

```text
GET    /api/v1/agent/sessions
POST   /api/v1/agent/sessions
GET    /api/v1/agent/sessions/{session_id}
PATCH  /api/v1/agent/sessions/{session_id}
DELETE /api/v1/agent/sessions/{session_id}
POST   /api/v1/agent/sessions/{session_id}/archive  # 可选兼容
```

行为：

```text
POST /sessions
- backend 生成 session_id：session_<16 hex> 或 sess_<uuid>
- 写 agent_sessions
- 同事务或同请求内创建 session_states
- 不请求 agent-service

GET /sessions
- 从 agent_sessions 按 user_id 查询
- 默认只返回 active
- 按 updated_at DESC 排序
- 不请求 agent-service

GET /sessions/{session_id}
- 校验 user_id 归属
- 返回 session 元数据 + session_state 摘要
- 第一阶段 messages 可返回 []，不要从 agent-service event replay 重建

PATCH /sessions/{session_id}
- 只支持 title
- title trim，限制 80 字
- 校验 user_id + active

DELETE /sessions/{session_id}
- 软归档：status=archived, archived_at=now
- 不删除 SDK SQLiteSession cache
```

### 2.3 AgentGatewayService 瘦身

第一阶段后，backend 不再需要通过 gateway 管理 session：

```text
AgentGatewayService 保留：
- health
- stream_run
- cancel_task  # 旧兼容，后续再移除

AgentGatewayService 删除或标记 deprecated：
- create_session
- list_sessions
- get_session
- update_session
- delete_session
```

`agent_routes.py` 中 session endpoints 不再依赖 `AgentGatewayService`。

### 2.4 Agent-Service session API 降级

agent-service 的 `/api/agent/sessions` 不再作为产品事实源。

第一阶段建议保留接口但标记 deprecated，避免旧前端或测试直接崩：

```text
GET /api/agent/sessions
- 返回 410 Gone 或空列表 + deprecation warning

POST /api/agent/sessions
- 返回 410 Gone，提示使用 backend /api/v1/agent/sessions

GET /api/agent/sessions/{session_id}
- 不再返回产品 messages
- 可选只返回 runtime cache 诊断信息，但默认不开放给前端
```

如果担心兼容测试，短期可保留旧接口，但必须在文档和代码注释明确：

```text
仅 deprecated 兼容，不作为产品数据源。
新代码禁止调用。
```

### 2.5 Agent-Service SDK Session Factory

确保 run 使用 backend 传入的 `session_id` 创建 SDK SQLiteSession：

```text
aniforce-agent/app/agent/session_factory.py
```

建议接口：

```python
def create_sdk_session(session_id: str) -> SQLiteSession:
    return SQLiteSession(
        session_id=session_id,
        db_path=settings.AGENT_SESSION_DB,
    )
```

约束：

```text
session_id 必须由 backend 生成或校验。
agent-service 不生成产品 session_id。
AGENT_SESSION_DB 只作为 runtime cache。
清理 runtime/agent/sessions.db 不影响 backend agent_sessions。
```

---

## 3. 执行顺序

### Block S0：基线确认

目标：确认当前行为，作为迁移前对照。

检查点：

```text
1. backend /api/v1/agent/sessions 当前会请求 agent-service
2. agent-service tasks.db.sessions 当前有产品 session
3. backend 创建 session 后会同步创建 session_states
4. run 使用传入 session_id 能写 SDK SQLiteSession cache
```

建议脚本：

```text
backend/tests/e2e/session_refactor/block_s0_current_baseline.py
```

验收：

```text
Block S0: passed 4/4
```

### Block S1：Backend agent_sessions 落库

目标：backend 拥有产品 session 元数据。

修改：

```text
backend/app/models/agent_session.py
backend/app/models/__init__.py
backend/app/repositories/impl/sqlite_agent_session_repo.py
backend/app/services/agent_session_service.py
```

验证点：

```text
1. create session 写 agent_sessions
2. list session 按 user_id 隔离
3. rename session 更新 title/updated_at
4. archive session 软删除
5. archived 默认不出现在 list
6. 非归属用户无法读取/修改/归档
```

建议脚本：

```text
backend/tests/e2e/session_refactor/block_s1_backend_agent_sessions.py
```

验收：

```text
Block S1: passed 6/6
```

### Block S2：Backend session API 切本地

目标：`/api/v1/agent/sessions` 不再依赖 agent-service。

修改：

```text
backend/app/api/v1/agent_routes.py
backend/app/services/agent_gateway.py
```

验证点：

```text
1. 停止 agent-service 后，backend /api/v1/agent/sessions 仍可 create/list/get/rename/archive
2. create session 同步创建 session_states
3. get session 返回 session + session_state，messages 第一阶段为 []
4. agent-service 不可用时，只有 run/health 受影响，session API 不受影响
```

建议脚本：

```text
backend/tests/e2e/session_refactor/block_s2_backend_session_api_local.py
```

验收：

```text
Block S2: passed 4/4
```

### Block S3：Run 只消费 backend session_id

目标：run 前必须确认产品 session 存在且归属正确。

修改：

```text
backend/app/api/v1/agent_routes.py
backend/app/services/agent_session_service.py
```

行为：

```text
POST /api/v1/agent/runs
- 如果 session_id 缺失：可选自动创建 backend session
- 如果 session_id 存在：必须校验 user_id + active
- session archived：返回 409 SESSION_ARCHIVED
- session 不存在或非归属：返回 404 SESSION_NOT_FOUND
- run 成功启动后 touch agent_sessions.updated_at
```

验证点：

```text
1. active session 可 run
2. archived session 拒绝 run
3. 其他用户 session 拒绝 run
4. run 后 agent_sessions.updated_at 更新
5. agent_payload 传给 agent-service 的 session_id 等于 backend session_id
```

建议脚本：

```text
backend/tests/e2e/session_refactor/block_s3_run_uses_backend_session.py
```

验收：

```text
Block S3: passed 5/5
```

### Block S4：Agent-Service 只保留 SDK session cache

目标：agent-service 不再维护产品 session 生命周期。

修改：

```text
aniforce-agent/app/api/sessions.py
aniforce-agent/app/agent/session_factory.py
aniforce-agent/app/agent/runtime.py 或 openai_adapter.py
```

验证点：

```text
1. agent-service run 使用传入 session_id 创建 SQLiteSession
2. 同一个 session_id 连续两轮有 LLM replay 记忆
3. 删除 runtime/agent/sessions.db 后，backend session 列表不丢
4. agent-service /api/agent/sessions 标记 deprecated 或不再被 backend 调用
```

建议脚本：

```text
aniforce-agent/tests/e2e_openai_refactor/block_s4_sdk_session_cache_only.py
```

验收：

```text
Block S4: passed 4/4
```

### Block S5：Frontend session 入口确认

目标：前端只调用 backend session API。

修改：

```text
frontend/packages/main-app/src/**
```

验证点：

```text
1. 创建 session 请求 /api/v1/agent/sessions
2. 列表读取 /api/v1/agent/sessions
3. 点击 session 后读取 /api/v1/agent/sessions/{session_id}
4. 重命名/归档走 backend
5. 前端没有直接请求 /api/agent/sessions 或 8020
```

建议脚本：

```text
backend/tests/e2e/session_refactor/block_s5_frontend_session_contract.py
```

验收：

```text
Block S5: passed 5/5
```

---

## 4. API 契约

### 4.1 Create Session

```http
POST /api/v1/agent/sessions
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "新对话"
}
```

响应：

```json
{
  "session_id": "session_abc123",
  "title": "新对话",
  "status": "active",
  "created_at": "2026-06-24T16:30:00Z",
  "updated_at": "2026-06-24T16:30:00Z",
  "archived_at": null
}
```

### 4.2 List Sessions

```http
GET /api/v1/agent/sessions?include_archived=false&limit=50&offset=0
```

响应：

```json
[
  {
    "session_id": "session_abc123",
    "title": "新对话",
    "status": "active",
    "created_at": "2026-06-24T16:30:00Z",
    "updated_at": "2026-06-24T16:35:00Z",
    "archived_at": null
  }
]
```

### 4.3 Get Session

```http
GET /api/v1/agent/sessions/{session_id}
```

第一阶段响应：

```json
{
  "session_id": "session_abc123",
  "title": "新对话",
  "status": "active",
  "created_at": "2026-06-24T16:30:00Z",
  "updated_at": "2026-06-24T16:35:00Z",
  "archived_at": null,
  "state": {
    "mode": "general",
    "linked_entities": {},
    "summary": "",
    "status": "active",
    "version": 1
  },
  "messages": []
}
```

`messages` 第一阶段返回空数组，后续 `agent_messages` 落地后再替换。

### 4.4 Rename Session

```http
PATCH /api/v1/agent/sessions/{session_id}
Content-Type: application/json

{
  "title": "投放计划讨论"
}
```

### 4.5 Archive Session

```http
DELETE /api/v1/agent/sessions/{session_id}
```

响应：

```json
{
  "status": "archived",
  "session_id": "session_abc123"
}
```

---

## 5. 数据一致性规则

### 5.1 session_id 来源

```text
产品 session_id 只能由 backend 生成或校验。
frontend 不生成最终 session_id。
agent-service 不生成产品 session_id。
```

### 5.2 user_id 归属

所有 backend 查询必须带：

```text
WHERE session_id = ? AND user_id = ?
```

禁止只按 `session_id` 修改产品 session。

### 5.3 SessionState 创建

`agent_sessions` 创建后必须保证存在 `session_states`：

```text
create agent_session
create session_state(session_id, user_id)
commit
```

如果 `session_states` 已存在，create session 不应覆盖它。

### 5.4 SDK cache 清理

清理以下文件不能影响产品 session 列表：

```text
aniforce-agent/runtime/agent/sessions.db
aniforce-agent/runtime/agent/tasks.db
```

第一阶段后，产品 session 只依赖：

```text
backend/data/sqlite/animagus.db
```

### 5.5 archived session

归档只影响产品层：

```text
agent_sessions.status = archived
agent_sessions.archived_at = now
```

不要主动删除 SDK SQLiteSession items。runtime cache 可由独立清理任务处理。

---

## 6. 最小校验清单

每个 Block 完成后至少执行：

```bash
UV_CACHE_DIR=./uv_cache uv run python -m py_compile backend/app/api/v1/agent_routes.py
UV_CACHE_DIR=./uv_cache uv run python -m py_compile backend/app/services/agent_gateway.py
UV_CACHE_DIR=./uv_cache uv run python -m py_compile aniforce-agent/app/api/sessions.py
```

涉及新增 backend 文件时补充：

```bash
UV_CACHE_DIR=./uv_cache uv run python -m py_compile \
  backend/app/models/agent_session.py \
  backend/app/repositories/impl/sqlite_agent_session_repo.py \
  backend/app/services/agent_session_service.py
```

涉及前端时：

```bash
cd frontend/packages/main-app
npm_config_cache=./npm_cache npm run build
```

端到端验收建议：

```bash
UV_CACHE_DIR=./uv_cache uv run python backend/tests/e2e/session_refactor/block_s1_backend_agent_sessions.py
UV_CACHE_DIR=./uv_cache uv run python backend/tests/e2e/session_refactor/block_s2_backend_session_api_local.py
UV_CACHE_DIR=./uv_cache uv run python backend/tests/e2e/session_refactor/block_s3_run_uses_backend_session.py
UV_CACHE_DIR=./uv_cache uv run python aniforce-agent/tests/e2e_openai_refactor/block_s4_sdk_session_cache_only.py
UV_CACHE_DIR=./uv_cache uv run python backend/tests/e2e/session_refactor/block_s5_frontend_session_contract.py
```

---

## 7. 风险与处理

### 风险 1：旧前端仍直连 agent-service sessions

处理：

```text
先 rg 检查 frontend 中 /api/agent/sessions、8020、AGENT_SERVICE_URL。
第一阶段结束标准要求前端只调 /api/v1/agent/sessions。
```

### 风险 2：backend session API 切本地后旧 E2E 失败

处理：

```text
更新 E2E 预期：停止 agent-service 时 session API 应该仍然可用。
原本“backend 创建 session 会请求 agent-service”的断言必须删除。
```

### 风险 3：run 自动创建 session 导致孤儿状态

处理：

```text
POST /runs 如果允许缺省 session_id，必须通过 AgentSessionService 创建完整 agent_session + session_state。
不要只创建 session_state。
```

### 风险 4：agent-service tasks.db.sessions 旧数据迁移

处理：

第一阶段不做自动迁移。原因：

```text
当前是开发期数据。
自动迁移会增加复杂度。
真正要保的是未来产品 session 事实源。
```

如必须保留旧数据，单独写一次性脚本：

```text
drafts/260624/migrate_agent_sessions_to_backend.py
```

脚本要求：

```text
只读 aniforce-agent/runtime/agent/tasks.db
写 backend/data/sqlite/animagus.db
日志写 logs/drafts/
可重复执行，按 session_id upsert
```

### 风险 5：SDK cache 与产品 session 生命周期不一致

处理：

```text
这是允许的。
产品 session 存在不代表 SDK cache 一定存在。
SDK cache 存在不代表产品 session active。
run 前以 backend agent_sessions 为准。
```

---

## 8. 完成定义

```text
功能：
- backend 有 agent_sessions 产品表
- /api/v1/agent/sessions 全部由 backend 本地读写
- create session 同步创建 session_states
- run 前校验 backend session 归属与 active 状态
- agent-service 不再作为产品 session 事实源
- SDK SQLiteSession 只作为 runtime cache

验证：
- agent-service 停止时，backend session create/list/get/rename/archive 仍可用
- 清理 aniforce-agent/runtime/agent/sessions.db 不影响 backend session 列表
- 清理 aniforce-agent/runtime/agent/tasks.db 不影响 backend session 列表
- 同一 session_id 的 SDK cache 多轮记忆仍可用
- archived session 不能继续 run
- 用户 A 不能读取/修改/归档用户 B 的 session

代码：
- backend session endpoints 不再调用 AgentGatewayService 的 session 方法
- frontend 不再直连 /api/agent/sessions
- agent-service session API 标记 deprecated 或不再被新代码调用
```

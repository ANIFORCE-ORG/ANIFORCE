# Agent Session / Run / Workspace 改造开发手册

**日期**：2026-06-23  
**性质**：架构改造方案 + 分 Block E2E 验证手册  
**参考**：`aniforce-agent/tests/e2e_openai/DEV_MANUAL.md`、`docs/design/session-state-architecture.md`、OpenAI Agents SDK `Session` / `RunState` 原生能力  

---

## 0. 目标

当前 agent-service 同时承担了三类状态：

1. 产品会话状态：session 元数据、标题、归档、用户归属。
2. LLM runtime 状态：OpenAI Agents SDK 的 `SQLiteSession` 对话缓存。
3. 执行记录状态：task、events、SSE 历史、消息重建。

这些状态的生命周期不同，放在 agent-service 里会导致：

- agent-service 从 runtime 变成事实存储。
- 服务重启、清理 runtime、横向扩容时容易丢失或分裂用户历史。
- `Task` 和 `Act` 概念重复，增加开发和排障成本。
- 前端消息历史依赖 agent-service event replay，而不是产品级消息表。

本次改造目标：

```text
Backend = 产品事实源
- session 元数据（user_id, title, status, created_at）
- 用户可见消息历史（前端展示的聊天记录）
- workspace/session state（业务上下文、linked entities、changelog）
- agent run execution log（执行记录、状态、token usage）

Agent Service = agent runtime
- 创建 Agent / SandboxAgent
- 调用 OpenAI Agents SDK
- MCP tool 调 backend
- 转换 SDK stream events
- 可选保留 LLM raw replay cache（SQLite 本地缓存）

OpenAI Agents SDK Session = LLM 对话缓存
- 只存 ResponseInputItem / tool call replay items
- 不存 session title / user ownership / workspace state
- 不作为用户可见聊天历史事实源
- 可以清空/compaction，不影响产品数据
```

**关键决策**：
1. ✅ Session 元数据和用户可见消息历史迁移到 backend
2. ✅ Task 降级为 Run execution log，不再做业务编排
3. ✅ Act 暂不实现，用 tool timeline + changelog 替代
4. ✅ SDK Session cache 短期保留本地 SQLite（性能考虑）
5. ✅ 当期优先保证已调试能力不退化；HITL / RunState 作为后续扩展，不进入第一阶段必做范围

---

## 1. 核心边界

### 1.1 产品 Session

产品 session 属于 backend。

职责：

- session 创建、列表、重命名、归档。
- user_id 权限隔离。
- 用户可见消息历史（见 1.2）。
- 当前 workspace 状态摘要（见 1.5）。
- 与业务实体的关联。

建议表：

```sql
CREATE TABLE agent_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',  -- active / archived
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    archived_at TEXT
);

CREATE INDEX idx_agent_sessions_user_updated
ON agent_sessions(user_id, updated_at DESC);

CREATE INDEX idx_agent_sessions_status
ON agent_sessions(status);
```

**重要**：此表在 backend，不在 agent-service。agent-service 不拥有产品 session 生命周期。

### 1.2 用户可见消息历史

用户可见消息历史属于 backend，不从 agent-service events 重建。

职责：

- 前端 ChatWindow 展示。
- 历史会话恢复。
- 用户导出、搜索、审计。
- 与 SDK raw items 解耦。

建议表：

```sql
CREATE TABLE agent_messages (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content_json TEXT NOT NULL,
    run_id TEXT,
    sequence INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES agent_sessions(session_id)
);

CREATE INDEX idx_agent_messages_session_seq
ON agent_messages(session_id, sequence);
```

说明：

- `content_json` 存前端展示结构，例如 text / thinking / toolCall blocks。
- 不直接存 SDK `TResponseInputItem`，避免 UI 历史被 SDK 内部格式绑死。
- thinking 不作为长期事实源：dev 可保存 `thinking.content` 便于调试；prod 默认只保存 `thinking.summary` 或直接丢弃 thinking block，除非隐私与合规策略明确允许。

### 1.3 SDK Session Cache

SDK session 是 LLM replay cache，不是产品 session。

**短期方案（推荐）**：

```text
agent-service/runtime/agent/sessions.db
  agent_sessions      SDK SQLiteSession 内部 metadata
  agent_messages      SDK ResponseInputItem JSON
```

**为什么保留本地 SQLite？**
- SDK Session 高频读写（每次 run 都调用 get_items/add_items）
- 本地 SQLite 性能最好，避免网络开销
- 作为 runtime cache，丢失不影响产品数据
- 单机部署足够用

**约束**：
- 明确标记为 runtime cache，定期清理（24h）
- 清空不影响 backend 产品 session/messages
- agent-service 重启后 cache 仍在（除非手动清理）

**中期优化（可选）**：

定期 compaction，把旧对话摘要写入 backend：

```python
# 伪码：当 SDK Session items 超过阈值时
if len(sdk_session.items) > 100:
    # 1. 生成旧对话摘要
    summary = await summarize_old_conversation(sdk_session.items[:-20])
    
    # 2. 写入 backend SessionState.summary
    await backend.update_session_state(session_id, summary=summary)
    
    # 3. 清空旧 items，只保留最近 20 轮
    await sdk_session.clear_old_items(keep_recent=20)
```

**长期方案（分布式部署）**：

如果需要 agent-service 横向扩展：

- **推荐**：用 Redis 作为共享 SDK Session backend
- **不推荐**：实现 BackendSession 通过 HTTP 读写（增加网络延迟）

建议表（backend，可选）：

```sql
-- 如果未来需要 BackendSession 实现
CREATE TABLE agent_llm_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    item_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_agent_llm_items_session_id
ON agent_llm_items(session_id, id);
```

原则：

- 这张表只给 SDK replay 使用。
- 不直接给前端展示。
- 可以做 compaction、裁剪、迁移。
- 短期不实现，保持简单。

### 1.4 Run / Execution

把当前 `Task` 降级成 `Run`。

Run 是一次用户 turn 的执行记录，不是业务编排对象。

同一 `session_id` 同时只允许一个 `running` / `requires_action` run。当已有未完成 run 时，新建 run 直接返回 `409 SESSION_RUN_IN_PROGRESS`，第一版不做队列。前端重试、SSE 断开重连、网关超时重放必须通过 `idempotency_key` 幂等处理。

建议表：

```sql
CREATE TABLE agent_runs (
    run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL,
    input_text TEXT NOT NULL,
    trace_id TEXT,
    idempotency_key TEXT,
    usage_json TEXT,
    error_json TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX idx_agent_runs_session_started
ON agent_runs(session_id, started_at DESC);

CREATE UNIQUE INDEX idx_agent_runs_idempotency
ON agent_runs(user_id, session_id, idempotency_key);
```

最小状态机：

```text
queued -> running -> completed
queued -> running -> error
queued -> running -> cancelled
queued -> running -> requires_action -> running -> completed/error/cancelled
```

保留状态机的原因：

- SSE 正在运行时需要知道 run 是否仍活着。
- 用户取消需要有目标。
- 排障需要知道失败在哪一次 run。
- HITL 需要 `requires_action`。

不再承担：

- 不做 task_type 业务分类。
- 不保存复杂 result 作为业务状态。
- 不从 run events 重建完整产品 session。

### 1.5 SessionState / Workspace Projection

SessionState 是 backend 的业务上下文抽象层。

当前 `backend/app/models/session_state.py` 已有基础字段：

```python
session_id: str
user_id: str
mode: str                      # general / creative / analysis
linked_entities_json: str      # {"projects": ["proj_xxx"], "campaigns": ["camp_xxx"]}
summary: str                   # 业务上下文摘要（可选 compaction 生成）
pending_actions_json: str      # 待审批操作（HITL 用）
changelog_json: str            # 业务变更历史
ui_snapshot_json: str          # 前端状态快照
status: str                    # active / archived
last_error_json: str
version: int                   # 乐观锁
created_at: datetime
updated_at: datetime
```

**建议调整**：

```text
pending_actions_json -> pending_approvals_json  # 语义更准确
```

**changelog 格式示例**：

```json
[
  {
    "type": "project.created",
    "entity_id": "proj_xxx",
    "entity_name": "Test Project",
    "timestamp": "2026-06-23T10:30:00Z",
    "run_id": "run_xxx"
  },
  {
    "type": "campaign.updated",
    "entity_id": "camp_xxx",
    "changes": {"budget": 10000},
    "timestamp": "2026-06-23T10:35:00Z",
    "run_id": "run_yyy"
  }
]
```

**linked_entities 格式示例**：

```json
{
  "projects": ["proj_xxx"],
  "campaigns": ["camp_yyy", "camp_zzz"],
  "materials": []
}
```

**SessionState mutation 约束**：

所有 `linked_entities_json`、`changelog_json`、`summary`、`pending_approvals_json` 更新必须经过统一服务：

```text
backend/app/services/session_state_mutation.py
```

禁止业务 API 直接随手写 `session_states` 字段，避免 changelog 丢失、linked_entities 不一致、summary 未同步更新。

**summary 用途**：

当 SDK Session cache 被清空或 compaction 后，`summary` 提供业务上下文：

```text
当前项目: Test Project (proj_xxx)
已创建广告系列: Campaign A, Campaign B
当前预算: 10000 USD
上次操作: 调整预算
```

agent 下次 run 时可以从 summary 恢复业务现场，而不依赖完整 LLM 对话历史。

---

## 2. 目标架构

```text
┌──────────────────────────────────────────────────────────────┐
│ Frontend                                                     │
│                                                              │
│ ChatWindow                                                   │
│ - 从 backend agent_messages 读取历史                         │
│ - 订阅 backend /agent/runs SSE                               │
│                                                              │
│ Workspace                                                    │
│ - 从 backend business APIs 查询 projects/campaigns/materials │
│ - 收到 side_effect 后刷新对应 panel                          │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│ Backend                                                      │
│                                                              │
│ Product Session                                              │
│ - agent_sessions                                             │
│ - agent_messages                                             │
│                                                              │
│ Workspace State                                              │
│ - session_states                                             │
│ - changelog                                                  │
│ - linked_entities                                            │
│                                                              │
│ Run Gateway                                                  │
│ - create agent_runs                                          │
│ - build business_context_summary                             │
│ - forward stream to agent-service                            │
│ - persist visible messages                                   │
│ - emit side_effect                                           │
└───────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────┐
│ Agent Service                                                │
│                                                              │
│ Runtime only                                                 │
│ - OpenAISDKAdapter                                           │
│ - AgentRuntime                                               │
│ - Sandbox workspace                                          │
│ - MCP connection                                             │
│ - SDK stream event transform                                 │
│                                                              │
│ Optional runtime cache                                       │
│ - SQLiteSession or BackendSession                            │
└───────────────────────────────┬──────────────────────────────┘
                                │ MCP tool calls
                                ▼
┌──────────────────────────────────────────────────────────────┐
│ Backend Business APIs                                        │
│ - projects / campaigns / materials / metrics                 │
│ - writes update DB + SessionState changelog                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. API 合约

### 3.1 Frontend -> Backend

Session：

```text
GET    /api/v1/agent/sessions
POST   /api/v1/agent/sessions
GET    /api/v1/agent/sessions/{session_id}
PATCH  /api/v1/agent/sessions/{session_id}
POST   /api/v1/agent/sessions/{session_id}/archive
```

Run：

```text
POST   /api/v1/agent/runs
GET    /api/v1/agent/runs/{run_id}
POST   /api/v1/agent/runs/{run_id}/cancel
```

`POST /api/v1/agent/runs` request：

```json
{
  "session_id": "session_xxx",
  "prompt": "当前有哪些再投项目",
  "context_snapshot": {
    "route": "/projects",
    "activePanel": "context",
    "selected_entities": {}
  },
  "idempotency_key": "client_msg_20260623_001"
}
```

SSE events：

```text
runtime.started
thinking.updated
message.updated
tool_call.started
tool_call.completed
side_effect
message.completed
runtime.completed
runtime.error
runtime.cancelled
runtime.requires_action
```

### 3.2 Backend -> Agent Service

内部 runtime API：

```text
POST /api/runtime/runs
POST /api/runtime/runs/{run_id}/resume
POST /api/runtime/runs/{run_id}/cancel
```

`POST /api/runtime/runs` request：

```json
{
  "run_id": "run_xxx",
  "session_id": "session_xxx",
  "user_id": "user_xxx",
  "prompt": "当前有哪些再投项目",
  "auth_token": "Bearer ...",
  "business_context_summary": "...",
  "ui_snapshot": {},
  "sdk_session_mode": "sqlite"
}
```

说明：

- agent-service 不创建产品 session。
- agent-service 不判断 session 归属，backend 已校验。
- agent-service 只使用 session_id 构造 SDK Session cache key。

---

## 4. 分 Block 开发计划

每个 Block 必须满足：

```text
目标明确
产物明确
最小代码改动
E2E 脚本可重复运行
通过后再进入下一 Block
```

Python 执行统一规则：

```bash
cd /workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE
if [ ! -d ".venv" ]; then
  UV_CACHE_DIR=./uv_cache uv venv --python 3.11
fi
UV_CACHE_DIR=./uv_cache uv run python <script>
```

服务启动前先检查端口：

```bash
ss -ltnp | grep 8010 || true
ss -ltnp | grep 8020 || true
```

---

## Block 0: 基线冻结与测试目录准备

### 目标

冻结当前行为，避免改造中不知道哪里坏了。

### 产物

```text
aniforce-agent/tests/e2e_openai_refactor/
  README.md
  block0_baseline_current_behavior.py
```

### 验证点

- backend health 正常。
- agent-service health 正常。
- 当前 session 创建、run、历史读取仍可用。
- 当前 MCP `list_projects` 能通过 agent-service 调到 backend。

### 执行

```bash
UV_CACHE_DIR=./uv_cache uv run python aniforce-agent/tests/e2e_openai_refactor/block0_baseline_current_behavior.py
```

### 验收标准

```text
Block 0: passed 6/6
```

---

## Block 1: Backend Product Session 表与 API

### 目标

把产品 session 生命周期迁到 backend。

### 代码范围

```text
backend/app/models/agent_session.py
backend/app/repositories/impl/sqlite_agent_session_repo.py
backend/app/services/agent_session_service.py
backend/app/api/v1/agent.py 或拆分 router
backend/app/config/database 初始化/migration
```

### 数据表

实现：

```text
agent_sessions
```

字段以第 1.1 节为准。

### API

```text
GET    /api/v1/agent/sessions
POST   /api/v1/agent/sessions
GET    /api/v1/agent/sessions/{session_id}
PATCH  /api/v1/agent/sessions/{session_id}
POST   /api/v1/agent/sessions/{session_id}/archive
```

### 兼容策略

- 前端仍调用 backend `/api/v1/agent/sessions`。
- backend 不再透传 agent-service session API。
- agent-service 旧 `/api/agent/sessions` 暂保留但标记 deprecated，只用于过渡测试。

### E2E 脚本

```text
aniforce-agent/tests/e2e_openai_refactor/block1_backend_product_session.py
```

### 验证点

1. 用户 A 创建 session 成功。
2. 用户 A 列表可见。
3. 用户 B 列表不可见。
4. 用户 B 访问用户 A session 返回 404。
5. rename 后标题变化。
6. archive 后 active 列表隐藏。
7. archive 后 run 被拒绝。

### 执行

```bash
UV_CACHE_DIR=./uv_cache uv run python aniforce-agent/tests/e2e_openai_refactor/block1_backend_product_session.py
```

### 验收标准

```text
Block 1: passed 7/7
```

---

## Block 2: Backend 用户可见消息历史

### 目标

用户可见聊天历史迁到 backend，不再从 agent-service task events 重建。

### 代码范围

```text
backend/app/models/agent_message.py
backend/app/repositories/impl/sqlite_agent_message_repo.py
backend/app/services/agent_message_service.py
backend/app/services/chat_event_assembler.py
```

### 数据表

实现：

```text
agent_messages
```

字段以第 1.2 节为准。

### content_json 格式定义

用户可见消息的 `content_json` 字段存储前端展示结构：

```json
{
  "blocks": [
    {
      "type": "text",
      "content": "好的，我来创建项目"
    },
    {
      "type": "thinking",
      "summary": "分析需求和参数",
      "collapsed": true
    },
    {
      "type": "tool_call",
      "tool": "create_project",
      "args": {"name": "Test Project", "budget": 10000},
      "status": "completed",
      "result": {"project_id": "proj_xxx", "name": "Test Project"}
    }
  ],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 80,
    "total_tokens": 230
  }
}
```

**Block 类型说明**：

- `text`: 普通文本回复
- `thinking`: 思考摘要；开发环境可额外保存 `content`，生产默认不保存完整 thinking
- `tool_call`: 用户可见执行过程（tool、args、status、result），可裁剪、折叠、脱敏，不作为审计事实源
- `error`: 错误信息（仅在 run error 时写入）

**注意**：
- 不直接存 SDK `TResponseInputItem`，避免 UI 被 SDK 内部格式绑死。
- thinking 长文本仅 dev 默认保存；prod 默认只保存 summary 或不保存 thinking block。
- tool_call 只服务前端 timeline 展示，允许裁剪、折叠、脱敏；业务审计以 `SessionState.changelog` 和 business DB 为准。

### 写入策略

每次 run：

1. backend 收到用户 prompt，立即写入 user message。
2. backend 转发 agent-service SSE。
3. backend 聚合 `thinking.updated`、`message.updated`、`tool_call.*`。
4. `message.completed` 或 `runtime.completed` 时写入 assistant message。
5. `runtime.error` 时写入 error block 或只写 run error，按产品策略决定。

实现：

```python
# backend/app/services/chat_event_assembler.py
class ChatEventAssembler:
    """从 agent-service SSE 聚合成 agent_messages.content_json"""
    
    def assemble_assistant_message(self, events: list[dict]) -> dict:
        blocks = []
        usage = None
        
        for event in events:
            if event["type"] == "thinking.updated":
                block = {
                    "type": "thinking",
                    "summary": self._summarize_thinking(event["content"]),
                    "collapsed": True
                }
                if self.save_full_thinking:
                    block["content"] = event["content"]
                blocks.append(block)
            elif event["type"] == "message.updated":
                blocks.append({
                    "type": "text",
                    "content": event["content"]
                })
            elif event["type"] == "tool_call.completed":
                blocks.append({
                    "type": "tool_call",
                    "tool": event["tool"],
                    "args": event["args"],
                    "status": "completed",
                    "result": event["result"]
                })
            elif event["type"] == "runtime.completed":
                usage = event.get("usage")
        
        return {"blocks": blocks, "usage": usage}
```

### E2E 脚本

```text
aniforce-agent/tests/e2e_openai_refactor/block2_backend_visible_messages.py
```

### 验证点

1. 创建 session 后消息为空。
2. run 一轮后 backend session detail 返回 user + assistant。
3. assistant content 包含 text block。
4. 工具调用时 assistant content 包含 toolCall block。
5. 刷新/重启 agent-service 后 backend 历史仍存在。
6. 用户 B 无法读取用户 A messages。

### 执行

```bash
UV_CACHE_DIR=./uv_cache uv run python aniforce-agent/tests/e2e_openai_refactor/block2_backend_visible_messages.py
```

### 验收标准

```text
Block 2: passed 6/6
```

---

## Block 3: Task 降级为 Run Execution Log

### 目标

把当前 agent-service `tasks/tasks.db/events` 的产品职责迁到 backend `agent_runs`。

### 代码范围

```text
backend/app/models/agent_run.py
backend/app/repositories/impl/sqlite_agent_run_repo.py
backend/app/services/agent_run_service.py
backend/app/services/agent_gateway.py
aniforce-agent/app/api/runs.py
aniforce-agent/app/services/agent_task_service.py
```

### 数据表

实现：

```text
agent_runs
```

字段以第 1.4 节为准，必须包含 `idempotency_key`。

### 运行链路

```text
frontend
  -> backend POST /api/v1/agent/runs
    -> backend create agent_runs(status=queued)
    -> backend mark running
    -> backend POST agent-service /api/runtime/runs
    -> backend stream SSE to frontend
    -> backend persist visible messages
    -> backend mark completed/error/cancelled
```

### agent-service 变化

- 不再创建 task。
- 入参必须带 `run_id/session_id/user_id`。
- stream event 上只附加 `run_id`，不再依赖 `task_id`。
- 旧 `AgentTaskEvent.task_id` 逐步改为 `run_id`，过渡期可双写字段。

### E2E 脚本

```text
aniforce-agent/tests/e2e_openai_refactor/block3_run_execution_log.py
```

### 验证点

1. backend 创建 run_id。
1.1 相同 `idempotency_key` 重试返回同一个 run，不重复创建业务执行。
2. SSE 第一条包含 `runtime.started` 和 run_id。
3. run 结束后 `agent_runs.status=completed`。
4. token usage 写入 `usage_json`。
5. 出错时 `status=error` 且 `error_json` 有内容。
6. 用户 B 不能查询用户 A run。
7. agent-service runtime DB 不再新增产品 task/session 元数据。

### 执行

```bash
UV_CACHE_DIR=./uv_cache uv run python aniforce-agent/tests/e2e_openai_refactor/block3_run_execution_log.py
```

### 验收标准

```text
Block 3: passed 7/7
```

---

## Block 4: Agent Service Runtime API 瘦身

### 目标

agent-service 只保留 runtime 职责。

### 代码范围

```text
aniforce-agent/app/api/runtime_runs.py
aniforce-agent/app/agent/runtime.py
aniforce-agent/app/agent/openai_adapter.py
aniforce-agent/app/models/runtime_event.py
```

### 新接口

```text
POST /api/runtime/runs
```

### 废弃接口

```text
/api/agent/sessions
/api/agent/tasks
```

过渡期策略：

- 不立即删除旧接口。
- 旧接口返回 deprecation warning header。
- 新 E2E 只打新 runtime API。

### E2E 脚本

```text
aniforce-agent/tests/e2e_openai_refactor/block4_runtime_api_slim.py
```

### 验证点

1. 不传 `run_id` 返回 422。
2. 不传 `session_id` 返回 422。
3. 不传 `auth_token` 时 MCP 写操作被拒绝。
4. 正常入参能完成简单回复。
5. 正常入参能完成 `list_projects` 工具调用。
6. agent-service 不写产品 session 表。

### 执行

```bash
UV_CACHE_DIR=./uv_cache uv run python aniforce-agent/tests/e2e_openai_refactor/block4_runtime_api_slim.py
```

### 验收标准

```text
Block 4: passed 6/6
```

---

## Block 5: SDK Session Cache 边界确认

### 目标

明确 SDK Session 只用于 LLM replay cache，不能作为用户历史事实源。

### 短期实现（当前采用）

继续使用本地 SQLite 作为 SDK Session backend：

```text
aniforce-agent/runtime/agent/sessions.db
```

**原因**：
- SDK Session 需要高频读写（每次 run 都 add_items/get_items）
- 本地 SQLite 性能最好，避免网络开销
- 作为 runtime cache，丢失不影响产品数据

**约束**：
- db_path 从配置读取
- 表只由 SDK `SQLiteSession` 使用
- 清空此 DB 不影响 backend 产品 session 列表和 visible messages
- 定期清理策略：保留最近 24 小时，旧数据自动删除

**配置示例**：

```python
# aniforce-agent/app/config/agent.py
SDK_SESSION_DB_PATH = os.getenv(
    "SDK_SESSION_DB_PATH",
    "runtime/agent/sessions.db"
)
SDK_SESSION_RETENTION_HOURS = int(os.getenv(
    "SDK_SESSION_RETENTION_HOURS",
    "24"
))
```

### 中期优化（可选）

如果 LLM cache 过大，可以定期 compaction：

```python
# 伪码
async def compact_old_sessions():
    """定期把旧对话摘要写入 backend SessionState.summary"""
    for session_id in get_old_sessions():
        # 1. 从 SDK Session 读取完整对话历史
        items = await sdk_session.get_items()
        
        # 2. 用 LLM 生成摘要
        summary = await summarize_conversation(items)
        
        # 3. 写入 backend SessionState
        await backend.update_session_state(
            session_id,
            summary=summary
        )
        
        # 4. 清空 SDK Session cache
        await sdk_session.clear_session()
```

这样 agent-service 只保留最近 N 轮 raw items，旧对话通过 summary 提供上下文。

### 长期方案（分布式部署）

如果需要 agent-service 横向扩展，可以：

**方案 A：共享 Redis 作为 SDK Session backend**

```python
class RedisSession(Session):
    """用 Redis 替代 SQLite，支持多实例共享"""
    
    async def get_items(self, limit: int | None = None):
        items = await redis.lrange(f"session:{self.session_id}", 0, limit or -1)
        return [json.loads(item) for item in items]
    
    async def add_items(self, items: list[TResponseInputItem]):
        await redis.rpush(
            f"session:{self.session_id}",
            *[json.dumps(item) for item in items]
        )
        await redis.expire(f"session:{self.session_id}", 86400)  # 24h TTL
```

**方案 B：BackendSession（不推荐）**

实现 `BackendSession(Session)` 让 SDK 通过 HTTP 读写 backend：

```python
class BackendSession(Session):
    async def get_items(self):
        resp = await http.get(f"/api/internal/sessions/{self.session_id}/items")
        return resp.json()
    
    async def add_items(self, items):
        await http.post(f"/api/internal/sessions/{self.session_id}/items", json=items)
```

**不推荐原因**：
- 增加网络延迟
- backend 成为 SDK 高频访问的瓶颈
- 没有必要为了"完美分层"牺牲性能

**建议**：
- 单机部署：继续用 SQLite（当前方案）
- 多实例部署：用 Redis（方案 A）
- 不要强行用 backend HTTP API（方案 B）

### E2E 脚本

```text
aniforce-agent/tests/e2e_openai_refactor/block5_sdk_session_cache_boundary.py
```

### 验证点

1. 同 session 多轮，LLM 能记住上文。
2. 清空 SDK cache 后，backend messages 仍存在。
3. 清空 SDK cache 后，LLM 不再依赖旧 raw replay，但 backend business_context_summary 仍能提供业务现场。
4. agent-service 重启后，在 SDK cache 存在时可 resume。
5. agent-service 重启后，backend session/messages 不丢。

### 执行

```bash
UV_CACHE_DIR=./uv_cache uv run python aniforce-agent/tests/e2e_openai_refactor/block5_sdk_session_cache_boundary.py
```

### 验收标准

```text
Block 5: passed 5/5
```

---

## Block 6: SessionState / Workspace Projection

### 目标

让 backend 成为 workspace 状态投影源。

### 代码范围

```text
backend/app/models/session_state.py
backend/app/repositories/impl/sqlite_session_state_repo.py
backend/app/services/business_context_builder.py
backend/app/services/session_state_mutation.py
backend/app/services/side_effect_service.py
```

### 保留字段

当前 `SessionState` 已有：

```text
linked_entities_json
summary
pending_actions_json
changelog_json
ui_snapshot_json
status
last_error_json
```

建议改名或语义收敛：

```text
pending_actions_json -> pending_approvals_json
```

如果暂不做 HITL，可以先保留字段但不扩展 Act。

### E2E 脚本

```text
aniforce-agent/tests/e2e_openai_refactor/block6_workspace_projection.py
```

### 验证点

1. 创建项目工具调用后，backend project DB 有新记录。
2. `SessionState.linked_entities` 记录 project id。
3. `SessionState.changelog` 记录 `project.created`。
4. SSE 返回 `side_effect`，指示 frontend refresh projects。
5. 后续 run 的 `business_context_summary` 包含该 project。
6. 前端 workspace 查询 backend API 能看到一致数据。

### 执行

```bash
UV_CACHE_DIR=./uv_cache uv run python aniforce-agent/tests/e2e_openai_refactor/block6_workspace_projection.py
```

### 验收标准

```text
Block 6: passed 6/6
```

---

## Block 7: HITL / Requires Action 后续扩展

### 目标

如果后续确实需要人工审批，实现最小可用的 Human-in-the-Loop。当前改造首期不把它作为必达能力，避免影响已调试通路。

### 推荐方案（可选）：SDK RunState pause / resume

真实 DeepSeek + ChatCompletions 基线已验证：

```text
needs_approval=True -> ToolApprovalItem
RunResult.to_state() -> RunState JSON
RunState.approve(interruption)
Runner.run(agent, state) -> 从审批点继续执行
```

调试产物：

```text
drafts/260624/02_hitl_probe.py
logs/drafts/hitl_probe_20260624_160623.jsonl
```

实测结果：

```text
interruptions_count = 1
interruption.type = ToolApprovalItem
tool_name = delete_project
RunState JSON size ~= 8KB
approve 后 resume 成功
```

**流程**：

```text
1. Agent 调用高风险工具（如 delete_campaign）
2. SDK 产生 ToolApprovalItem，不执行工具
3. agent-service 返回 runtime.requires_action
4. backend 保存待审批信息和 RunState：
   {
     "tool": "delete_campaign",
     "args": {"campaign_id": "camp_xxx"},
     "risk_reason": "删除操作不可逆",
     "run_state": "{...}"
   }
5. frontend 显示确认弹窗
6. 用户点击 approve：
   - backend 标记 approval
   - agent-service 恢复 RunState
   - RunState.approve(interruption)
   - Runner.run(agent, state) 从审批点继续执行
7. 用户点击 reject：
   - run 标记 cancelled
   - agent 返回"操作已取消"
```

### 代码范围

```text
backend/app/models/agent_run.py (增加 pending_approval 字段)
backend/app/services/agent_run_service.py
aniforce-agent/app/agent/run_state_store.py (新增或并入 runtime)
aniforce-agent/app/api/runtime_runs.py
```

### 数据表调整

在 `agent_runs` 表增加字段：

```sql
ALTER TABLE agent_runs ADD COLUMN pending_approval_json TEXT;
ALTER TABLE agent_runs ADD COLUMN run_state_json TEXT;
```

存储格式：

```json
{
  "tool": "delete_campaign",
  "args": {"campaign_id": "camp_xxx"},
  "risk_reason": "删除操作不可逆",
  "interruption": {
    "type": "ToolApprovalItem",
    "tool_name": "delete_campaign",
    "call_id": "call_xxx"
  },
  "requested_at": "2026-06-23T10:30:00Z"
}
```

### 前端交互

```typescript
// 收到 runtime.requires_action 事件
if (event.type === 'runtime.requires_action') {
  const approval = await showConfirmDialog({
    title: '确认操作',
    message: event.risk_reason,
    tool: event.tool,
    args: event.args
  })
  
  if (approval) {
    await approveRun(runId)
  } else {
    await rejectRun(runId)
  }
}
```

### E2E 脚本

```text
aniforce-agent/tests/e2e_openai_refactor/block7_hitl_run_state.py
```

### 验证点

1. 高风险工具（delete_campaign）触发 `runtime.requires_action`。
2. backend `agent_runs.status=requires_action`。
3. backend `pending_approval_json` 和 `run_state_json` 有内容。
4. 用户 approve 后 resume，工具成功执行。
5. 用户 reject 后 run 标记 cancelled。
6. 非高风险工具不触发审批流程。

### 执行

```bash
UV_CACHE_DIR=./uv_cache uv run python aniforce-agent/tests/e2e_openai_refactor/block7_hitl_run_state.py
```

### 验收标准

```text
Block 7: passed 6/6
```

---

### 降级方案

如果 RunState 反序列化失败或 agent/tool graph 版本不兼容，降级为"重新 run + approval flag"：

```text
1. 保存 {tool, args, risk_reason, approved=true}
2. 用户重新发送继续执行请求
3. agent 检查 approval flag 后执行工具
4. 原 run 标记 failed_to_resume，新 run 记录实际执行
```

**何时需要？**
- 一个 run 包含多步操作，中间需要多次审批
- 需要暂停后恢复复杂状态（多工具、多分支）
- 用户审批后不是"重新 run"，而是"从暂停点继续"

**数据表（扩展）**：

```sql
CREATE TABLE agent_run_states (
    run_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    state_json TEXT NOT NULL,           -- SDK RunState 序列化
    interruptions_json TEXT NOT NULL,   -- SDK interruptions
    agent_version TEXT NOT NULL,        -- agent 版本，用于兼容性检查
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**流程**：

```text
1. SDK result.interruptions 有内容
2. agent-service 保存 result.state_snapshot
3. backend 保存 RunState + agent_version
4. 用户审批后 POST /runs/{run_id}/resume
5. agent-service 检查 agent_version 兼容性
6. Runner.run(agent, state=saved_state)
```

**风险控制**：
- RunState 保存时长限制（24h），过期拒绝 resume
- agent 版本变化时拒绝 resume，提示重新发起
- 反序列化失败时降级为"重新 run"

**建议**：
- 先实现 MVP（Block 7）
- 观察真实业务需求
- 如果 MVP 不够用，再扩展完整 HITL

---

## Block 8: 移除 Act / Task UI 依赖

### 目标

前端不再依赖 task/act 概念展示业务流程。

### 代码范围

```text
frontend/packages/main-app/src/api/agent.ts
frontend/packages/main-app/src/composables/useHomeAgentSession.ts
frontend/packages/main-app/src/pages/Home.vue
frontend/packages/main-app/src/components/layout/SidebarNav.vue
```

### UI 表达

保留：

- Chat message blocks。
- Tool call timeline blocks。
- Side effect 后 workspace 自动刷新。
- Run status：running / error / requires_action。

移除或冻结：

- Act timeline。
- Task list 作为主导航。
- task_type 驱动的业务面板切换。

### E2E 脚本

```text
aniforce-agent/tests/e2e_openai_refactor/block8_frontend_contract.py
```

### 验证点

1. Sidebar session 列表来自 backend。
2. 点击 session 后消息来自 backend `agent_messages`。
3. 发送消息后 SSE 正常渲染。
4. tool_call block 正常显示。
5. side_effect 后 workspace panel 触发刷新。
6. 不再调用 `/api/agent/tasks`。

### 执行

```bash
UV_CACHE_DIR=./uv_cache uv run python aniforce-agent/tests/e2e_openai_refactor/block8_frontend_contract.py
```

### 验收标准

```text
Block 8: passed 6/6
```

---

## Block 9: 并发、多租户、重启安全

### 目标

验证新边界下的生产安全性。

### E2E 脚本

```text
aniforce-agent/tests/e2e_openai_refactor/block9_concurrency_restart_safety.py
```

### 验证点

1. 同用户同 session 并发 run 返回 409 `SESSION_RUN_IN_PROGRESS`，第一版不做串行队列。
2. 不同 session 可并发执行。
3. 用户 A/B session、messages、runs 完全隔离。
4. backend 重启后产品 session/messages/runs 不丢。
5. agent-service 重启后 runtime 恢复，产品历史不丢。
6. 清空 agent-service runtime cache 不影响 backend 产品历史。
7. MCP tool 调用不会串 JWT。
8. run error 不污染 session active 状态。

### 执行

```bash
UV_CACHE_DIR=./uv_cache uv run python aniforce-agent/tests/e2e_openai_refactor/block9_concurrency_restart_safety.py
```

### 验收标准

```text
Block 9: passed 8/8
```

---

## Block 10: 端到端业务剧本

### 目标

验证 workspace + agentic 的真实业务闭环。

### 剧本

```text
1. 用户创建 session。
2. 用户要求创建项目 "RefactorE2EProject"。
3. Agent 调 MCP create_project。
4. Backend 写 projects。
5. Backend 写 SessionState linked_entities + changelog。
6. SSE 返回 tool_call + side_effect。
7. Frontend/workspace 查询 projects，看到新项目。
8. 用户第二轮问“刚创建的项目是什么？”
9. Agent 通过 business_context_summary 回答。
10. 用户归档 session 后不可继续 run。
```

### E2E 脚本

```text
aniforce-agent/tests/e2e_openai_refactor/block10_workspace_agentic_e2e.py
```

### 验证点

1. session 创建成功。
2. run 创建成功。
3. MCP tool 被调用。
4. backend 业务 DB 有项目。
5. SessionState 有 linked entity。
6. changelog 有 project.created。
7. messages 有 user + assistant。
8. 第二轮能引用业务上下文。
9. side_effect 类型正确。
10. 归档后 run 被拒绝。

### 执行

```bash
UV_CACHE_DIR=./uv_cache uv run python aniforce-agent/tests/e2e_openai_refactor/block10_workspace_agentic_e2e.py
```

### 验收标准

```text
Block 10: passed 10/10
```

---

## 5. 迁移策略

### 5.1 不做大爆炸迁移

按以下顺序切：

```text
1. Backend 新表/API 先落地。
2. Frontend session/message 读路径切 backend。
3. Backend run gateway 开始写 agent_runs。
4. Agent-service 增加新 runtime API。
5. Backend run gateway 切新 runtime API。
6. 旧 task/session API 标记 deprecated。
7. E2E 全绿后删除旧 task/session 产品职责。
```

### 5.2 双写窗口

Block 2 - Block 4 可以短期双写：

```text
agent-service events 仍写旧 tasks.db
backend 同时写 agent_messages / agent_runs
```

双写只用于对账，不作为长期方案。若双写影响当前已调试好的消息流或 run 流，应优先保留现有可用路径，再逐步切换。

### 5.3 删除条件

满足以下条件才删除旧 task API：

```text
Block 1-6、Block 8-10 通过；Block 7 仅在启用 HITL 时要求通过
frontend 不再调用 /api/agent/tasks
backend 不再依赖 agent-service session API
历史消息读取全部来自 backend
```

---

## 6. 风险与处理

### 风险 1：SDK raw items 与用户消息双存不一致

处理：

- 用户可见消息以 backend `agent_messages` 为准。
- SDK raw items 只用于 LLM replay。
- E2E 验证清空 SDK cache 后 backend 历史仍存在。

### 风险 2：LLM cache 清空后模型忘记旧聊天

处理：

- **这是预期行为**。SDK Session 只是 LLM replay cache，清空后 LLM 无法直接引用旧对话。
- 业务上下文通过 `backend SessionState.summary` 和 `business_context_summary` 注入。
- 长对话策略：
  ```python
  # 定期 compaction（可选）
  if len(sdk_session.items) > 100:
      # 1. 生成旧对话摘要
      summary = await summarize_old_conversation(sdk_session.items[:-20])
      
      # 2. 写入 backend SessionState
      await backend.update_session_state(session_id, summary=summary)
      
      # 3. 清空旧 SDK items，只保留最近 20 轮
      await sdk_session.clear_old_items(keep_recent=20)
  ```
- 这样既节省 LLM 上下文，又不丢业务连续性。

### 风险 3：SSE 中断导致 assistant message 未完成

处理：

- backend run status 标记 error/cancelled。
- assistant message 可写 partial block，标记 `status=partial`。
- 下次打开 session 时前端显示“上次回复中断”。

### 风险 4：同 session 并发 run

处理：

- 第一版直接返回 409：`SESSION_RUN_IN_PROGRESS`。
- 暂不实现 `session_lock` 串行队列，避免引入排队超时、取消语义、消息顺序和 SSE 绑定复杂度。
- agent-service 不负责产品级锁。

### 风险 5：HITL 审批流程的状态管理

处理：

**RunState 方案（已通过真实 DeepSeek 基线验证，后续可选实现）**：
- `needs_approval=True` 能产生 `ToolApprovalItem`
- `RunResult.to_state()` 能生成可保存的 RunState JSON
- `RunState.approve(interruption)` 后 `Runner.run(agent, state)` 能从审批点继续执行
- RunState JSON 保存 `schema_version`、`agent_version` 和过期时间
- agent graph 名称、工具名必须保持稳定
- RunState 保存时长限制（24h），过期自动失效

**降级方案**：
- 如果 RunState 反序列化失败，降级为"重新 run + approval flag"
- 风险工具触发 requires_action，保存 `{tool, args, risk_reason, approved}`
- 用户 approve 后重新发送继续执行请求，agent 检查 approval flag 后执行工具
- 原 run 标记 `failed_to_resume` 或 `cancelled`，新 run 记录实际执行

**建议优先级**：
1. 首期先完成 session/message/run/workspace 边界改造，确保现有能力不退化
2. 观察真实业务是否需要审批
3. 如果需要审批，优先实现 RunState resume
4. 保留重新 run 作为兼容降级路径

---

## 7. 完成定义

本改造完成的定义：

```text
功能：
- session 元数据在 backend
- 用户可见消息历史在 backend
- run execution log 在 backend
- agent-service 不再拥有产品 session/task 生命周期
- workspace 状态由 backend SessionState + business DB 投影
- Act 不再作为当前实现对象
- HITL / RunState 作为可选扩展，不阻塞当前改造完成

验证：
- Block 0-6、Block 8-10 E2E 通过
- 清空 aniforce-agent/runtime 不会丢产品 session/messages/runs
- agent-service 重启不影响历史查看
- backend 权限隔离通过
- MCP tool 写入能更新 SessionState changelog
- 现阶段已调试好的消息流、run 流、workspace 刷新流程保持可用

代码：
- 旧 /api/agent/tasks 不再被 frontend/backend 调用
- 旧 agent-service session API 标记 deprecated 或删除
- 文档和测试命令更新
```

---

## 8. 建议的最终目录

```text
backend/app/models/
  agent_session.py
  agent_message.py
  agent_run.py
  session_state.py

backend/app/repositories/impl/
  sqlite_agent_session_repo.py
  sqlite_agent_message_repo.py
  sqlite_agent_run_repo.py
  sqlite_session_state_repo.py

backend/app/services/
  agent_session_service.py
  agent_message_service.py
  agent_run_service.py
  agent_gateway.py
  business_context_builder.py
  session_state_mutation.py
  side_effect_service.py

aniforce-agent/app/api/
  runtime_runs.py

aniforce-agent/app/agent/
  runtime.py
  openai_adapter.py
  session_factory.py

aniforce-agent/tests/e2e_openai_refactor/
  README.md
  block0_baseline_current_behavior.py
  block1_backend_product_session.py
  block2_backend_visible_messages.py
  block3_run_execution_log.py
  block4_runtime_api_slim.py
  block5_sdk_session_cache_boundary.py
  block6_workspace_projection.py
  block7_hitl_run_state.py  # 可选，启用 HITL 时再做
  block8_frontend_contract.py
  block9_concurrency_restart_safety.py
  block10_workspace_agentic_e2e.py
```

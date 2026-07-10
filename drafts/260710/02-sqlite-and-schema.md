# 02 SQLite 与表管理

## 1. 当前阶段数据库布局

第一阶段不强制物理拆分现有 `animagus.db`，先完成逻辑 ownership 和 migration。目标布局：

```text
backend/data/sqlite/agent-control.db   # 产品 Agent 事实
backend/data/sqlite/animagus.db        # 现有业务数据，过渡期可含 Agent 表
aniforce-agent/data/runtime.db         # SDK session/checkpoint
```

若拆库会扩大改动，可暂时共用 `animagus.db`。禁止跨两个 SQLite 文件假设原子事务。

## 2. SQLite 连接规范

每个连接必须启用：

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
```

实现要求：

- 在 SQLAlchemy connect event 中设置 pragma，不靠手工运行。
- 写事务尽量小于 100ms。
- 模型调用、HTTP、文件上传不得放在事务内。
- 对 `database is locked` 做有限退避；不得无限重试。
- API 和 worker 使用独立 session，禁止共享 ORM session。
- 时间统一存 UTC；状态比较使用规范化格式。

## 3. Backend 核心表

### `agent_runs`

保留现有字段，新增：

```text
version INTEGER NOT NULL
status TEXT CHECK(...)
lease_owner TEXT
lease_expires_at DATETIME
heartbeat_at DATETIME
last_event_sequence INTEGER NOT NULL DEFAULT 0
terminal_event_id TEXT UNIQUE
runtime_started_at DATETIME
cancel_requested_at DATETIME
error_code TEXT
retryable BOOLEAN
```

索引：`(status, lease_expires_at)`、`(session_id, status)`、`(user_id, created_at)`。

### `agent_run_events`

```text
id TEXT PRIMARY KEY
run_id TEXT NOT NULL
sequence INTEGER NOT NULL
event_type TEXT NOT NULL
payload_json TEXT NOT NULL
is_terminal BOOLEAN NOT NULL DEFAULT 0
created_at DATETIME NOT NULL
UNIQUE(run_id, sequence)
```

只保存关键事实，不永久保存每个 token delta。

### `agent_messages`

```text
message_id, session_id, run_id, user_id
role, status, content
error_code, created_at, completed_at
```

用户可见历史以此表为准，SDK items 只服务模型上下文。

### `agent_tool_calls`

```text
tool_call_id, run_id, tool_name
status, arguments_json, result_json, error_json
idempotency_key, started_at, completed_at
```

### `agent_approvals`

```text
approval_id, checkpoint_ref, run_id, tool_call_id, user_id
status, original_arguments_json, edited_arguments_json
preconditions_json, expires_at
claimed_by, claimed_at, resolved_by, resolved_at
version
```

### `agent_artifacts`

```text
artifact_id, session_id, run_id, source_tool_call_id
surface, schema_version, status
payload_json, object_uri, entity_versions_json
supersedes_artifact_id, created_at, updated_at
```

### `idempotency_requests`

唯一键应包含 `(user_id, operation, key)`，并保存 request hash、status、response 和 expires_at。相同 key 但不同 request hash 必须返回冲突。

## 4. Runtime 表

`runtime_checkpoints` 增加：

```text
version
status CHECK(pending,resuming,completed,rejected,expired,failed)
claimed_by
claimed_at
context_schema_version
```

claim 必须是单条条件 UPDATE：

```sql
UPDATE runtime_checkpoints
SET status='resuming', claimed_by=:worker, claimed_at=:now, version=version+1
WHERE id=:id
  AND user_id=:user_id
  AND status='pending'
  AND expires_at>:now;
```

影响行数不是 1 就不得恢复 RunState。

## 5. CAS 与 lease

Run claim 示例：

```sql
UPDATE agent_runs
SET status='running', lease_owner=:worker,
    lease_expires_at=:expires, heartbeat_at=:now, version=version+1
WHERE run_id=:run_id
  AND status IN ('queued','interrupted')
  AND (lease_expires_at IS NULL OR lease_expires_at<:now)
  AND version=:expected_version;
```

Session 串行可使用独立 `agent_session_leases` 表，或在 session 上维护 lease。不得依赖 `asyncio.Lock`。

## 6. Migration 规范

- Backend 表只由 Backend Alembic 管理。
- Runtime 表建立独立 migration runner；不得在 repository 的 `ensure_tables()` 中改表。
- migration 文件名使用 `YYMMDD_序号_描述.py`。
- 每个 migration 包含 upgrade、downgrade、数据回填和索引检查。
- 部署顺序采用 expand -> migrate/backfill -> switch code -> contract。
- 禁止提交运行中的 `.db` 作为 schema 发布方式。
- master 新增的 campaign `connection_id` 等字段也必须补 migration，不能只更新模型和数据库二进制。

## 7. PostgreSQL 兼容约束

领域层不得使用 SQLite 专属 SQL。专属 claim、pragma 和 polling 放在 `infrastructure/sqlite/`。Repository protocol 保持稳定，未来 PostgreSQL 实现可使用 `FOR UPDATE SKIP LOCKED`、LISTEN/NOTIFY 和更强约束。

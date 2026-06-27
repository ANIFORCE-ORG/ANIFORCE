# ANIFORCE 后端内嵌 openai-agents-python Agent 服务开发计划

**日期**：2026-06-11  
**项目**：`/workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE`  
**参考资源**：`resources/openai-agents-python`、`resources/AiToEarn`、旧项目 `GrowthAgentService`  
**当前决策**：Agent 服务直接写进 ANIFORCE 后端；单独维护 `/api/v1/agent/*` 接口；共享 `backend` 的 uv 虚拟环境；固定本地端口 `backend=18003`、`frontend=13003`；换用 `openai-agents-python`，旧项目只做能力映射，不照搬旧 Pi/TS agent-service 架构。

---

## 0. 本轮重新想清楚的核心问题

### 0.1 不是迁移旧 agent-service

旧 `GrowthAgentService` 的价值是已经验证过的 Agent 平台能力：

```text
Session / Task / Run / Message / ToolCall / Event / Action / Artifact
CurrentTask / Reducer / Trace / Worker / Idempotency / Cancel / SSE Replay
Tool Policy / Permission / Cost / Deployment
```

但旧实现里这些东西绑定了：

```text
TS agent-service
Pi runtime
独立 agent-service 端口
apps + libs 分离式 workspace
.pi runtime session / skill / MCP 机制
```

现在已经明确换 SDK，所以不能照搬实现。新方向是：

```text
旧项目能力模型
  -> 用 openai-agents-python 重新实现
  -> 直接嵌入 ANIFORCE FastAPI backend
  -> 前端/数据库/部署按 ANIFORCE 当前工程形态演进
```

### 0.2 Agent 服务写进后端，但接口独立

运行形态：

```text
同一个 FastAPI 后端进程，监听 18003
  ├── /api/v1/projects
  ├── /api/v1/campaigns
  ├── /api/v1/materials
  └── /api/v1/agent/*
```

开发环境：

```text
frontend: http://127.0.0.1:13003
backend:  http://127.0.0.1:18003
agent:    不单独开端口，走 backend /api/v1/agent/*
```

环境规则：

```text
backend/.venv          # 后端唯一 Python 虚拟环境
backend/uv_cache       # 后端 uv 缓存
frontend/npm_cache     # 前端 npm/pnpm 缓存，如沿用当前结构
```

### 0.3 流式对话和异步任务不是一回事

这里必须改正：**普通对话不需要异步队列**。对话需要的是低延迟、可流式、可断线续拉；异步队列需要解决的是“业务 Task 执行”而不是每一轮聊天。

两条链路要分开：

```text
Conversation Turn（普通对话轮次）
  用户发一条消息
  -> backend 直接调用 Runner.run_streamed()
  -> backend 边消费 SDK Stream 边向当前 HTTP/SSE 响应输出
  -> 同时沉淀必要消息、usage、轻量事件
  -> 请求结束时本轮对话结束

Business Task Execution（业务任务执行）
  用户触发创建/生成/分析/投放/审批等待等任务
  -> backend 创建 task/run/artifact/action
  -> 短任务可 inline 执行
  -> 长任务/可恢复任务进入 DB-backed worker
  -> worker 消费 Runner.run_streamed()
  -> 前端通过 task events / snapshot 订阅结果
```

关键原则：

```text
对话流式响应可以绑定当前 HTTP/SSE 请求
业务 Task 执行不能依赖前端连接
前端关闭页面不影响已经入队或运行中的业务 Task
普通聊天不必创建队列 run
只有业务目标需要 Task/Run/Worker/Recovery
```

### 0.4 队列预留给 Task，不预留给所有消息

第一阶段不要上 Redis/BullMQ/Celery/Temporal，也不要单独 agent-service。先跑通两类最小闭环：

```text
A. 普通对话闭环
POST /api/v1/agent/chat/stream
  -> 直接 Runner.run_streamed()
  -> 返回流式 assistant 文本
  -> 可保存 conversation message
  -> 不创建业务 task，不入 worker

B. 业务任务闭环
POST /api/v1/agent/tasks
  -> 创建 task/run
  -> inline 执行一个短任务
  -> 生成 artifact/action/current_task
  -> 前端可通过 task snapshot 查看结果
```

第一阶段只有业务任务模型需要预留队列字段：

```text
agent_runs.status = created/running/completed/error/aborted/requires_action
agent_runs.execution_mode = inline/worker
agent_runs.lock_owner
agent_runs.lock_expires_at
agent_runs.heartbeat_at
agent_runs.idempotency_key
agent_runs.run_state_json
agent_runs.runtime_started_at
```

第二阶段只把业务任务切到 DB-backed worker：

```text
POST /api/v1/agent/tasks/{task_id}/runs
  -> 创建 CREATED run 后返回 queued
worker
  -> claim run
  -> 消费 Runner.run_streamed()
  -> 写 task events/artifacts/actions/final status
frontend
  -> SSE / polling 订阅 task 状态变化
```

---

## 1. 从 resources 得到的设计结论

### 1.1 openai-agents-python 关键结论

来自 `resources/openai-agents-python/docs/running_agents.md`、`streaming.md`、`sessions/index.md`、`human_in_the_loop.md`、`tools.md`、`tracing.md`：

1. **Runner 有三种模式**
   - `Runner.run()`：异步非流式。
   - `Runner.run_sync()`：同步包装。
   - `Runner.run_streamed()`：返回 `RunResultStreaming`，通过 `stream_events()` 消费。

2. **stream 必须有明确终止语义**
   - 文档明确：streamed run 在 `stream_events()` 迭代器结束前不算完成。
   - session persistence、approval bookkeeping、history compaction 可能发生在最后一个可见 token 之后。
   - 普通 chat 请求断开可以按用户取消处理；业务 Task 一旦创建，不能因为前端订阅断开就停止，必须由后端 inline executor 或 worker drain/cancel/recover。

3. **取消有 SDK 语义**
   - `result.cancel()` 可中断当前 streaming run。
   - `result.cancel(mode="after_turn")` 可让当前 turn 干净结束后停止。
   - 后端需要保存 running run 对应的 streaming handle / cancellation handle，至少单进程阶段可用内存表管理。

4. **HITL 审批会让 stream 结束并产生 interruptions**
   - `RunResultStreaming.interruptions` 中有待审批 tool call。
   - 需要 `result.to_state()` 保存 `RunState`。
   - 用户 approve/reject 后，用 `Runner.run_streamed(agent, state)` 恢复。
   - 这可以映射为 ANIFORCE 的 `agent_task_actions`。

5. **Session 选择要单一**
   - SDK sessions 不能和 `conversation_id` / `previous_response_id` 同时混用。
   - 本项目第一阶段建议选择 SDK client-managed session，使用 `SQLiteSession` 或 `SQLAlchemySession`。
   - 业务 session 仍由 ANIFORCE 自己维护，SDK session 只是 LLM 上下文存储。

6. **Session 后端选择**
   - 本地开发：`SQLiteSession` / `AsyncSQLiteSession`。
   - 生产关系库：`SQLAlchemySession`。
   - 多 worker/服务共享：`RedisSession` 或 `MongoDBSession`。
   - 当前阶段共享后端 uv 环境，优先 `SQLiteSession` 文件落在项目 runtime 目录；后续切 `SQLAlchemySession`。

7. **工具能力不要裸奔**
   - `@function_tool` 可直接把 Python 函数暴露给 Agent。
   - `needs_approval=True` 或 callable 可触发人工审批。
   - `timeout`、`failure_error_function`、`ToolExecutionConfig(max_function_tool_concurrency=...)` 可限制工具执行。
   - ANIFORCE 必须在 SDK tool 外再包业务权限、dry-run/proposal、审计和 artifact contract。

8. **Tracing 是 SDK 观测，不等于业务事件账本**
   - SDK tracing 默认开启，可用 `RunConfig.workflow_name/trace_id/group_id/trace_metadata`。
   - 生产可设置 `trace_include_sensitive_data=false`。
   - 长 worker 结束后可 `flush_traces()`。
   - 但业务状态仍以 `agent_events` 为准。

### 1.2 AiToEarn 关键结论

来自 `resources/AiToEarn` 的 Docker 部署、Agent controller/runtime、queue、redlock、timeout scheduler：

1. **服务端消费 runtime stream**
   - AiToEarn 的 runtime service 将 SDK generator 转成 Observable。
   - 服务端负责 transform message、写库、状态更新、上传 session、清理 runningTasks。
   - 前端只是接收 SSE chunk，不是 run 状态事实来源。

2. **任务对象比聊天更重要**
   - `ContentGenerationTask` 可列表、收藏、评分、分享、删除、更新标题、查询消息。
   - ANIFORCE 应保留 task 作为业务对象，不要只做 chat session。

3. **Abort 是控制面能力**
   - AiToEarn controller 通过 taskId 发 abort。
   - Runtime 内部有 `runningTasks` 和 `AbortController`。
   - 分布式时用 Redis Pub/Sub 通知运行进程。
   - ANIFORCE 第一阶段可用进程内 registry，worker 阶段再用 DB/Redis 传播。

4. **Keepalive 与断线续拉都需要**
   - SSE 有 keepalive chunk。
   - 任务消息查询支持 `lastMessageId`，用于 SSE 断开后补拉。
   - ANIFORCE 应使用 `after_sequence` 事件续拉，必要时再提供 `last_message_id` 消息续拉。

5. **Timeout/recovery 是定时治理能力**
   - AiToEarn 有 scheduler 每 10 分钟恢复超时 running task。
   - 使用 Redlock 避免多实例重复跑恢复任务。
   - ANIFORCE 先写 recovery service + 手动脚本，后续接 scheduler/Redis lock。

6. **队列要有 jobId、attempts、backoff、remove policy**
   - AiToEarn queue service 用 BullMQ，jobId 防重复，attempts/backoff 控制失败重试。
   - ANIFORCE 先 DB-backed queue：run.idempotency_key + status + lease；后续需要 Redis/Celery 时再替换执行层。

7. **部署外壳值得借鉴**
   - Nginx 单入口。
   - 服务 healthcheck。
   - MongoDB/Redis/ObjectStorage/RustFS 可 compose 化。
   - init 任务初始化默认数据。
   - 环境变量集中配置，生产必须替换默认密钥。

---

## 2. 最终目标架构

```text
Browser :13003
  -> Frontend Home / Live Workspace
  -> EventSource / fetch

FastAPI Backend :18003
  -> /api/v1/agent/*
  -> AgentGatewayService
  -> AgentRunExecutor / AgentWorkerService
  -> OpenAI Agents SDK Runner.run_streamed()
  -> ANIFORCE function tools
  -> agent_events / messages / actions / artifacts

Database / Runtime
  -> SQLite dev first
  -> runtime/agent/sessions/<session_id>/sdk_session.db
  -> runtime/agent/runs/<run_id>/state.json when needed
  -> logs/agent-runtime.log
```

部署上第一阶段只有两个本地服务：

```text
frontend 13003
backend  18003
```

不再有：

```text
agent-service 18004
```

---

## 3. 后端目录设计

```text
backend/app/
  api/v1/
    agent.py                         # Agent 独立 API
    router.py                        # include agent router

  schemas/
    agent.py                         # 请求/响应/SSE/event/action/artifact schema

  models/
    agent_runtime.py                 # Session/Task/Run/Message/ToolCall/Event/Action/Artifact
    ai_call_log.py                   # 后续成本治理

  services/
    agent_gateway_service.py         # API 门面，协调 session/task/run/action
    agent_run_executor.py            # 消费 Runner.run_streamed 的核心执行器
    agent_event_service.py           # 事件校验、入库、广播、SSE formatter
    agent_task_reducer.py            # event -> current_task snapshot
    agent_recovery_service.py        # timeout/stale/reconcile
    agent_worker_service.py          # 第二阶段 DB-backed worker
    agent_artifact_service.py        # artifact 写入、版本、业务对象链接
    agent_tool_policy_service.py     # tool policy / permission / dry-run
    agent_trace_service.py           # trace/correlation

  agents/
    __init__.py
    assistant.py                     # 单 ANIFORCE Assistant 定义
    runtime.py                       # Runner / RunConfig / tracing 封装
    sessions.py                      # SDK session factory
    tools/
      project.py
      market.py
      material.py
      campaign.py
      monitor.py
      session_tools.py               # set_title/output_result/propose_action
```

第一阶段可以少建，但不要违背这个边界：

```text
api 只处理 HTTP/SSE
service 处理业务状态
agents 处理 SDK 对接
tools 调用现有业务 service/repository
models/repositories 负责持久化
```

---

## 4. 端口与启动约定

### 4.1 固定端口

```text
backend:  18003
frontend: 13003
```

### 4.2 启动前端

```bash
cd /workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE/frontend
npm_config_cache=./npm_cache npx pnpm install
npm_config_cache=./npm_cache npx pnpm --filter main-app dev --host 127.0.0.1 --port 13003
```

### 4.3 启动后端

```bash
cd /workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE/backend
if [ ! -d ".venv" ]; then UV_CACHE_DIR=./uv_cache uv venv --python 3.11; fi
UV_CACHE_DIR=./uv_cache uv pip install -r requirements.txt
UV_CACHE_DIR=./uv_cache uv run alembic upgrade head
UV_CACHE_DIR=./uv_cache uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 18003
```

### 4.4 端口检查

启动前只检查，不擅自 kill：

```bash
ss -ltnp | grep -E ':(13003|18003)\b' || true
```

如果占用，回传 PID/进程名，由用户决定是否停止。

---

## 5. API 设计

### 5.1 第一阶段 API 分层

普通对话 API：

```text
GET  /api/v1/agent/health
POST /api/v1/agent/chat/sessions
GET  /api/v1/agent/chat/sessions
GET  /api/v1/agent/chat/sessions/{chat_session_id}
POST /api/v1/agent/chat/sessions/{chat_session_id}/stream
GET  /api/v1/agent/chat/sessions/{chat_session_id}/messages?after_message_id=...
```

业务任务 API：

```text
POST /api/v1/agent/tasks
GET  /api/v1/agent/tasks
GET  /api/v1/agent/tasks/{task_id}
POST /api/v1/agent/tasks/{task_id}/runs
GET  /api/v1/agent/tasks/{task_id}/events?after_sequence=0
GET  /api/v1/agent/tasks/{task_id}/snapshot
POST /api/v1/agent/tasks/{task_id}/abort
POST /api/v1/agent/tasks/{task_id}/actions/{action_id}/respond
GET  /api/v1/agent/task-types
```

说明：

```text
chat session 负责普通多轮对话记忆和消息历史
task 负责业务目标、产物、审批、恢复和异步执行
chat 可以触发 task 创建，但 chat 本身不等于 task
```

### 5.2 普通对话返回方式

`POST /chat/sessions/{id}/stream` 返回流式响应，不返回 queued：

```text
event: message_delta
data: {"delta":"..."}

event: message_completed
data: {"message_id":"msg_...","usage":{...}}

event: done
data: {"chat_session_id":"chat_..."}
```

### 5.3 业务任务 run 返回值

Inline 短任务：

```json
{
  "task_id": "task_...",
  "run_id": "run_...",
  "execution_mode": "inline",
  "status": "running",
  "queued": false,
  "trace_id": "trace_..."
}
```

Worker 长任务：

```json
{
  "task_id": "task_...",
  "run_id": "run_...",
  "execution_mode": "worker",
  "status": "created",
  "queued": true,
  "trace_id": "trace_..."
}
```

前端只有在业务 task 场景中才根据 `task_id/run_id/events/snapshot` 追踪状态。

---

## 6. 流式事件设计

### 6.1 事件分层

```text
SDK Raw Events
  raw_response_event / run_item_stream_event / agent_updated_stream_event

Backend Runtime Events
  sdk.message.delta / sdk.tool.called / sdk.tool.output / sdk.interruption / sdk.completed / sdk.error

ANIFORCE Business Events
  run.started / message.delta / message.completed / tool.started / tool.completed
  action.created / artifact.created / task.phase_changed / run.completed / run.failed
```

前端只消费 ANIFORCE Business Events。

### 6.2 入库策略

不全部入库：

```text
message.delta 高频 token：默认只实时推送，可按策略合并落 assistant message
heartbeat：不入审计账本
连接类事件：不入审计账本
```

必须入库：

```text
session.created
task.created
run.created
run.started
message.user.created
message.assistant.completed
tool.started
tool.completed
tool.failed
action.created
action.resolved
artifact.created
task.phase_changed
task.completed
run.completed
run.failed
run.aborted
run.requires_action
```

### 6.3 后端事件广播

第一阶段可用进程内 pubsub：

```text
AgentEventHub
  append_event() 写 DB
  publish() 推送给本进程 SSE subscribers
```

但不能只存在内存。SSE 断开后必须能用：

```text
GET /events?after_sequence=N
```

补回事件。

### 6.4 SSE 输出格式

```text
event: agent_event
id: 42
data: {"sequence":42,"type":"message.delta",...}
```

keepalive：

```text
event: heartbeat
data: {"ts":...}
```

Nginx 反代时必须：

```text
X-Accel-Buffering: no
Cache-Control: no-cache, no-transform
```

---

## 7. Chat Stream 与 Task Worker 的动手顺序

### 7.1 先做普通对话流式闭环

先做 chat stream，不做 worker。目标是验证新 SDK 的基本对话能力和前端流式体验：

```text
验证 openai-agents-python 能在 backend/.venv 跑
验证 Runner.run_streamed() 能被 FastAPI StreamingResponse/SSE 包装
验证 SDK StreamEvent 能转成前端可显示的 message delta
验证 session memory 能延续多轮对话
```

普通对话接口不创建业务 task，不进入队列：

```text
POST /api/v1/agent/chat/stream
  -> 获取/创建 conversation session
  -> Runner.run_streamed(agent, message, session=sdk_session)
  -> stream_events() 直接转换为 chat delta
  -> 请求结束后保存 assistant final message / usage
```

这个阶段解决的是“聊天能不能稳定流式”，不是“业务任务能不能恢复”。

### 7.2 再做业务 Task inline 执行

第二步才引入 Task/Run，但仍不进 worker。目标是验证产品层对象：

```text
POST /api/v1/agent/tasks
  -> 创建 task
  -> 创建 run(execution_mode=inline)
  -> Runner.run_streamed()
  -> 工具产生 artifact/action
  -> reducer 生成 current_task
```

这时 run 是业务任务执行记录，不是每条聊天消息的必选对象。

### 7.3 最后把业务 Task 切到 DB-backed worker

当 inline task 已能产生 artifact/action/current_task 后，再把“长任务执行”切到 worker。

Worker 不单独项目，只是后端代码库里的进程入口：

```text
backend/scripts/run_agent_worker.py
backend/app/services/agent_worker_service.py
```

执行：

```bash
cd backend
UV_CACHE_DIR=./uv_cache uv run python scripts/run_agent_worker.py --loop
```

claim 规则：

```text
CREATED task run 可 claim
RUNNING 且 lock_expires_at 过期、且未进入 SDK stream 的 run 可 reclaim
已开始 SDK stream 的 run 不盲目重放，交给 recovery/reconcile
```

DB 字段：

```text
execution_mode
lock_owner
lock_expires_at
heartbeat_at
started_at
completed_at
error_message
runtime_started_at
```

### 7.4 何时引入 Redis/Celery

只有满足以下条件再引入：

```text
普通 chat stream 已稳定
业务 task inline 已稳定
单机 DB-backed worker 已跑通
run idempotency / abort / replay 已稳定
需要多 worker 并发或跨进程 abort
SQLite 已成为瓶颈或需要生产部署
```

引入后参考 AiToEarn：

```text
jobId = task_run_id or idempotency_key
attempts / backoff
Redis lock / PubSub abort
timeout scheduler
```

---

## 8. 数据模型优先级

### 8.1 第一阶段必须有

```text
agent_sessions
agent_tasks
agent_runs
agent_messages
agent_events
```

### 8.2 第一阶段建议一起有

```text
agent_tool_calls
agent_task_actions
agent_artifacts
```

因为 `openai-agents-python` 很快会遇到：

```text
tool_called
tool_output
interruptions
output_task_result
```

如果没有这些表，会退化成解析聊天文本。

### 8.3 SDK session 存储

第一阶段：

```text
runtime/agent/sdk-sessions/<business_session_id>.sqlite
```

后续：

```text
SQLAlchemySession -> 复用生产 DB
RedisSession      -> 多 worker 低延迟共享
MongoDBSession    -> 对话文档和多进程扩展
```

不要混用：

```text
SDK Session + conversation_id/previous_response_id
```

第一阶段只选 SDK Session。

---

## 9. 人工审批 Action 设计

`openai-agents-python` 的 HITL 映射到 ANIFORCE：

```text
SDK interruption
  -> agent_task_actions(status=pending)
  -> run.status = requires_action
  -> persist result.to_state() as run_state_json
  -> frontend action button
  -> POST /actions/{id}/respond
  -> load RunState
  -> state.approve/reject
  -> Runner.run_streamed(agent, state)
```

注意：

```text
审批不是新 user turn
审批后要恢复原 top-level agent
stream 要重新 drain 到结束
同一个 SDK session 要继续传入
```

第一阶段可先不启用 SDK `needs_approval`，但 `agent_task_actions` 模型和 API 要按这个最终形态设计。

---

## 10. 工具与 Artifact 设计

### 10.1 工具先做 Python function_tool

首批工具：

```text
project.list_projects
project.create_project_draft
material.list_assets
campaign.list_campaigns
campaign.create_draft_plan
monitor.get_latest_metrics
session.set_title
session.output_task_result
session.propose_action
```

### 10.2 写操作先 proposal

```text
create_project_draft       可创建 draft artifact
create_draft_plan          可创建 campaign_draft artifact
apply_campaign_to_platform 第一阶段不做真实执行
pause_campaign             第一阶段必须 needs_approval 或不开放
```

### 10.3 Artifact 是业务事实

聊天消息只是解释，artifact 才是右侧 Workspace 的事实来源：

```text
project_draft
campaign_draft
creative_brief
analysis_report
diagnostic_report
data_table
chart_snapshot
```

工具输出要写：

```text
agent_artifacts
agent_events.artifact.created
current_task.artifacts
```

---

## 11. 前端 Home 工作区

### 11.1 产品方向

旧项目 `home-first-ai-workspace-plan.md` 的判断继续成立：

```text
Home = Agentic Creation Workspace
Conversation + Live Workspace + Embedded Task State
```

不是：

```text
纯聊天页
AgentDemo
右侧假任务卡
从 assistant 文本猜状态
```

### 11.2 第一阶段前端范围

先做最小接入：

```text
frontend/packages/main-app/src/api/agent.ts
frontend/packages/main-app/src/composables/useAgentSession.ts
frontend/packages/main-app/src/components/agent/ChatWindow.vue
frontend/packages/main-app/src/components/agent/ChatInput.vue
frontend/packages/main-app/src/components/agent/LiveWorkspaceShell.vue
```

Home 使用：

```text
Conversation 左侧
LiveWorkspaceShell 右侧
```

### 11.3 前端状态原则

```text
messages 来自 agent_messages / events
workspace 来自 current_task / artifacts / snapshot
actions 来自 pending_actions
run state 来自 latest_run / events
```

不要：

```text
根据 messages.length 猜任务阶段
根据 SSE open/close 猜 run 是否完成
把 tool result 只渲染成聊天文本
```

---

## 12. Block 开发顺序

### Block 0：文档与基线

当前文档即本 Block 输出。

验收：

```text
明确端口 18003/13003
明确后端内嵌 Agent
明确普通对话不进异步队列
明确业务 Task 才进入 Task/Run/Worker 模型
明确 SDK session 策略
明确旧项目只做能力映射
```

### Block 1：后端 SDK 基线

目标：后端内嵌 `openai-agents-python` 最小可运行。

改动：

```text
backend/requirements.txt                  # openai-agents
backend/app/agents/assistant.py
backend/app/agents/runtime.py
backend/app/api/v1/agent.py               # health
backend/app/schemas/agent.py
```

验收：

```bash
cd backend
UV_CACHE_DIR=./uv_cache uv run python -m compileall app
curl http://127.0.0.1:18003/api/v1/agent/health
```

### Block 2：普通 Chat Stream

目标：先跑通低延迟普通对话，不引入业务 Task/Run/Worker。

接口：

```text
POST /api/v1/agent/chat/sessions
POST /api/v1/agent/chat/sessions/{chat_session_id}/stream
GET  /api/v1/agent/chat/sessions/{chat_session_id}/messages
```

验收：

```text
用户发送普通问题
backend 调 Runner.run_streamed()
前端收到 message_delta
stream 结束后有 final assistant message
同一 chat_session_id 能延续多轮上下文
不创建 business task
不返回 queued
```

### Block 3：Chat Persistence / Session Memory

目标：把普通对话的消息历史、SDK session、usage 记录稳定下来。

能力：

```text
chat_sessions / chat_messages 或复用现有对话表
SDK SQLiteSession 文件落在 runtime/agent/sdk-sessions
assistant final message 合并入库
delta 不高频入库，避免 SQLite locked
usage / last_response metadata 可记录
```

### Block 4：Business Task Kernel

目标：业务目标才进入 `Task/Run/Event/Action/Artifact`。

验收样例：

```text
用户：帮我创建 Meta 测试投放计划，预算每天 500 美金
backend 创建 task/run(execution_mode=inline)
写 task.created/run.created/tool/artifact/action 事件
GET /api/v1/agent/tasks/{id}/snapshot 返回 current_task
```

### Block 5：Task Stream / Artifact / Action

目标：业务 task inline 执行时，能产生 workspace 需要的结构化事实。

能力：

```text
Runner.run_streamed() 可用于 task 执行
工具输出写 artifact，不只写聊天文本
pending action 写 agent_task_actions
SDK interruption -> RunState -> action 的映射预留
```

### Block 6：Home Live Workspace

目标：前端不再只是聊天。

验收场景：

```text
帮我创建 Meta 测试投放计划，预算每天 500 美金
  -> 左侧显示对话解释
  -> 右侧显示 campaign_draft artifact
  -> timeline 显示 task phase
  -> action 可响应
```

### Block 7：Task Abort / Timeout / Recovery

目标：不要让业务 task 的 running run 永久悬挂。

能力：

```text
process-local running task registry
abort endpoint 对 task run 调 cancel
timeout scanner 手动脚本
迟到 completion 幂等忽略
```

### Block 8：DB-backed Task Worker

目标：只有业务 task 执行和长工具进入 worker。

验收：

```text
POST /api/v1/agent/tasks/{task_id}/runs 返回 queued=true
worker claim task run
worker 消费 Runner.run_streamed()
前端通过 task events/snapshot 看到状态变化
worker 未启动时前端显示 queued/等待派发
普通 chat stream 不受 worker 影响
```

### Block 9：工具治理与 Artifact Contract

目标：工具不是随便调用，输出不是纯文本。

验收：

```text
工具调用写 tool_call + events
写操作默认 proposal/draft
artifact 可恢复右侧 workspace
```

### Block 10：Auth / Tenant / Cost / Deployment

目标：生产化。

能力：

```text
ownership 校验
AI call log
trace/cost/latency
Docker Compose
Nginx SSE config
readiness/migration check
```

---

## 13. 第一轮真正动手清单

第一轮只做 Block 1 + Block 2 的最小后端闭环，不碰 worker、不碰复杂数据库、不改造全站前端：

1. 检查端口：

```bash
ss -ltnp | grep -E ':(13003|18003)\b' || true
```

2. 后端依赖：

```text
backend/requirements.txt 增加 openai-agents
```

3. 最小后端文件：

```text
backend/app/agents/__init__.py
backend/app/agents/assistant.py
backend/app/agents/runtime.py
backend/app/schemas/agent.py
backend/app/api/v1/agent.py
backend/app/api/v1/router.py
```

4. 最小接口：

```text
GET  /api/v1/agent/health
POST /api/v1/agent/chat/sessions
POST /api/v1/agent/chat/sessions/{chat_session_id}/stream
```

5. 校验：

```bash
cd /workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE/backend
if [ ! -d ".venv" ]; then UV_CACHE_DIR=./uv_cache uv venv --python 3.11; fi
UV_CACHE_DIR=./uv_cache uv pip install -r requirements.txt
UV_CACHE_DIR=./uv_cache uv run python -m compileall app
```

6. 如果要启动服务：

```bash
UV_CACHE_DIR=./uv_cache uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 18003
```

7. 健康检查：

```bash
curl http://127.0.0.1:18003/health
curl http://127.0.0.1:18003/api/v1/agent/health
```

8. 有 `OPENAI_API_KEY` 时验证普通聊天流：

```bash
curl -N -X POST http://127.0.0.1:18003/api/v1/agent/chat/sessions/<chat_session_id>/stream \
  -H 'Content-Type: application/json' \
  -d '{"message":"用一句话说明 ANIFORCE 是什么"}'
```

---

## 14. 当前不做

```text
不创建独立 agent-service
不使用 18004
不把普通聊天放进异步队列
不引入 Redis 队列
不引入 Celery/Temporal/DBOS
不改造全站前端
不做 Docker Compose
不接真实投放写操作
不使用 OpenAI server-managed conversation_id
不让业务 Task 执行依赖前端连接
```

这些不是不要，而是排到后续 Block。

---

## 15. 风险和注意事项

1. **普通对话和业务 Task 混淆会导致系统过重**
   - 普通 chat turn 直接流式完成，只有业务目标才建 task/run。

2. **SDK stream 没 drain 完会导致结果不完整**
   - 对普通 chat，请求内 drain 到结束。
   - 对业务 task，inline/worker 都必须 drain 到结束或明确 cancel/requires_action。

3. **自动 compaction 可能拖慢 streaming 完成**
   - 第一阶段不要启用复杂 compaction。

4. **SQLite 高频 token 入库会锁库**
   - delta 实时推送，最终 assistant message 合并入库。

5. **前端断线恢复不能靠消息猜**
   - chat 用 `after_message_id`。
   - task 用 `after_sequence`。

6. **审批恢复不是新用户消息**
   - 用 `RunState` 恢复原 task run。

7. **队列化后不能重复执行已进入 SDK stream 的 task run**
   - claim/recovery 必须区分 runtime_started。

8. **OpenAI tracing 可能包含敏感数据**
   - 默认生产配置 `trace_include_sensitive_data=false`。

9. **旧项目脚本有自动清端口行为**
   - 新 ANIFORCE 脚本不照搬，未经确认不 kill。

---

## 16. 结论

现在的动手顺序应该是：

```text
1. 固定端口与后端 uv 环境
2. 后端内嵌 openai-agents-python health
3. 普通 chat stream 跑通，不进队列
4. chat session/message persistence 稳定
5. 再做 business task kernel
6. task inline 产生 artifact/action/current_task
7. 前端 Home 展示 Live Workspace
8. 只有业务 task 再引入 DB-backed worker
9. 再补工具治理、artifact、权限、成本、部署
```

这条路线既承认旧项目的 Block 资产，也不被旧 SDK/旧 agent-service 架构绑架；先让新 SDK 的普通对话在 ANIFORCE 后端内跑稳，再把业务 Task 平台能力一块块恢复回来。

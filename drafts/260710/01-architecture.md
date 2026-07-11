# 01 三端目标架构

## 1. 事实归属

| 状态                    | 权威服务      | 持久位置                |
| ----------------------- | ------------- | ----------------------- |
| 产品 Session            | Backend       | control DB              |
| Run 生命周期            | Backend       | control DB              |
| 用户可见消息            | Backend       | control DB              |
| ToolCall 与副作用       | Backend       | control DB              |
| Approval                | Backend       | control DB              |
| Workspace Artifact      | Backend       | control DB/对象存储     |
| 关键 Run Event          | Backend       | control DB              |
| SDK Session items       | Agent Service | runtime DB              |
| SDK RunState checkpoint | Agent Service | runtime DB              |
| 页面选中项、未提交输入  | Frontend      | 内存，可选 localStorage |

Agent runtime DB 不得成为产品消息或审批的唯一来源。Frontend store 不得成为 active run、approval 或 artifact 的唯一来源。

## 2. Backend 运行模型

```text
API worker
  POST /runs
    -> 短事务创建 queued run、用户消息、run.created event
    -> 返回 run_id

Run worker
  -> CAS claim queued/interrupted run
  -> 获取 session lease
  -> 调 Agent Runtime
  -> 持久化 message/tool/approval/artifact/terminal facts
  -> 更新 heartbeat
  -> 释放 lease

SSE API worker
  -> 查询 run_events(after_sequence)
  -> SQLite 阶段短轮询
  -> buffer 缺失时要求客户端重拉 snapshot

Reconcile worker
  -> 回收过期 lease
  -> 收敛 stale running
  -> 过期 approval/checkpoint
  -> 对账 run/session/tool side effect
```

API 请求不得用 `asyncio.create_task()` 持有 run 所有权。`AgentRunEventBus` 可短期保留为低延迟优化，但不能决定 replay、sequence 或终态。

## 3. Agent Service 运行模型

Agent Service 负责：

- 创建 SDK Agent 和 MCP 连接；
- 构建当前 `WorkspaceRunContext`；
- 执行 `Runner.run_streamed`；
- 标准化 SDK 事件；
- 序列化/加载 RunState；
- 保存 runtime checkpoint 和 SDK session items。

Agent Service 不负责：

- 产品 run 最终状态；
- 用户可见历史；
- Approval 权威状态；
- Workspace artifact；
- 业务幂等和副作用事实。

`_ACTIVE_RUNTIME_RUNS` 只能加速同进程取消。取消事实来自 Backend 的 `cancel_requested`，正确性不能依赖该 dict。

# 4. Frontend 运行模型

Frontend 启动或刷新时先请求：

```text
GET /sessions/{session_id}/snapshot
```

返回 messages、latest run、pending approval、artifacts 和 last persisted sequence。若 run 仍活跃，再连接：

```text
GET /runs/{run_id}/events?after_sequence=N
```

Frontend 仅渲染服务端 artifact，不再通过多个 tool event 的到达顺序猜测 Workspace projection。

## 5. 代码目录目标

先建立目录和接口，再按纵向链路迁移；不要一次移动全部文件。

```text
backend/app/agent/
  api/                 # sessions, runs, approvals, artifacts
  domain/              # states, events, errors, transition rules
  application/         # run, approval, session, artifact, reconcile
  infrastructure/
    sqlite/            # repository, lease, event store
    runtime_client.py
  workers/             # run worker, reconcile worker

aniforce-agent/app/
  api/                  # runtime runs/sessions/checkpoints
  runtime/              # executor, context, SDK adapter, event mapper
  tools/                # MCP, backend client, tool errors
  infrastructure/sqlite/

frontend/packages/main-app/src/agent/
  api/
  protocol/             # event types + pure reducers
  runtime/              # connection manager + run controller
  messages/
  approvals/
  workspace/
```

## 6. Backend service 收敛

| 当前文件                         | 目标                                    |
| -------------------------------- | --------------------------------------- |
| `agent_routes.py`              | 拆成薄 API，不再执行后台任务            |
| `agent_run_service.py`         | 收敛为唯一 Run application service      |
| `agent_run_event_processor.py` | 纯 runtime event translator/reducer     |
| `agent_run_event_bus.py`       | 被持久 event repository 替代            |
| `session_lock.py`              | 被 DB session lease 替代                |
| `agent_gateway.py`             | 改为纯`RuntimeClient`                 |
| `chat_event_assembler.py`      | 保留为纯协议函数或并入 event mapper     |
| `session_state_mutation.py`    | 拆为 context、snapshot、business change |
| `side_effect_service.py`       | 并入 ToolCall/BusinessChange 事实层     |

文件数不是指标。验收指标是：一个状态只有一个 owner，一个状态迁移只有一个入口。

## 7. 多 worker 启用门槛

Backend 多 worker 前必须具备：持久 run event、DB sequence、run/session lease、heartbeat、reconcile、snapshot 和故障测试。

Agent 多 worker 前必须具备：共享 runtime DB、checkpoint CAS、过期校验、SDK session 单 session 串行、恢复时重建 context 和版本兼容检查。

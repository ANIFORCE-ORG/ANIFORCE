# ANIFORCE Agent 代码库重构迁移手册

日期：2026-07-11  
适用基线：`docs/sqlite-multiworker-refactor-260710` / `99a99c7`  
目标：在不降低现有能力、不修改外部协议的前提下，收敛代码职责、状态归属和依赖方向，删除经过验证的冗余路径。

---

## 1. 使用原则

本次是结构迁移，不是产品功能迭代。每一阶段都必须满足：

1. 先冻结行为，再移动代码。
2. 一次只改变一个边界，不同时重写 Backend、Agent Service 和 Frontend。
3. 先建立新入口并双跑验证，再删除旧入口。
4. 数据库、HTTP、SSE、MCP 协议默认不可变化。
5. 每个阶段独立提交、独立验证、可用单个 `git revert` 回滚。
6. 不以文件数量或行数为目标，以“一个状态一个 owner、一个迁移一个入口”为验收标准。
7. 不顺手格式化、不调整 UI、不升级依赖、不修改 Prompt 行为。

### 1.1 禁止变化的能力

- 创建、查询、归档和删除 Agent Session。
- 创建、查询、取消和恢复 Run。
- reasoning、text delta、tool called/output 的实时流式体验。
- Redis 不可用时 Run 继续执行、事实继续落库、客户端可获得最终结果。
- requires_action、approve、reject、resume 和 checkpoint 恢复。
- ToolCall 从 interruption 到最终执行结果使用同一个审计 ID。
- Session snapshot 刷新恢复消息、活动 Run、审批和 Workspace Artifact。
- 多 Backend worker 的 claim、lease、heartbeat 和 reconcile。
- Agent runtime checkpoint、SDK session ownership 和多 worker 防护。
- 当前 MCP 工具名称、参数 Schema、返回结构和审批策略。
- 当前 HTTP 路径、状态码、SSE event name 和主要 payload 字段。

### 1.2 明确的状态归属

| 状态 | 唯一 owner | 持久位置 |
| --- | --- | --- |
| Product Session | Backend | control DB |
| Run 生命周期 | Backend Run application service | control DB |
| Approval | Backend Approval service | control DB |
| 用户可见 Message | Backend Message projection | control DB |
| ToolCall / Side effect | Backend Tool audit service | control DB |
| Workspace Artifact | Backend Artifact service | control DB / object storage |
| 关键 Run Event | Backend | control DB |
| 短期 delta | Redis transport | Redis Stream，非事实源 |
| SDK session items | Agent Service | runtime DB |
| SDK RunState checkpoint | Agent Service | runtime DB |
| 页面临时输入和选择 | Frontend | memory / optional localStorage |

---

## 2. 当前问题清单

### 2.1 Backend

- `backend/app/api/v1/agent_routes.py` 同时承担 HTTP、SSE、应用编排、运行消费、状态迁移和事实持久化。
- `backend/app/agent/run_worker.py` 反向导入 API 私有函数 `_consume_agent_run_background`。
- SQLite durable events、Redis transient stream、`AgentRunEventBus` 三套事件机制并存。
- Run 状态可由 Route helper、EventProcessor、Worker、Reconcile 等多个入口修改。
- `_persist_run_output_short_tx` 同时投影 Message、ToolCall、Artifact 和 Session 状态。
- `agent_routes.py` 中大量 `_with_session` helper 隐藏事务边界，难以确认原子性。

### 2.2 Agent Service

- `app/agent/runtime.py` 混合新 Run、恢复 Run、MCP context、event mapping 和 checkpoint。
- `app/mcp_server.py` 混合 context、审批参数处理及 project/campaign/material 三个业务域。
- 工具调用共用大量 headers、approved arguments 和 backend request 样板，但缺少清晰的基础层。

### 2.3 Frontend

- `useAgentSession.ts` 只是 `useHomeAgentSession.ts` 的转发别名，领域命名仍绑定 Home。
- Home 使用正式 Agent/Workspace 链路，ProjectDetail 和 CampaignDetail 仍使用旧 `ChatPanel`。
- `AgentShell + ChatWindow` 与 `Home + MessageView` 形成重叠展示路径。
- event parsing、连接恢复、timeline 构建和 workspace hydration 集中在 1300 行 composable 中。
- 前端没有独立测试脚本，重构前缺少 reducer/协议保护。

---

## 3. 目标目录和依赖方向

先建立边界，不要求一次完成全部目录移动。

```text
backend/app/agent/
  api/                    # FastAPI transport，仅解析和响应
  application/            # run/session/approval application services
  domain/                 # state、transition、event、error
  infrastructure/         # sqlite repository、runtime client、redis stream
  projections/            # message/tool/artifact/session facts
  workers/                # run worker、reconcile worker

aniforce-agent/app/
  api/                    # runtime HTTP API
  runtime/                # executor、resume、event mapper、context
  tools/                  # MCP registry 和分域工具
  infrastructure/sqlite/  # runtime schema/session/checkpoint

frontend/packages/main-app/src/agent/
  api/                    # HTTP/SSE client
  protocol/               # types、parser、pure reducers
  runtime/                # connection manager、session controller
  messages/
  approvals/
  workspace/
```

依赖只能向内：

```text
API / Worker
  -> Application Service
    -> Domain rules
    -> Repository protocol / Runtime client / Event publisher
```

禁止：

- Worker 导入 API Route。
- Domain 导入 FastAPI、SQLAlchemy、Redis 或 Vue store。
- Repository 决定业务状态迁移。
- Redis 回调直接修改产品事实。
- Frontend 根据 tool event 到达顺序推断权威 Artifact。

---

## 4. 阶段 0：建立迁移基线

### 4.1 开工检查

```bash
git switch docs/sqlite-multiworker-refactor-260710
git pull --ff-only
git status --short
git log -1 --oneline
```

预期基线 commit 为 `99a99c7` 或其后续明确提交。`test-results/` 等本地产物不得混入重构提交。

### 4.2 修复测试环境

两个 Python 服务都使用顶层包名 `app`，禁止在同一 pytest 进程中混跑。分别执行：

```bash
cd backend
if [ ! -d ".venv" ]; then
  UV_CACHE_DIR=../uv_cache uv venv --python 3.11
fi
UV_CACHE_DIR=../uv_cache uv pip install -r requirements.txt -r ../aniforce-agent/requirements-dev.txt
UV_CACHE_DIR=../uv_cache uv run python -m pytest tests -q
```

```bash
cd aniforce-agent
if [ ! -d ".venv" ]; then
  UV_CACHE_DIR=../uv_cache uv venv --python 3.11
fi
UV_CACHE_DIR=../uv_cache uv pip install -r requirements.txt -r requirements-dev.txt
UV_CACHE_DIR=../uv_cache uv run python -m pytest tests -q
```

注意：Backend 当前没有独立 `requirements-dev.txt`。若确认长期需要，应新增该文件并仅放 pytest 等开发依赖；不要长期借用 Agent Service 的 dev requirements。

前端基线：

```bash
cd frontend
npm_config_cache=../npm_cache pnpm install
npm_config_cache=../npm_cache pnpm --filter main-app build
```

### 4.3 契约清单

重构前保存以下契约样本或自动化断言：

- `POST /api/v1/agent/runs`
- `GET /api/v1/agent/runs/{run_id}`
- `GET /api/v1/agent/runs/{run_id}/events?after_sequence=N`
- `GET /api/v1/agent/sessions/{session_id}/snapshot`
- `GET /api/v1/agent/runs/{run_id}/approvals`
- `POST /api/v1/agent/runs/{run_id}/approvals/{checkpoint_id}`
- `POST /api/v1/agent/runs/{run_id}/cancel`
- Agent Service run、resume、cancel 和 checkpoint API。
- 所有 MCP tool 的 name、input schema、approval requirement。
- SSE event name、terminal event 和 sequence 行为。

### 4.4 建议新增测试

- Redis 正常发布和 `after_sequence` replay。
- Redis 连接失败时 durable fallback。
- Redis TTL 过期后 snapshot + persisted event 恢复。
- approve/reject 后 ToolCall 审计 ID 不变化。
- Worker lease 丢失时不得写入 terminal state。
- 同一个 Session 不允许两个 active Run。
- Run completed 后重复 runtime.completed 幂等。
- Frontend event parser 和 reducer 的纯函数测试。

验收门槛：当前测试全部通过，新增契约测试先对旧实现通过。

提交建议：

```text
test(agent): freeze runtime and streaming contracts
```

---

## 5. 阶段 1：迁出 Backend Run Executor

这是第一优先级，先修复依赖方向，不改变执行行为。

### 5.1 新增组件

建议新增：

```text
backend/app/agent/run_executor.py
```

定义：

```python
class AgentRunExecutor:
    async def execute(self, command: ExecuteRunCommand) -> None:
        ...
```

`ExecuteRunCommand` 至少包含当前 `_consume_agent_run_background` 的参数：

- run_id
- session_id
- user_id
- authorization
- agent payload
- changelog start index
- lease owner
- resume payload

依赖通过构造函数注入：

- Runtime client / `AgentGatewayService`
- session maker
- transient publisher
- application services / projections

### 5.2 迁移顺序

1. 原样复制 `_consume_agent_run_background` 到 `AgentRunExecutor.execute`。
2. 第一提交只调整调用位置，不重写内部逻辑。
3. `run_worker.py` 改为依赖 `AgentRunExecutor`。
4. Route 若仍需要同步调用，也依赖同一个 Executor。
5. 删除 `run_worker.py -> agent_routes.py` 的导入。
6. 测试 monkeypatch 从 route 私有函数迁到 executor 实例。

### 5.3 验收

- `rg "from app.api.v1.agent_routes" backend/app/agent backend/app/services` 无结果。
- API Route 不再拥有 Agent 流消费循环。
- Run 的成功、失败、取消、requires_action 行为不变。
- Redis 和 durable facts 的发布顺序不变。

提交建议：

```text
refactor(agent): extract backend run executor
```

回滚：直接 revert 本提交，无数据库变化。

---

## 6. 阶段 2：集中 Run 状态迁移

### 6.1 建立领域状态规则

新增纯领域模块：

```text
backend/app/agent/domain/run_state.py
```

显式允许的迁移：

```text
queued          -> running | cancelled
running         -> requires_action | completed | error | cancelled
requires_action -> queued(resume) | cancelled
```

`completed`、`error`、`cancelled` 为终态，不允许被普通事件覆盖。恢复和 reconcile 的特殊迁移必须有具名方法，禁止散落 SQL。

### 6.2 收敛 Application Service

`AgentRunService` 成为唯一写入口，提供明确方法：

- `enqueue_run`
- `claim_run`
- `mark_running`
- `require_action`
- `enqueue_resume`
- `complete_run`
- `fail_run`
- `request_cancel`
- `confirm_cancelled`
- `recover_stale_run`

Repository 只提供原子 CAS、查询和保存，不决定“是否应该迁移”。

### 6.3 替换位置

- `agent_routes.py` 的 `_mark_run_status_short_tx`。
- `AgentRunEventProcessor` 的直接状态修改 callback。
- Worker 的 resume 后状态处理。
- Reconciliation 的直接状态更新。

### 6.4 验收

- 除 migration/repository 外，业务代码不直接写 `agent_runs.status`。
- 所有非法迁移返回统一错误码或 no-op 结果。
- 重复 terminal event 幂等。
- cancel 与 complete 并发结果符合既有 fencing 规则。

提交建议：

```text
refactor(agent): centralize run state transitions
```

---

## 7. 阶段 3：删除进程内 AgentRunEventBus

### 7.1 最终事件模型

只保留两类通道：

1. Durable event repository：关键事实、恢复、审计。
2. Redis transient stream：实时 delta 和跨进程订阅。

Redis 不可用时，SSE 使用 durable event + Run snapshot 降级。不得由内存对象决定 sequence 或 terminal。

### 7.2 改造 EventProcessor

将 `AgentRunEventProcessor` 改为纯翻译器或 reducer，不发布、不建事务：

```python
result = processor.reduce(current_run, runtime_event)
```

返回值包含：

- proposed transition
- durable facts
- transient events
- terminal / requires_action 标识

Executor 根据结果调用 Application Service 和 publisher。

### 7.3 删除顺序

1. 移除 Processor 对 `AgentRunEventBus` 的依赖。
2. 移除 Executor 对 `agent_run_event_bus.publish` 的调用。
3. 移除 Worker 的 `create_run`。
4. 迁移依赖 EventBus 的测试。
5. `rg` 确认零引用后删除 `agent_run_event_bus.py`。

### 7.4 验收

- 多 worker 下任意 API worker 均可订阅活动 Run。
- Redis 关闭时 Run 不失败，最终状态和 Message 正常。
- Redis 重启后新事件可继续发布。
- durable sequence 和 transient sequence 的含义在文档中明确，前端不混用二者作为同一游标。
- `rg "AgentRunEventBus|agent_run_event_bus" backend` 仅允许历史文档出现。

提交建议：

```text
refactor(agent): remove in-memory run event bus
```

---

## 8. 阶段 4：拆分产品事实投影

将当前聚合持久化逻辑拆为小而明确的服务：

```text
backend/app/agent/projections/
  message_projection.py
  tool_audit.py
  approval_projection.py
  workspace_artifact.py
  session_settlement.py
```

### 8.1 约束

- 每个投影必须幂等。
- 投影服务接收标准化事件，不解析 HTTP/SSE 字节。
- ToolCall started/completed/rejected 使用同一 `tool_call_id`。
- Message 只在 terminal 或明确的 message event 上生成一次。
- Artifact 以服务端持久事实为准。
- Session settlement 必须在 Run terminal fact 成功后执行。

### 8.2 事务策略

- 同一事实内必须原子完成的写操作使用一个短事务。
- 网络调用不允许放在数据库事务内。
- 不为“减少 session 数量”扩大事务。
- 每个服务方法写明输入事实、幂等键和事务边界。

### 8.3 验收

- `_persist_run_output_short_tx` 被删除或退化为薄 orchestration。
- 每类事实都有独立单元测试。
- 重放相同 terminal events 不产生重复 Message、ToolCall 或 Artifact。

提交建议：

```text
refactor(agent): split durable fact projections
```

---

## 9. 阶段 5：拆分 Backend API

Executor 和 Application Service 稳定后，再拆 Route：

```text
backend/app/agent/api/
  sessions.py
  runs.py
  approvals.py
  events.py
  schemas.py
  dependencies.py
```

原 URL prefix 和 OpenAPI contract 保持不变。旧 `agent_routes.py` 可先作为 router aggregator，确认所有引用迁移后再删除。

每个 handler 只允许：

1. 解析输入。
2. 鉴权。
3. 调用一个 application use case。
4. 转换已知领域错误。
5. 返回响应。

验收：单个 route handler 不创建后台任务、不直接使用 Repository、不处理 Runtime SSE 字节。

提交建议：

```text
refactor(agent): split backend transport routes
```

---

## 10. 阶段 6：收敛 Agent Service Runtime

### 10.1 拆分 runtime.py

建议按职责迁移：

```text
aniforce-agent/app/runtime/
  executor.py
  resume_executor.py
  event_mapper.py
  mcp_context.py
  checkpoint_service.py
  session_service.py
```

迁移次序：

1. 先提取无状态 event mapper。
2. 再提取 MCP connection/context builder。
3. 再提取 checkpoint service。
4. 最后分离 new run 与 resume executor。

不要改变 SDK `Runner` 配置、ModelSettings、Prompt、stream event name 或 checkpoint 格式。

### 10.2 拆分 MCP 工具

```text
aniforce-agent/app/tools/
  context.py
  approval.py
  projects.py
  campaigns.py
  materials.py
  registry.py
```

- `context.py`：meta、token、headers、tool_call_id。
- `approval.py`：approved arguments 获取、校验和 argument diff。
- 各业务文件：工具 Schema 和 Backend 调用。
- `registry.py`：向 MCP server 注册，保持工具名不变。

### 10.3 契约保护

迁移前后对工具列表生成快照并比较：

- tool name 完全相同。
- required/optional 参数完全相同。
- description 不应无意变化。
- approval-required 工具集合完全相同。
- 同一模拟 Backend 响应产生相同工具结果。

提交建议拆成两个：

```text
refactor(runtime): split execution services
refactor(runtime): split mcp tools by domain
```

---

## 11. 阶段 7：统一 Frontend Agent 控制器

### 11.1 先提取纯协议层

从 `useHomeAgentSession.ts` 提取：

```text
frontend/packages/main-app/src/agent/protocol/
  events.ts
  parser.ts
  reducer.ts
  timeline.ts
```

这些模块不得导入 Vue component、router 或 Pinia store。先为以下行为建立测试：

- text/reasoning delta 合并。
- tool called/output 配对。
- terminal event 收敛。
- requires_action 展示。
- snapshot hydration。
- reconnect 后事件去重。

如需新增前端测试框架，优先使用 Vitest，与 Vite 技术栈一致；只增加必要依赖。

### 11.2 建立统一控制器

将 `useHomeAgentSession` 收敛为领域无关的 `useAgentSessionController`：

- route context 作为输入。
- Session、Run、connection、approval 分开管理。
- 页面只组合 controller 暴露的 state/actions。
- `useAgentSession.ts` 可临时 re-export，迁移完成后删除兼容层。

### 11.3 页面迁移顺序

1. Home 继续使用新控制器，确保行为无变化。
2. ProjectDetail 从 `ChatPanel` 迁到统一控制器。
3. CampaignDetail 从 `ChatPanel` 迁到统一控制器。
4. 核对 `AgentShell + ChatWindow` 的真实路由引用。
5. 零引用且浏览器验证通过后删除旧组件。

### 11.4 验收

- 全站只有一个 SSE connection manager。
- 全站只有一套 reconnect/snapshot 恢复逻辑。
- Home、Project、Campaign 场景共享同一消息和审批 reducer。
- 页面业务上下文仍正确传给 Backend。
- 桌面和移动视口无布局回归。

提交建议：

```text
refactor(frontend): extract agent protocol reducers
refactor(frontend): unify agent session controller
refactor(frontend): remove legacy chat path
```

---

## 12. 阶段 8：清理其他遗留模块

该阶段不得与 Agent 核心迁移混在同一提交。

候选项：

- `platform_auth.py` 按 provider、OAuth flow、token persistence 拆分。
- `CreateAdUnitModal.vue`、`CreateCampaignModal.vue` 提取 form model、API orchestration 和小组件。
- `Material.vue` 分离 query state、selection、upload 和 display。
- 评估 `DEMO_MODE`、MockRepository、MockClient 是否仍为正式产品能力。
- 清理不可达的 HTML prototype、旧启动脚本、重复文档和无引用组件。

### 12.1 删除证据表

删除任何候选项前记录：

| 项目 | 要求 |
| --- | --- |
| 静态引用 | `rg` 为零或仅剩明确兼容入口 |
| 路由可达性 | 不在 router/navigation/import graph 中 |
| 配置使用 | 本地、云端 env 均未启用 |
| 测试依赖 | 测试不再 patch/import 该路径 |
| 数据兼容 | 不删除仍需读取的字段和 migration |
| 运行验证 | E2E 和浏览器验证通过 |

无法满足任一项时，标记 deprecated 并延后一个发布周期，不直接删除。

---

## 13. 重构 Coding 规范

本章是重构代码的合入标准，不是风格建议。违反边界规则的代码即使功能可用，也不应合入。

### 13.1 可读性的判断标准

一段合格代码应让首次阅读者快速回答：

1. 这个模块负责什么？
2. 它明确不负责什么？
3. 输入、输出和副作用是什么？
4. 状态由谁拥有、在哪里持久化？
5. 失败如何表达，调用者如何处理？
6. 重试会不会重复写入或产生重复副作用？

如果必须跨越多个 Route、Service、Repository 和全局变量才能回答，说明边界仍未建立。

### 13.2 模块职责

- 一个模块只围绕一个变化原因组织，而不是围绕“相关功能”无限聚合。
- API 只处理 transport；Application Service 编排 use case；Domain 表达规则；Infrastructure 处理外部技术细节。
- Worker 是 application use case 的触发器，与 HTTP Route 地位相同，不能依赖 Route。
- Repository 只负责持久化和原子 CAS，不决定业务流程。
- Parser、mapper、reducer 优先写成无 IO 的纯函数。
- 文件名称必须表达业务职责，禁止新增 `utils.py`、`helpers.py`、`common.py`、`manager.py` 作为杂物容器。
- 不按行数机械拆文件；当一个文件存在两个独立变化原因、两个 owner 或两个副作用边界时才拆。

每个核心模块顶部用简短 docstring 说明：

```python
"""Translate runtime events into domain outcomes without performing IO."""
```

不要写“提供 Agent 相关功能”这类无法形成边界的描述。

### 13.3 依赖规则

允许的依赖方向：

```text
transport / worker -> application -> domain
                                  -> ports(protocols)
infrastructure --------------------^ implements
```

- Domain 禁止导入 FastAPI、SQLAlchemy、Redis、HTTP client 或具体 Repository。
- Application 依赖 Protocol，不依赖 `Sqlite*Repository` 等实现类。
- Infrastructure 可以依赖 Domain 类型，但不能反向调用 API。
- 禁止为了绕过边界在函数内部临时 import 上层模块。
- 禁止新增隐式 service locator 和可变全局单例。
- 依赖优先通过构造函数注入；仅稳定、无状态、无外部资源的纯函数可直接导入。
- 出现循环依赖时先检查职责归属，不用延迟 import 掩盖设计问题。

### 13.4 抽象门槛

抽象必须降低认知成本，而不是增加层数。

允许新增抽象的条件至少满足一项：

- 隔离明确的外部系统边界，例如 Runtime、Redis、Database。
- 统一一个业务不变量，例如 Run transition。
- 消除三处以上且会共同变化的重复逻辑。
- 为测试替换真实副作用提供稳定接口。

禁止：

- 只有一个实现且没有边界价值的 Interface + Impl 套壳。
- 只调用下一层同名方法的空 Service。
- “未来可能需要”驱动的参数、策略、工厂和插件系统。
- 用 `BaseManager`、`GenericService`、`CommonProcessor` 隐藏不同业务语义。
- 为追求 DRY 合并只是表面相似、业务不变量不同的流程。

优先顺序：纯函数 > 具名数据结构 > 小型领域服务 > Protocol > 框架级抽象。

### 13.5 命名规则

- 名称表达领域意图，不表达模糊技术动作。
- Command 使用动词：`enqueue_run`、`resolve_approval`、`complete_tool_call`。
- Query 使用读取语义：`get_run`、`list_pending_approvals`。
- 布尔值使用 `is_`、`has_`、`can_`、`should_`。
- 事件使用已经发生的事实：`run.completed`，不要使用含糊的 `handle_done`。
- 同一概念全仓统一用词：只使用 Run，不混用 task/job/execution 指代同一对象。
- `data`、`info`、`item`、`result` 只允许在极小局部作用域使用；跨层参数必须具名。
- 禁止用 `new`、`old`、`v2`、`temp` 表达长期模块。迁移兼容代码必须带删除条件和截止阶段。
- 私有函数不是架构边界；被跨模块调用的能力必须成为正式公开接口。

### 13.6 函数和控制流

- 一个函数只处于一个抽象层级，不同时解析 SSE、判断业务状态并写数据库。
- 公共函数优先使用具名 command/result dataclass，避免持续增长的位置参数和松散 dict。
- 正常主路径保持左对齐，使用 guard clause 处理失败和特殊条件。
- 避免深层嵌套；超过三层通常应提取具名步骤或重新划分职责。
- 不使用布尔参数切换两个不同流程，例如 `execute(resume=True)`；使用 `execute_run` 和 `resume_run` 或具名 command。
- 不用异常控制正常业务分支；冲突、拒绝、过期使用明确领域结果或领域异常。
- 不捕获裸 `Exception` 后静默继续。边界兜底必须记录结构化上下文，并返回明确失败结果。
- 注释解释“为什么”和不变量，不复述代码。复杂流程优先通过命名和类型表达。

建议的 application method 形态：

```python
async def complete_run(self, command: CompleteRun) -> CompleteRunResult:
    current = await self.runs.get(command.run_id, command.user_id)
    transition = decide_completion(current, command)
    if transition.is_noop:
        return CompleteRunResult.from_existing(current)
    return await self.runs.compare_and_set(transition)
```

### 13.7 类型与数据边界

- 跨层数据禁止长期使用无约束的 `dict[str, Any]`。
- HTTP 输入输出使用 Pydantic schema；Domain 使用 dataclass/enum/value object；持久层负责映射。
- 外部输入在边界处一次性校验，内部代码不反复猜测字段是否存在。
- 标准化 Runtime event 后，内部层不再解析原始 SSE payload。
- 时间统一使用带时区 UTC；展示层再转换时区。
- ID 在同一链路中保持原值和语义，不重新生成“看起来一样”的 ToolCall ID。
- `None`、空字符串、空列表必须有清晰且一致的领域含义。
- Enum/状态值集中定义，禁止散落字符串集合。

允许在协议适配边界保留原始 dict，但必须尽快转换：

```python
runtime_event = RuntimeEvent.from_payload(raw_payload)
```

### 13.8 状态与副作用

- 一个状态只能有一个权威 owner 和一个正式写入口。
- 所有状态迁移必须显式列出 expected state，并通过 CAS 或等价机制保护。
- 网络调用不得位于数据库事务中。
- 先持久化意图/事实还是先调用外部系统，必须按业务幂等策略明确设计，不能依赖运气。
- 写操作必须定义幂等键；Agent 工具默认以 `tool_call_id` 作为审计和去重依据。
- terminal fact、Message、ToolCall result、Artifact 投影都必须可重放且不重复。
- Redis、内存缓存和前端 store 不得成为产品事实唯一来源。
- 对同一副作用不得同时保留“旧路径”和“新路径”长期双写；双写只能用于有截止时间的迁移验证。

### 13.9 事务规范

每个写方法必须能明确回答事务包含哪些不变量。

- 事务尽可能短，只包含必须原子完成的数据库操作。
- Service 不隐藏无限嵌套事务；事务 owner 必须清楚。
- Repository 默认不自行 commit，由 use case 决定提交边界。
- CAS 失败不是数据库异常，而是业务并发结果。
- 不在循环内逐条提交可批量完成的同类事实。
- 不跨 Backend DB 和 Agent runtime DB 假装实现分布式事务；使用明确状态、幂等和 reconcile 收敛。

### 13.10 错误模型

错误分三类：

| 类型 | 示例 | 处理方式 |
| --- | --- | --- |
| Domain rejection | 非法状态迁移、审批过期 | 具名领域错误，稳定错误码 |
| Infrastructure failure | Redis/DB/Runtime 超时 | 记录上下文，按策略重试或降级 |
| Programmer error | 缺少必填字段、违反不变量 | 快速失败，不伪装成友好业务错误 |

- 错误码是协议，集中定义并测试。
- 日志记录内部原因；客户端只接收稳定、安全的信息。
- 降级必须明确降低了什么体验，不能吞掉正确性失败。
- Redis 失败允许失去实时 delta，不允许丢失 Run terminal fact。
- 错误日志至少包含 `run_id`、`session_id`、`user_id`、`checkpoint_id` 中适用的关联字段。
- 不在多个层重复记录同一异常堆栈；在能够决定处理策略的边界记录一次。

### 13.11 事件规范

- 事件名表示已经发生的事实，并集中定义。
- Durable event 和 transient event 分开建模，禁止共享含义不清的 sequence。
- event mapper 只做协议转换，不执行持久化和业务决策。
- terminal event 必须唯一、幂等、可通过数据库状态恢复。
- 消费者必须容忍重复事件，不能默认 exactly-once delivery。
- 新增事件前必须写清 producer、consumer、durability、ordering 和 replay 策略。
- 删除事件前先证明所有消费者已经迁移。

### 13.12 API 和工具契约

- Route handler 保持薄：解析、鉴权、调用 use case、映射错误、响应。
- Route 不直接拼接 SQL、不消费 Runtime stream、不创建后台 Run 任务。
- HTTP schema、SSE payload 和 MCP tool schema 必须有契约测试。
- MCP 工具函数负责领域参数和结果，不重复实现 Backend 权限与资金校验。
- 高风险写工具必须保留审批、超时和结构化错误处理。
- 兼容字段只能在 adapter 层处理，不能污染 Domain。
- 外部契约变化必须单独提交、记录迁移策略，不能混入内部重构。

### 13.13 Frontend 规范

- 协议 parser/reducer 写成纯 TypeScript，不依赖 Vue component。
- Component 只负责展示和用户交互；连接、恢复、去重不得散落页面。
- Pinia store 保存客户端状态，不复制服务端事实规则。
- 一个产品动作只有一个 controller action，页面不得直接绕过 controller 调 API。
- Workspace 只渲染服务端 Artifact；临时 delta 可以优化体验，但不能成为刷新后的唯一来源。
- 页面上下文以显式 `AgentRouteContext` 输入统一 controller，不复制聊天实现。
- 超大 Vue 文件按 form model、use case orchestration、可复用视图拆分，不把所有逻辑转移到另一个巨型 composable。
- 删除旧组件前验证 router、动态 import、模板引用和浏览器关键流程。

### 13.14 测试规范

测试保护业务不变量和外部契约，不保护内部函数形状。

- Domain transition 和 reducer 使用快速表驱动单元测试。
- Application Service 测试覆盖成功、冲突、重复、失败和重试。
- Repository 测试覆盖 CAS、并发、事务回滚和 migration。
- 契约测试冻结 HTTP、SSE、MCP schema。
- E2E 只覆盖关键纵向链路，不用 E2E 替代所有单元测试。
- 禁止为了完成重构而删除断言、扩大 mock 或只断言“没有抛异常”。
- Mock 应放在真正的外部边界；不要 mock 被测模块的内部实现步骤。
- 每个生产事故或迁移缺陷先增加失败测试，再修复。
- 测试名称表达场景和结果，例如 `test_repeated_completion_does_not_duplicate_message`。

### 13.15 日志与可观测性

- 使用结构化关联字段，不把关键 ID 只拼进 message。
- 一个 use case 至少可观察开始、终态、耗时和失败原因。
- 高频 delta 不逐条记录 info 日志，避免淹没关键生命周期事件。
- 日志不得包含 token、API key、完整 Prompt 或未经脱敏的工具结果。
- metrics/tracing 只能观察行为，不能成为业务正确性依赖。
- 重构不得无意改变现有 tracing span 和关键日志字段；确需调整时更新运维文档。

### 13.16 兼容代码与删除规则

任何兼容逻辑必须同时具备：

- 为什么存在。
- 服务哪个旧版本或数据。
- 何时可以删除。
- 用什么测试证明仍需要或可以删除。

建议格式：

```python
# Compatibility: runtime schema <= 3 may omit checkpoint_version.
# Remove after all deployed runtime DBs reach schema 5.
```

禁止永久保留无期限的 `legacy_*`、fallback chain 和双写路径。删除代码必须比新增代码更谨慎，但确认无 owner、无入口、无数据依赖后应彻底删除，不保留注释掉的实现。

### 13.17 Code Review 合入清单

每个重构 PR 必须逐项回答：

- [ ] 本次改变了哪个边界，为什么必须改？
- [ ] 哪些外部能力和协议明确保持不变？
- [ ] 状态 owner 和正式写入口是否唯一？
- [ ] 是否出现新的反向依赖、全局状态或 service locator？
- [ ] 新抽象是否隔离边界或表达不变量，而非仅增加层数？
- [ ] IO、事务和业务决策是否分离？
- [ ] 写操作是否定义幂等、并发和重试行为？
- [ ] 错误是否在正确层处理且保持稳定错误码？
- [ ] 测试是否保护行为而非当前实现细节？
- [ ] 是否存在可以随本次迁移删除的旧入口？删除证据是什么？
- [ ] diff 是否混入格式化、依赖升级、UI 或无关重命名？
- [ ] 是否可以用单个 commit revert，回滚后数据是否兼容？

### 13.18 代码质量的最终标准

“清爽”不是少写代码，“抽象”不是多建目录。目标代码应具备：

- 主流程短且直，异常路径明确。
- 领域名称贯穿 API、Service、Repository 和测试。
- 技术细节被隔离，但关键业务规则不被框架隐藏。
- 每个模块的依赖数量有限且方向稳定。
- 删除任一组件前能说明其消费者；修改任一状态前能定位唯一入口。
- 新开发者可以从 Route 或 Worker 沿单一调用链理解完整 Run 生命周期。
- 故障发生时，可以从持久事实恢复，而不是依赖进程内偶然状态。

真正高级的代码通常不炫技。它让复杂性有明确归属，让正确路径容易，让错误路径无法被忽略。

---

## 14. 每阶段统一验收模板

### 14.1 静态检查

```bash
git diff --check
git status --short
rg "from app.api.v1.agent_routes" backend/app/agent backend/app/services
rg "AgentRunEventBus|agent_run_event_bus" backend
```

后两项按当前阶段判断是否应为零。

### 14.2 Backend 测试

```bash
cd backend
UV_CACHE_DIR=../uv_cache uv run python -m pytest tests -q
```

重点测试：

```bash
UV_CACHE_DIR=../uv_cache uv run python -m pytest \
  tests/test_agent_run_background.py \
  tests/test_agent_run_event_processor.py \
  tests/test_agent_execution_fencing.py \
  tests/test_agent_phase1_recovery.py \
  tests/test_agent_approval_cas.py \
  tests/test_agent_tool_audit_semantics.py -q
```

### 14.3 Agent Service 测试

```bash
cd aniforce-agent
UV_CACHE_DIR=../uv_cache uv run python -m pytest tests -q
```

### 14.4 Frontend 验证

```bash
cd frontend
npm_config_cache=../npm_cache pnpm --filter main-app build
```

存在测试脚本后追加：

```bash
npm_config_cache=../npm_cache pnpm --filter main-app test
```

### 14.5 E2E 场景

至少人工或自动验证：

1. 普通对话完整流式输出。
2. 工具查询和 Workspace 投影。
3. 写工具触发审批，approve 后成功。
4. 写工具 reject 后不产生副作用，审计状态正确。
5. requires_action 页面刷新后可恢复。
6. Run 执行中刷新页面可重连。
7. Redis 停止后 Run 仍完成并可通过 snapshot 查看。
8. Backend 两 worker 下连续发起多个 Session Run。
9. Worker 中断后 reconcile 收敛或恢复。
10. ProjectDetail、CampaignDetail 的上下文对话正确。

---

## 15. Git 和回滚策略

### 15.1 分支建议

从当前留底分支创建独立重构分支：

```bash
git switch -c refactor/agent-boundaries-260712
```

### 15.2 提交纪律

- 每阶段一个或少量原子提交。
- 测试和相应迁移放在同一提交或紧邻前置提交。
- 禁止一个提交同时包含目录迁移、行为修改、依赖升级和 UI 调整。
- 提交前检查 `git diff --stat`，发现无关大 diff 立即拆分。

### 15.3 回滚

无 Schema 变化的阶段使用：

```bash
git revert <commit>
```

若后续确需 Schema 变化：

- 先提供兼容读取，再迁移写入，最后删除旧字段。
- 至少跨一个发布周期执行 expand/contract。
- SQLite 数据库已纳入 Git，但 Git 中数据库只能用于当前开发留底，不能替代正式 migration 和生产备份。

### 15.4 停止条件

出现以下情况立即停止当前阶段并回滚或修复，不继续叠加：

- HTTP/SSE/MCP 契约发生非预期变化。
- Run 出现双 terminal、重复 Message 或重复副作用。
- Redis 故障导致 Run 失败。
- approve/reject 后 ToolCall ID 断链。
- 多 worker 出现双执行。
- snapshot 无法恢复活动 Run 或审批。
- 测试只能通过放宽断言而无法解释行为差异。

---

## 16. 明日建议执行顺序

第一天只做 Backend 边界，不开始 Agent Service 和 Frontend 拆分：

1. 拉取 `99a99c7` 基线并创建 `refactor/agent-boundaries-260712`。
2. 为 Backend 创建独立开发依赖并跑通现有测试。
3. 为 Redis fallback、SSE replay、审批审计补契约测试。
4. 新建 `AgentRunExecutor`，原样迁移 `_consume_agent_run_background`。
5. 修改 Worker 和 Route 依赖，消除 Worker 反向导入 API。
6. 跑完整 Backend、Agent Service 测试和最小 E2E。
7. 提交 `refactor(agent): extract backend run executor`。
8. 当天到此为止，不顺手删除 EventBus。

第二个工作日再集中 Run 状态迁移；第三个工作日才删除 EventBus。这样每一步出现问题都能准确定位。

---

## 17. 完成定义

只有同时满足以下条件，重构才算完成：

- Worker 不依赖 API 层。
- API Route 不执行 Agent 消费循环，不直接操作 Repository。
- Run 状态只有一个 application service 写入口。
- 内存 `AgentRunEventBus` 已删除。
- Redis 明确只是 transient transport，故障不影响产品事实。
- Message、ToolCall、Approval、Artifact 投影独立且幂等。
- Agent Runtime 和 MCP 工具按职责分离，协议完全兼容。
- Frontend 只有一套 Agent controller、连接恢复和消息 reducer。
- 旧路径均有删除证据，不存在仅凭感觉清理的文件。
- Backend、Agent Service、Frontend build、关键 E2E 全部通过。
- README、架构文档和部署文档与实际代码一致。

重构的最终结果不是“目录更漂亮”，而是任何开发者都能快速回答：状态属于谁、由谁修改、失败后从哪里恢复、实时事件丢失时依赖什么事实。

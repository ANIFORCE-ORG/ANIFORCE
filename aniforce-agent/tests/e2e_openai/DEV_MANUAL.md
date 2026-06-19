# ANIFORCE OpenAI Agent Service 开发手册 v1.0

**性质**：开发交付物 + E2E 验证一体。改一个 Block，测一个 Block。
**依据**：`AGENTS.md`（架构设计）+ Claude SDK 调研笔记（`drafts/260615_claude_sdk_learning/study_notes.md`）
**原则**：真实生产场景，不造假数据；每个 Block = 一个交付物。

---

## 架构方向变更（2026-06-18）

**重要决策**：放弃 Claude SDK 迁移线，改用 **OpenAI Agents SDK 独立服务**。

### 变更理由

**Claude SDK 的问题**（实测，详见 `drafts/260618/260618_01_sdk_ttft_probe.py`）：
- 走 `copilot.huya.info` 网关首字延迟 5-8 秒（网关缓冲 + 上游链路慢）
- 直连 `api.anthropic.com` 虽快（0.45s），但生产环境无法直连外网
- Claude SDK subprocess 启动开销大（Node CLI + bootstrap 请求）
- AG-UI/CopilotKit 适配层增加复杂度，收益不匹配

**新方案核心**：
1. **独立 agent-service**（`aniforce-agent/`，端口 8020），从 backend 拆出
2. **OpenAI Agents SDK 原生协议**（`Runner.run_streamed` → `stream_events`）
3. **统一事件模型**（`AgentTaskEvent`，EventType 枚举），前端不感知底层 SDK
4. **agent-service 内部 MCP server**（FastMCP `/mcp`，工具内通过 `httpx` 调 backend REST）
5. **SQLite 持久化**（tasks + events，复用旧版 repository）

### 与 Claude SDK 版本的对比

| 维度 | Claude SDK 版（已弃） | OpenAI SDK 版（当前） |
|------|---------------------|---------------------|
| 部署 | agent 服务独立（8020） | agent 服务独立（8020） |
| SDK | claude-agent-sdk（subprocess） | openai-agents（in-process） |
| 协议 | ANIFORCE business events | AgentTaskEvent（EventType） |
| 适配层 | business_event_adapter + copilotkit_adapter | 无（原生 SDK 事件转换） |
| Session | Claude SDK session.db | OpenAI SQLiteSession |
| MCP | claude mcp（backend_sdk_server） | agent-service 内部 FastMCP + agents.mcp（StreamableHttp） |
| 首字延迟 | 5-8 秒 | ~1-2 秒（deepseek） |

---

## 总览

| Block | 交付物 | 状态 | 脚本 |
|-------|--------|------|------|
| 1 | 基础连通性 + JWT(sub) | ✅ 通过（6/6） | `block1_basic_connectivity.py` |
| 2 | OpenAI SDK 调通（最小闭环） | ✅ 通过（9/9） | `block2_openai_sdk.py` |
| 3 | 事件系统（AgentTaskEvent 流） | ✅ 通过（13/14） | `block3_event_system.py` |
| 4 | 通用任务模型 + DB Schema | ✅ 通过（9/9） | `block4_task_model.py` |
| 5 | Sandbox + Skills | ✅ 通过（10/10） | `block5_sandbox_real_execution.py` |
| 6 | MCP 工具接 backend | ✅ 通过（10/10） | `block6_mcp_backend.py` |
| 7 | 多租户隔离 | ✅ 通过（6/7） | `block7_multi_tenant.py` |
| 8 | 对话历史 + resume | ✅ 通过（13/13） | `block8_history_resume.py` |
| 9 | 生产并发安全 | ✅ 通过（28/28） | `block9_concurrency_safety.py` |
| 10 | 端到端业务剧本（campaign） | ⏳ 待写 | `block10_e2e_campaign.py` |

**执行顺序**：1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10（端到端业务放最后，综合验证）

---

## 核心架构设计

### 架构全景图

```
┌─────────────────────────────────────┐
│           前端                      │
│  订阅 AgentTaskEvent SSE 流         │
│  (message.updated / tool_call.* /   │
│   runtime.* / plan.* / todo.*)      │
└──────────────┬──────────────────────┘
               │ SSE
┌──────────────┴──────────────────────┐
│   OpenAI Agent Service (8020)       │
│  ┌────────────────────────────┐    │
│  │ FastAPI (runs/sessions/    │    │
│  │           tasks)            │    │
│  └──────────┬─────────────────┘    │
│             ↓                       │
│  ┌──────────────────────────────┐  │
│  │ AgentTaskService             │  │
│  │ (create/run/stream task)     │  │
│  └──────────┬───────────────────┘  │
│             ↓                       │
│  ┌──────────────────────────────┐  │
│  │ AgentRuntime                 │  │
│  │ (MCP连接 + Agent创建 + 执行) │  │
│  └──────────┬───────────────────┘  │
│             ↓                       │
│  ┌──────────────────────────────┐  │
│  │ OpenAISDKAdapter             │  │
│  │ (Runner.run_streamed         │  │
│  │  → stream_events             │  │
│  │  → AgentTaskEvent 转换)      │  │
│  └──────────┬───────────────────┘  │
│             ↓                       │
│  ┌──────────────────────────────┐  │
│  │ OpenAI Agents SDK            │  │
│  │ (Agent / SandboxAgent +      │  │
│  │  SQLiteSession + MCP)        │  │
│  └──────────┬───────────────────┘  │
│             ↓                       │
│  ┌──────────────────────────────┐  │
│  │ SQLite Repository            │  │
│  │ (tasks + events 持久化)      │  │
│  └──────────────────────────────┘  │
└──────────────┬──────────────────────┘
               │ MCP (StreamableHttp)
┌──────────────┴──────────────────────┐
│   FastMCP /mcp（agent-service 内部） │
│  tools: projects/campaigns/materials│
└──────────────┬──────────────────────┘
               │ httpx + JWT
┌──────────────┴──────────────────────┐
│   Backend (8010)                    │
│  REST API: /api/v1/projects         │
│            /api/v1/campaigns        │
│            /api/v1/materials        │
└─────────────────────────────────────┘
```

### 通用任务模型

```python
AgentTask:
    task_id: str           # task_{uuid16}
    user_id: str           # 从 JWT sub
    task_type: str         # conversation / campaign_analysis / ...
    title: str
    input: dict            # 任务输入
    session_id: str        # OpenAI SDK Session ID
    status: AgentTaskStatus  # pending/running/completed/error/aborted
    context: dict          # auth_token 等
    created_at / updated_at

AgentTaskEvent:
    event_id: str
    task_id: str
    event_type: EventType  # 见下表
    payload: dict
    sequence: int          # 单调递增
```

### EventType 枚举（前端消费的事件类型）

| EventType | 触发时机 | payload 关键字段 |
|-----------|---------|-----------------|
| `runtime.started` | 任务开始 | task_type, user_input |
| `runtime.completed` | 任务完成 | final_output, usage |
| `runtime.error` | 任务出错 | code, message |
| `runtime.aborted` | 任务取消 | message |
| `message.updated` | 流式文本 delta | delta |
| `message.completed` | 文本回复完成 | content, usage |
| `tool_call.started` | 工具调用开始 | tool_name, arguments |
| `tool_call.completed` | 工具调用完成 | tool_name, result |
| `handoff` | Agent 切换 | agent_name |
| `custom` (subtype=plan_created) | 检测到执行计划 | plan_id, todos |
| `custom` (subtype=todo_started) | Todo 开始执行 | todo_id, title |

---

## 环境准备

### 启动 agent 服务

```bash
cd aniforce-agent
./start_dev.sh
# 固定端口 8020；启动前释放端口；日志覆盖写入 logs/agent.log
```

### 启动 backend（MCP 工具源）

```bash
cd backend
DEMO_MODE=false UV_CACHE_DIR=./uv_cache .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

### 环境变量（.env）

```env
JWT_SECRET=change-me-in-production
PORT=8020

OPENAI_API_KEY=sk-hvtAUe3lPjYQtwiZqLMfYg
OPENAI_BASE_URL=https://copilot.huya.info/api/openai
OPENAI_AGENTS_MODEL=deepseek/deepseek-v4-pro

BACKEND_BASE_URL=http://localhost:8010

AGENT_TASK_DB=runtime/agent/tasks.db
AGENT_SESSION_DB=runtime/agent/sessions.db
RUNTIME_DIR=runtime/sessions
SKILLS_DIR=runtime/skills
SANDBOX_DIR=runtime/agent/sandbox
```

---

## Block 1: 基础连通性 + JWT(sub)

### 验证点
- 服务启动，`/health` 返回 `deepseek/deepseek-v4-pro`
- JWT 用 `sub` 字段（对齐 backend `auth.py`）
- 无认证请求返回 401
- Tasks / Sessions API 带 JWT 可访问

### 执行
```bash
UV_CACHE_DIR=./uv_cache uv run python tests/e2e_openai/block1_basic_connectivity.py
```

### 最近验证（2026-06-19）
- agent-service：`http://localhost:8020`
- 结果：6/6 通过

---

## Block 2: OpenAI SDK 调通（最小闭环）

### 验证点
- 真实 OpenAI 兼容 API 调用（deepseek 模型）
- 流式 SSE 输出（`message.updated` delta）
- 事件链：`runtime.started` → `message.updated*` → `message.completed` → `runtime.completed`
- 多轮对话上下文保持（同一 SQLiteSession 记得上文）
- Session 隔离（新 session 不记得上文）
- 响应时间 < 30s

### 执行
```bash
UV_CACHE_DIR=./uv_cache uv run python tests/e2e_openai/block2_openai_sdk.py
```

### 最近验证（2026-06-19）
- 结果：9/9 通过
- 覆盖：流式 SSE、多轮上下文、Session 隔离、MCP 连接不再报错

---

## Block 3: 事件系统（AgentTaskEvent 流）

### 目标
验证 SSE 事件流的完整性、序号单调、持久化落盘。

### 验证点
- 事件 sequence 单调递增
- 所有事件都落盘到 `agent_events` 表
- 事件类型覆盖：runtime.* / message.* / tool_call.*
- 断点续传：`after_sequence` 只返回后续事件

### 执行
```bash
UV_CACHE_DIR=./uv_cache uv run python tests/e2e_openai/block3_event_system.py
```

### 最近验证（2026-06-19）
- 结果：13/14 通过
- 覆盖：SSE 事件流、DB 落盘、sequence 单调、after_sequence 查询
- 注意：handoff 事件未落盘（不影响核心逻辑）

---

## Block 4: 通用任务模型 + DB Schema

### 目标
验证 `agent_tasks` 表的 CRUD、状态流转、user_id 隔离。

### 验证点
- 创建 task（pending）
- 运行后状态变 running → completed
- 跨用户访问被拒绝（404 或 403）
- 任务列表分页（limit/offset）
- 按 task_type / status 过滤

### 执行
```bash
UV_CACHE_DIR=./uv_cache uv run python tests/e2e_openai/block4_task_model.py
```

### 最近验证（2026-06-19）
- 结果：9/9 通过
- 覆盖：任务状态流转、user_id 隔离、跨用户访问 404、任务列表查询

---

## Block 5: Sandbox + Skills

### 目标
验证 SandboxAgent 是否具备真实执行能力，并确认 sandbox 按 session 隔离。

### 验证点
- Agent 能调用 sandbox 工具（`apply_patch` / `exec_command`）
- Agent 能在当前 session sandbox 中真实创建文件
- Agent 能执行命令读取/列出 sandbox 文件
- 不同 session 使用不同目录：`runtime/agent/sandbox/{session_id}`
- Session B 无法看到 Session A 创建的文件
- Skills 从 `SKILLS_DIR` 加载，不与 sandbox workspace 混用

### 执行
```bash
UV_CACHE_DIR=./uv_cache uv run python tests/e2e_openai/block5_sandbox_real_execution.py
```

### 最近验证（2026-06-19）
- 结果：10/10 通过
- 覆盖：sandbox 工具调用、文件真实落盘、命令执行、session 级目录隔离
- Sandbox 目录：`runtime/agent/sandbox/{session_id}`

---

## Block 6: MCP 工具接 backend

### 目标
验证 agent-service 内部 FastMCP `/mcp` 与 backend REST 的工具调用全链路。

### 验证点
- `MCPServerStreamableHttp` 连接 `http://127.0.0.1:8020/mcp`
- MCP `list_tools` 暴露 9 个工具：projects / campaigns / materials
- `tool_meta_resolver` 注入 `_meta.jwt_token`
- MCP 工具从 `ctx.request_context.meta` 读取 JWT，并通过 `httpx` 调 backend REST
- backend 正式模式下，无 token / 无效 token 返回 401

### 最近验证（2026-06-19）
- 结果：10/10 通过
- 覆盖：MCP 连接、9 个工具暴露、JWT 透传创建/查询、无 token 401

### 执行
```bash
UV_CACHE_DIR=./uv_cache uv run python tests/e2e_openai/block6_mcp_backend.py
```

---

## Block 7: 多租户隔离

### 目标
验证不同 user_id 的 task / session 完全隔离。

### 验证点
- 用户 A 不能访问用户 B 的 task（404）
- 用户 A 不能 resume 用户 B 的 session
- MCP 工具调用带各自 user_id，backend 数据隔离
- 并发请求不串数据

### 最近验证（2026-06-19）
- 结果：6/7 通过
- 覆盖：A/B 用户 MCP 工具级隔离、backend 数据隔离、跨用户 task 访问 404
- 注意：测试用户无历史 task，跨用户访问验证未完全执行（不影响核心隔离）

### 执行
```bash
UV_CACHE_DIR=./uv_cache uv run python tests/e2e_openai/block7_multi_tenant.py
```

---

## Block 8: 对话历史 + resume

### 目标
验证 SQLiteSession 的历史持久化 + 生产级 session 状态管理。

### 验证点
- session 是用户拥有的长期会话元数据，不是 task 派生字段
- 同一 session_id 多轮对话记得上文
- 服务重启后 resume 同一 session 仍记得上文
- 用户不能 resume 其他用户的 session
- session 列表 API 只返回当前用户 active 会话
- session 归档后不再出现在列表，且不能继续 run

### 最近验证（2026-06-19）
- 结果：13/13 通过
- 覆盖：session 创建/列表、SQLiteSession 多轮记忆、服务重启 resume、跨用户拒绝、归档拒绝

### 执行
```bash
UV_CACHE_DIR=./uv_cache uv run python tests/e2e_openai/block8_history_resume.py
```

---

## Block 9: 生产并发安全

### 目标
验证多用户、多 session、同 session 并发请求下的隔离与正确性。

### 验证点
- 10 个并发请求（5 用户 × 2 session）全部成功
- 每个 run 回复自己的唯一 marker，不串上下文
- 每个 user_id 的 task/session 列表互不干扰
- SQLite 写入启用 WAL + busy_timeout，无 `database is locked`
- 同一 session 并发 run 被服务端 session 级锁串行化，避免历史和 sandbox 竞态写

### 最近验证（2026-06-19）
- 结果：28/28 通过
- 覆盖：SQLite WAL、10 路并发 run、跨用户 task/session 隔离、同 session 双并发串行安全
- 日志：`logs/e2e_block9.log`

### 执行
```bash
UV_CACHE_DIR=./uv_cache uv run python tests/e2e_openai/block9_concurrency_safety.py
```

---

## Block 10: 端到端业务剧本（campaign）

### 目标
完整业务链路：用户提问 → Agent 调 MCP 工具查 campaign → 返回分析结果。

### 验证点
- Agent 自主调用 `list_campaigns` / `get_campaign_detail` 工具
- `tool_call.started` / `tool_call.completed` 事件正确
- 工具参数正确（project_id 等）
- 最终回复包含真实 campaign 数据
- MCP 透传 JWT（backend 鉴权通过）

### 执行
```bash
UV_CACHE_DIR=./uv_cache uv run python tests/e2e_openai/block10_e2e_campaign.py
```

---

## 新任务如何接入？

### 场景：新增"受众重叠分析"任务

1. **定义 task_type**：`audience_overlap_analysis`
2. **写 System Prompt**：在 `app/agent/prompts.py` 的 `SystemPromptManager` 加分支
3. **确认 MCP 工具**：agent-service 内部 FastMCP 已暴露 `get_audience_overlap`，工具内通过 `httpx` 调 backend REST
4. **前端调用**：`POST /api/agent/runs`，`task_type=audience_overlap_analysis`
5. **写 E2E**：`tests/e2e_openai/blockN_audience_overlap.py`

---

## 维护规则

1. **改一个 Block，测一个 Block**：不积压未验证的改动
2. **真实数据**：不造假 user_id / session_id，用 backend 真实 JWT
3. **日志留底**：每次测试输出到 `logs/e2e_blockN.log`
4. **失败即停**：Block N 失败不继续 N+1，先修 N
5. **手册同步**：Block 完成后更新本手册状态表

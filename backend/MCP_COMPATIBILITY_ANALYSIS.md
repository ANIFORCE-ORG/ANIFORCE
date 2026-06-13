# MCP 集成全面兼容性分析

## 🎯 目标

确保 MCP 集成**不破坏**现有系统的任何功能：
- ✅ 前端 API 调用
- ✅ Agent 工具调用
- ✅ 事件流
- ✅ 数据库
- ✅ 日志
- ✅ 鉴权

---

## 📊 当前系统架构

```
前端 (13003)
  ↓ HTTP
后端 FastAPI (18003)
  ├─ /api/v1/auth
  ├─ /api/v1/projects
  ├─ /api/v1/campaigns
  ├─ /api/v1/agent/chat/sessions/{id}/stream
  └─ /api/v1/mcp ⭐ 新增
  
数据存储
  ├─ SQLite: data/sqlite/animagus.db (业务数据)
  ├─ Agent Tasks: runtime/agent/tasks.db
  ├─ Agent Sessions: runtime/agent/sessions.db
  └─ Agent Traces: runtime/agent/traces/
```

---

## ✅ 兼容性检查清单

### 1. 前端 API 调用（无影响）

**现有流程**：
```
前端 → POST /api/v1/agent/chat/sessions/{id}/stream
       ↓
       Agent Runtime
       ↓
       返回 SSE 事件流
```

**MCP 集成后**：
```
前端 → POST /api/v1/agent/chat/sessions/{id}/stream
       ↓
       Agent Runtime
       ├─ 创建 Agent（带 MCP）
       ├─ Agent 自动调用 MCP 工具（内部）
       └─ 返回 SSE 事件流（格式不变）
```

**结论**：✅ **完全兼容**，前端无需任何修改

---

### 2. 工具调用阶段（无影响）

**OpenAI Agents SDK 事件流程**：

```python
# Runtime 推送事件
async for event in runner.stream():
    if event.type == "agent.run.started":
        yield AgentTaskEvent(event_type="agent.run.started", ...)
    
    if event.type == "agent.tool.call.started":  # ⭐ MCP 工具调用也会触发
        yield AgentTaskEvent(event_type="tool_call_started", ...)
    
    if event.type == "agent.tool.call.completed":
        yield AgentTaskEvent(event_type="tool_call_completed", ...)
    
    if event.type == "agent.message.delta":
        yield AgentTaskEvent(event_type="message_delta", ...)
```

**MCP 工具调用的事件**：
- `tool_call_started` - 工具调用开始（包含工具名和参数）
- `tool_call_completed` - 工具调用完成（包含返回结果）

**结论**：✅ **完全兼容**，MCP 工具和普通工具一样走事件流

---

### 3. 事件管理（无影响）

**事件存储**：
```python
# runtime.py 中
await self.repo.save_event(task_id, event)
# 存入 runtime/agent/tasks.db
```

**事件类型**：
```python
class EventType(str, Enum):
    RUNTIME_STARTED = "runtime.started"
    TOOL_CALL_STARTED = "tool_call_started"      # ⭐ MCP 工具也用这个
    TOOL_CALL_COMPLETED = "tool_call_completed"  # ⭐ MCP 工具也用这个
    MESSAGE_DELTA = "message_delta"
    RUNTIME_COMPLETED = "runtime.completed"
    ERROR = "error"
```

**结论**：✅ **完全兼容**，MCP 工具调用会生成标准事件并存储

---

### 4. 数据库（无影响）

**现有数据库**：
```
1. data/sqlite/animagus.db
   - users, projects, campaigns, materials, etc.
   - 业务数据，MCP 工具会读写这个库（通过 Repository）

2. runtime/agent/tasks.db
   - agent_tasks 表
   - agent_task_events 表
   - MCP 工具调用的事件也存这里

3. runtime/agent/sessions.db
   - SDK Session 管理
   - MCP 工具调用在 Session 内
```

**MCP 影响**：
- ✅ 复用现有 Repository（ProjectRepository, CampaignRepository）
- ✅ 事件存储机制不变
- ✅ 无新增数据表

**结论**：✅ **完全兼容**，无需迁移或修改数据库

---

### 5. 日志（完全兼容）

**现有日志**：
```python
# runtime.py
task_logger.info("[RUNTIME] Task started")
task_logger.debug(f"[RUNTIME] Event[{seq}]: {event.event_type}")

# adapter.py
logger.debug(f"[SDK] Created agent: {agent.name}")
logger.debug(f"[SDK] Event: {event.type}")
```

**MCP 日志增强**：
```python
# runtime.py
task_logger.debug(f"[RUNTIME] Configured MCP server: {mcp_url}")
task_logger.debug(f"[RUNTIME] Agent created with {len(mcp_servers)} MCP servers")

# mcp.py
logger.debug(f"MCP request: method={method}, params={params}")
logger.info(f"MCP tool executed: {tool_name}")
logger.error(f"MCP tool error: {tool_name} - {e}")
```

**结论**：✅ **完全兼容**，只是增加了 MCP 相关日志

---

### 6. 鉴权（完全复用）

**现有鉴权流程**：
```
请求 → RequestContextMiddleware
       ↓ 解析 JWT
       set_current_user(user_info)
       ↓
API 路由 → get_current_user()
```

**MCP 鉴权**：
```
Agent Runtime → MCP HTTP 请求（带 Authorization header）
                ↓
                POST /api/v1/mcp
                ↓
                RequestContextMiddleware（复用）
                ↓ 解析 JWT
                set_current_user(user_info)
                ↓
                MCP 工具 → get_current_user()
```

**结论**：✅ **完全复用**，无需新增鉴权逻辑

---

## 🔍 详细验证：前端事件流

### 前端接收的事件格式（不变）

```typescript
// 前端代码（无需修改）
eventSource.addEventListener('message_delta', (e) => {
  const event = JSON.parse(e.data);
  // event.event_type === "message_delta"
  // event.data.content
});

eventSource.addEventListener('tool_call_started', (e) => {
  const event = JSON.parse(e.data);
  // ⭐ MCP 工具调用也会触发这个事件
  // event.data.tool_name === "create_project"
  // event.data.arguments === {"name": "春节推广", ...}
});

eventSource.addEventListener('tool_call_completed', (e) => {
  const event = JSON.parse(e.data);
  // ⭐ MCP 工具返回结果
  // event.data.result === "✅ 项目创建成功..."
});
```

### 事件流示例（带 MCP）

```json
// 1. Runtime 启动
{"event_type": "runtime.started", "data": {...}}

// 2. Agent 思考
{"event_type": "message_delta", "data": {"content": "我需要创建一个项目"}}

// 3. 调用 MCP 工具（⭐ 新增，但格式标准）
{
  "event_type": "tool_call_started",
  "data": {
    "tool_name": "create_project",
    "arguments": {"name": "春节推广", "total_budget": 100000}
  }
}

// 4. MCP 工具返回
{
  "event_type": "tool_call_completed",
  "data": {
    "tool_name": "create_project",
    "result": "✅ 项目创建成功\n\n项目 ID: xxx\n名称: 春节推广\n..."
  }
}

// 5. Agent 继续回复
{"event_type": "message_delta", "data": {"content": "项目已创建成功"}}

// 6. 完成
{"event_type": "runtime.completed", "data": {...}}
```

**结论**：✅ **格式完全一致**，前端无需修改

---

## 🔧 Runtime 中的 MCP 集成

### 修改点分析

**修改文件**：`backend/app/agent_platform/runtime.py`

**修改内容**：
```python
# 3. 创建 MCP 服务连接（使用主应用的 MCP 端点）
from agents.mcp import MCPServerStreamableHttp
from app.config.settings import get_settings

settings = get_settings()
auth_token = task.context.get("auth_token", "") if hasattr(task, "context") else ""

mcp_servers = []
if auth_token:  # 只有有 token 时才启用 MCP
    mcp_server = MCPServerStreamableHttp(
        name="ANIFORCE MCP",
        params={
            "url": f"{settings.BACKEND_BASE_URL}/api/v1/mcp",  # http://127.0.0.1:18003/api/v1/mcp
            "headers": {
                "authorization": f"Bearer {auth_token}"
            }
        }
    )
    mcp_servers.append(mcp_server)

# 4. 创建 Agent（带 MCP 服务）
agent = self.adapter.create_agent(
    name="ANIFORCE Assistant",
    instructions=self._get_system_prompt(task.task_type),
    mcp_servers=mcp_servers,  # ⭐ 传递 MCP 服务列表
)
```

**影响范围**：
- ✅ 只在创建 Agent 时增加 MCP 参数
- ✅ 如果没有 token，mcp_servers = []，行为和之前一样
- ✅ 事件流、日志、DB 存储逻辑**完全不变**

---

## 📋 完整的执行流程

### 用户发送消息："帮我创建一个春节推广项目"

```
1. 前端
   POST /api/v1/agent/chat/sessions/{id}/stream
   Body: {"message": "帮我创建一个春节推广项目"}
   Header: Authorization: Bearer <token>

2. API 路由 (routes.py)
   ├─ 解析 auth_token
   ├─ 获取 task
   ├─ task.context = {"auth_token": token}  # ⭐ 设置 token
   └─ 调用 service.run_task()

3. Service (agent_task_service.py)
   └─ 调用 runtime.run_task()

4. Runtime (runtime.py)
   ├─ 创建 MCP 连接（带 auth_token）
   ├─ 创建 Agent（带 mcp_servers）
   ├─ 调用 runner.stream()
   └─ 推送事件流

5. Agent SDK (OpenAI Agents SDK)
   ├─ 理解用户意图
   ├─ 决定调用 create_project 工具
   ├─ 触发 tool_call_started 事件 → 存储到 tasks.db
   ├─ HTTP POST http://127.0.0.1:18003/api/v1/mcp
   │  {
   │    "method": "tools/call",
   │    "params": {
   │      "name": "create_project",
   │      "arguments": {"name": "春节推广", "total_budget": 100000}
   │    }
   │  }
   │  Header: Authorization: Bearer <token>
   │
   ├─ MCP 端点处理
   │  ├─ RequestContextMiddleware 解析 JWT → set_current_user()
   │  ├─ 调用 create_project_tool()
   │  ├─ get_current_user() → 获取用户信息
   │  ├─ async for session in get_db():
   │  │     project_repo = await get_project_repo(session)
   │  │     project = await project_repo.create(...)  # 写入 animagus.db
   │  │     await session.commit()
   │  └─ 返回结果："✅ 项目创建成功..."
   │
   ├─ 触发 tool_call_completed 事件 → 存储到 tasks.db
   ├─ Agent 继续生成回复
   └─ 触发 message_delta 事件 → 存储到 tasks.db

6. 前端
   ├─ 收到 tool_call_started 事件 → 显示"正在创建项目..."
   ├─ 收到 tool_call_completed 事件 → 显示"项目创建成功"
   └─ 收到 message_delta 事件 → 显示 Agent 回复
```

---

## ✅ 兼容性总结

| 组件 | 影响 | 兼容性 |
|------|------|--------|
| **前端 API** | 无变化 | ✅ 100% 兼容 |
| **事件类型** | 无新增 | ✅ 复用现有事件 |
| **事件格式** | 无变化 | ✅ 前端无需修改 |
| **数据库** | 无新表 | ✅ 复用现有表 |
| **日志** | 增加 MCP 日志 | ✅ 不影响现有日志 |
| **鉴权** | 复用中间件 | ✅ 无需新增逻辑 |
| **Agent 创建** | 增加 MCP 参数 | ✅ 可选参数，向后兼容 |
| **业务逻辑** | 复用 Repository | ✅ 无重复代码 |

---

## 🎯 关键设计原则

### 1. 最小侵入

```python
# Runtime 修改（只增加，不改动原有逻辑）
# Before
agent = self.adapter.create_agent(
    name="ANIFORCE Assistant",
    instructions=self._get_system_prompt(task.task_type),
)

# After
agent = self.adapter.create_agent(
    name="ANIFORCE Assistant",
    instructions=self._get_system_prompt(task.task_type),
    mcp_servers=mcp_servers,  # ⭐ 新增参数（可选）
)
```

### 2. 完全复用

```python
# MCP 工具（复用现有 Repository）
async def create_project_tool(...):
    user = get_current_user()  # 复用鉴权
    
    async for session in get_db():  # 复用数据库
        project_repo = await get_project_repo(session)  # 复用 Repository
        project = await project_repo.create(...)  # 复用业务逻辑
        await session.commit()
```

### 3. 事件标准化

```python
# MCP 工具调用和普通工具调用使用相同事件
if event.type == "agent.tool.call.started":
    # 无论是 MCP 工具还是普通工具，都走这里
    yield AgentTaskEvent(event_type="tool_call_started", ...)
```

---

## 🚀 启动验证步骤

### 1. 启动后端（18003）

```bash
cd /workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE
./run_server.sh --backend-port 18003 --frontend-port 13003
```

### 2. 检查 MCP 端点

```bash
curl http://localhost:18003/api/v1/mcp/tools
```

预期输出：
```json
{
  "tools": [
    {"name": "list_projects", ...},
    {"name": "create_project", ...},
    {"name": "list_campaigns", ...},
    {"name": "create_campaign", ...}
  ],
  "count": 4
}
```

### 3. 前端测试

1. 打开 http://localhost:13003
2. 创建新对话
3. 发送："帮我创建一个测试项目，预算 5 万"
4. 观察：
   - ✅ 前端显示"正在创建项目..."（tool_call_started 事件）
   - ✅ 前端显示"项目创建成功"（tool_call_completed 事件）
   - ✅ Agent 继续回复（message_delta 事件）

### 4. 检查数据库

```bash
# 检查项目是否创建
sqlite3 backend/data/sqlite/animagus.db "SELECT * FROM projects ORDER BY created_at DESC LIMIT 1;"

# 检查事件是否记录
sqlite3 backend/runtime/agent/tasks.db "SELECT event_type, data FROM agent_task_events ORDER BY sequence DESC LIMIT 10;"
```

预期看到：
- ✅ `tool_call_started` 事件（包含 create_project 工具名和参数）
- ✅ `tool_call_completed` 事件（包含返回结果）
- ✅ projects 表中有新记录

### 5. 检查日志

```bash
tail -f logs/backend_logs_*.log | grep -E "MCP|tool_call"
```

预期日志：
```
[RUNTIME] Configured MCP server: http://127.0.0.1:18003/api/v1/mcp
[RUNTIME] Agent created with 1 MCP servers
[MCP] request: method=tools/call, params={'name': 'create_project', ...}
[MCP] tool executed: create_project
[RUNTIME] Event[X]: tool_call_started
[RUNTIME] Event[Y]: tool_call_completed
```

---

## ⚠️ 注意事项

### 1. Token 传递

确保 `routes.py` 中正确提取 token：
```python
auth_header = request.headers.get("authorization", "")
auth_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
task.context = {"auth_token": auth_token}
```

### 2. 端口配置

确保 `.env` 正确配置：
```bash
BACKEND_BASE_URL=http://127.0.0.1:18003
FRONTEND_BASE_URL=http://127.0.0.1:13003
```

### 3. 数据库路径

确保 DB 文件存在：
```bash
ls -la backend/data/sqlite/animagus.db
ls -la backend/runtime/agent/tasks.db
ls -la backend/runtime/agent/sessions.db
```

---

## 📊 最终架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     前端 (13003)                             │
│  - 对话界面                                                  │
│  - 事件监听（SSE）                                           │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP POST /api/v1/agent/chat/sessions/{id}/stream
                      │ Authorization: Bearer <token>
                      ↓
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (18003)                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ RequestContextMiddleware                                ││
│  │  - 解析 JWT Token                                       ││
│  │  - set_current_user()                                   ││
│  └─────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ API Routes                                              ││
│  │  /api/v1/auth         - 认证                           ││
│  │  /api/v1/projects     - 项目管理                       ││
│  │  /api/v1/campaigns    - 广告投放                       ││
│  │  /api/v1/agent        - Agent 任务                     ││
│  │  /api/v1/mcp ⭐       - MCP 工具端点                  ││
│  └─────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Agent Runtime                                           ││
│  │  ├─ 创建 Agent (带 MCP)                                ││
│  │  ├─ 执行任务                                           ││
│  │  ├─ 推送事件流                                         ││
│  │  └─ 存储事件到 DB                                      ││
│  └─────────────────┬───────────────────────────────────────┘│
│                    │                                          │
│                    │ MCP Tool Call (内部 HTTP)               │
│                    ↓                                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ MCP Endpoint (/api/v1/mcp)                              ││
│  │  ├─ 接收工具调用请求                                   ││
│  │  ├─ get_current_user() ← 从上下文获取                 ││
│  │  ├─ 调用 Repository                                    ││
│  │  └─ 返回结果                                           ││
│  └─────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Repositories (复用)                                     ││
│  │  ├─ ProjectRepository                                   ││
│  │  ├─ CampaignRepository                                  ││
│  │  ├─ MaterialRepository                                  ││
│  │  └─ ...                                                 ││
│  └─────────────────────────────────────────────────────────┘│
└───────────────────────┬───────────────────────────────────────┘
                        │
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                    数据库                                     │
│  ├─ animagus.db          - 业务数据                         │
│  ├─ tasks.db             - Agent 任务和事件                 │
│  └─ sessions.db          - Agent Session                    │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ 总结

MCP 集成**没有丢西瓜**：

1. ✅ **前端零修改** - 事件格式完全一致
2. ✅ **工具调用标准化** - MCP 工具和普通工具走相同流程
3. ✅ **事件管理不变** - 存储、查询、推送逻辑不变
4. ✅ **数据库复用** - 无新表，复用现有 Repository
5. ✅ **日志增强** - 只增加 MCP 日志，不影响现有日志
6. ✅ **鉴权复用** - 完全复用 RequestContextMiddleware

**捡到的芝麻**：
- ✅ Agent 可以调用真实业务逻辑（创建项目、投放广告）
- ✅ 统一端口管理（18003）
- ✅ 自动鉴权（无需手动传递 user_id）

**现在可以放心测试了！** 🚀

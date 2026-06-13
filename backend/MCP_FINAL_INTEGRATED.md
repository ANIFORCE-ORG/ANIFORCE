# MCP 集成完成 - 最终版

## ✅ 实现方案

### 核心设计：MCP 作为主应用路由

**不使用独立端口**，而是集成到 FastAPI 主应用：

```
FastAPI App (端口 18004)
│
├─ /api/v1/auth      - 认证
├─ /api/v1/projects  - 项目管理
├─ /api/v1/campaigns - 广告投放
├─ /api/v1/agent     - Agent 任务
└─ /api/v1/mcp       - MCP 工具入口 ⭐ 新增
   ├─ POST /api/v1/mcp - 工具调用
   └─ GET /api/v1/mcp/tools - 工具列表
```

---

## 📋 架构流程

```
前端请求
  ↓
POST /api/v1/agent/chat/sessions/{id}/stream
  ↓ (带 Authorization: Bearer <token>)
Agent Runtime
  ↓ (创建 MCP 连接)
MCPServerStreamableHttp
  ↓ (HTTP 请求，带 Authorization header)
POST /api/v1/mcp
  ↓ (通过上下文中间件验证)
get_current_user() → 获取用户信息
  ↓
执行 MCP 工具（list_projects, create_campaign 等）
  ↓ (自动使用当前用户身份)
返回结果给 Agent
```

---

## 🔑 关键特性

### 1. 共用主应用端口

- ✅ 无需单独启动 MCP 服务
- ✅ 统一端口管理（18004）
- ✅ 共用鉴权中间件

### 2. 自动鉴权

```python
# MCP 工具自动获取当前用户
@router.post("/mcp")
async def mcp_endpoint(request: Request):
    # RequestContextMiddleware 已设置用户信息
    # MCP 工具内部直接调用 get_current_user()
```

### 3. 复用现有逻辑

```python
async def list_projects_tool():
    user = get_current_user()  # 自动获取
    
    async for session in get_db():
        project_repo = await get_project_repo(session)
        projects = await project_repo.list_by_user(user["id"])
    
    return format_projects(projects)
```

---

## 📁 文件清单

### 新增文件

```
backend/app/
├─ api/v1/
│  └─ mcp.py                    ⭐ MCP 路由（9 个工具）
├─ core/
│  └─ context.py                ⭐ 上下文管理
└─ middleware/
   └─ context.py                ⭐ 上下文中间件
```

### 修改文件

```
backend/app/
├─ main.py                      ✏️ 添加上下文中间件
├─ api/v1/
│  ├─ router.py                 ✏️ 注册 MCP 路由
│  └─ agent/routes.py           ✏️ 传递 auth_token
└─ agent_platform/
   └─ runtime.py                ✏️ 使用 MCP 服务
```

---

## 🚀 启动验证

### 1. 启动应用

```bash
cd /workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE
./run_server.sh --backend-port 18004 --frontend-port 3010
```

### 2. 查看 MCP 工具

```bash
# 获取工具列表
curl http://localhost:18004/api/v1/mcp/tools

# 预期输出：9 个工具
{
  "tools": [
    {"name": "list_projects", "description": "获取用户的项目列表"},
    {"name": "create_project", "description": "创建新项目"},
    {"name": "list_campaigns", "description": "获取广告投放计划列表"},
    {"name": "create_campaign", "description": "创建广告投放计划"},
    ...
  ],
  "count": 4
}
```

### 3. 测试 Agent 调用 MCP 工具

```bash
# 1. 登录获取 token
TOKEN=$(curl -s -X POST http://localhost:18004/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}' \
  | jq -r '.data.access_token')

# 2. 创建对话
SESSION_ID=$(curl -s -X POST http://localhost:18004/api/v1/agent/chat/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"测试对话"}' \
  | jq -r '.id')

# 3. 发送消息（Agent 会自动调用 MCP 工具）
curl -X POST http://localhost:18004/api/v1/agent/chat/sessions/$SESSION_ID/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"帮我创建一个名为'春节推广'的项目，预算10万元"}'
```

**预期行为**：
- Agent 自动调用 `create_project` 工具
- 使用当前用户身份（从 Bearer Token 获取）
- 返回创建结果

---

## 🔍 调试

### 查看 Agent 日志

```bash
tail -f logs/backend_logs_*.log | grep MCP
```

预期日志：
```
[RUNTIME] Configured MCP server: http://localhost:18004/api/v1/mcp
[RUNTIME] Agent created: ANIFORCE Assistant with 1 MCP servers
[MCP] request: method=tools/call, params={'name': 'create_project', ...}
[MCP] tool executed: create_project
```

### 查看 MCP 请求

```bash
# 直接测试 MCP 端点
curl -X POST http://localhost:18004/api/v1/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "list_projects",
      "arguments": {}
    },
    "id": 1
  }'
```

---

## ⚙️ 配置

### 端口配置

编辑 `.env`:
```bash
# 后端端口（默认 8010）
PORT=18004

# 前端会自动连接到后端端口
VITE_BACKEND_PORT=18004
```

### MCP URL

Runtime 自动使用：
```python
mcp_url = f"{settings.BACKEND_BASE_URL}/api/v1/mcp"
# 本地: http://localhost:18004/api/v1/mcp
# 生产: https://www.aniforce.cc/api/v1/mcp
```

---

## 📊 可用的 MCP 工具

当前实现：

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `list_projects` | 获取项目列表 | status, limit |
| `create_project` | 创建项目 | name, total_budget, description, game_type |
| `list_campaigns` | 获取广告投放列表 | project_id, status, limit |
| `create_campaign` | 创建广告投放 | project_id, name, platform, budget, status |

---

## 🎯 下一步

### 扩展更多工具

编辑 `backend/app/api/v1/mcp.py`，添加新工具：

```python
async def your_new_tool_function(...) -> str:
    user = get_current_user()
    # 复用现有 Repository
    ...
    return "result"

# 注册到 TOOLS 字典
TOOLS["your_tool"] = {
    "function": your_new_tool_function,
    "description": "...",
    "parameters": {...}
}
```

重启应用即可生效。

### 建议添加的工具

- ✅ 项目管理（已完成）
- ✅ 广告投放管理（已完成）
- ⏳ 素材管理（materials）
- ⏳ 平台授权（platform_auth）
- ⏳ 数据分析（analytics）

---

## ✨ 总结

现在 MCP 已经：
- ✅ 集成到主应用（共用 18004 端口）
- ✅ 自动鉴权（通过上下文中间件）
- ✅ 复用现有业务逻辑
- ✅ Agent 自动调用工具
- ✅ 零配置，开箱即用

**一个端口，统一管理！** 🚀

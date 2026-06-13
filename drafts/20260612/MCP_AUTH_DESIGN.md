# MCP 鉴权设计方案（基于 AI2Earn 参考）

## 1. AI2Earn 的鉴权架构分析

### 1.1 核心设计理念

AI2Earn 的 MCP 鉴权采用 **请求上下文传递 + 无状态验证** 模式：

```
前端请求（带 JWT Token）
    ↓
API Gateway（解析 Token）
    ↓
Agent Runtime（提取并过滤 Headers）
    ↓
MCP HTTP Server（接收 Headers，验证用户身份）
    ↓
MCP Tool（通过 AsyncLocalStorage 获取用户信息）
```

### 1.2 关键组件

#### 1) AsyncLocalStorage 请求上下文

**文件**: `libs/common/src/interceptors/request-context.interceptor.ts`

```typescript
import { AsyncLocalStorage } from 'node:async_hooks'

interface RequestContextStore {
  locale: Locale
  user?: TokenInfo  // 用户信息
}

export const requestContext = new AsyncLocalStorage<RequestContextStore>()

// 在任何地方获取当前请求的用户信息
export function getUser(): TokenInfo {
  const user = requestContext.getStore()?.user
  if (!user) {
    throw new UnauthorizedException()
  }
  return user
}

export function getUserOptional(): TokenInfo | undefined {
  return requestContext.getStore()?.user
}
```

**核心特点**:
- 使用 Node.js AsyncLocalStorage 在异步调用链中传递上下文
- 无需手动传递 `userId`，任何嵌套函数都能获取
- 线程安全（基于异步上下文）

#### 2) Headers 过滤与传递

**文件**: `apps/aitoearn-ai/src/core/agent/agent.utils.ts`

```typescript
export function filterHeaders(headers: Record<string, unknown>): Record<string, string> {
  const basicHeaders = new Set([
    'host', 'connection', 'content-length', 'content-type',
    'accept', 'accept-encoding', 'user-agent', 'cache-control',
    'pragma', 'upgrade-insecure-requests', 'if-modified-since',
    'if-none-match',
  ])

  const filtered: Record<string, string> = {}

  for (const [key, value] of Object.entries(headers)) {
    if (!basicHeaders.has(key.toLowerCase()) && typeof value === 'string') {
      filtered[key] = value
    }
  }

  return filtered
}
```

**用途**:
- 过滤掉基础 HTTP Headers
- 保留业务 Headers（如 `authorization`、`x-user-id` 等）
- 传递给远程 MCP 服务

#### 3) Agent SDK 配置 MCP 服务（带 Headers）

**文件**: `apps/aitoearn-ai/src/core/agent/services/agent-runtime.service.ts`

```typescript
async initializeTask(userId, userType, dto, abortController, req) {
  // 过滤并提取业务 headers
  const headers = filterHeaders(req.headers)
  
  // 配置 MCP 服务（HTTP 类型）
  const mcpServers: Record<string, McpServerConfig> = {
    [McpServerName.Account]: {
      type: 'http',
      url: `${config.serverClient.baseUrl}/account/mcp`,
      headers,  // 传递 headers 进行鉴权
    },
    [McpServerName.Content]: {
      type: 'http',
      url: `${config.serverClient.baseUrl}/content/mcp`,
      headers,
    },
    [McpServerName.Publish]: {
      type: 'http',
      url: `${config.serverClient.baseUrl}/publish/mcp`,
      headers,
    },
  }

  return { mcpServers, ... }
}
```

**关键点**:
- Claude Agent SDK 支持在 MCP HTTP 配置中传递 `headers`
- Headers 会被附加到所有 MCP 工具调用请求中

#### 4) MCP Server 鉴权中间件

**文件**: `libs/nest-mcp/src/mcp.module.ts`

```typescript
@Module({
  imports: [
    McpModule.forRoot({
      name: 'account',
      version: '1.0.0',
      apiPrefix: 'account',
      guards: [],  // 可配置 NestJS Guards
      decorators: [ApiTags('MCP/Account')],
    }),
  ],
})
export class AccountMcpModule {}
```

**文件**: `libs/nest-mcp/src/services/mcp-streamable-http.service.ts`

```typescript
async handleStatelessRequest(req: any, res: HttpResponse, body: unknown) {
  // 每次请求都会创建新的请求作用域
  const contextId = ContextIdFactory.getByRequest(req)
  
  // 使用请求作用域解析 executor（会触发 AsyncLocalStorage 设置）
  const executor = await this.moduleRef.resolve(
    McpExecutorService,
    contextId,
    { strict: true },
  )
  
  // 注册请求处理器（在此处可以访问 req.user）
  executor.registerRequestHandlers(server, req)
}
```

**关键点**:
- NestJS 的 `ContextIdFactory.getByRequest(req)` 确保请求作用域
- 在请求作用域内，`getUser()` 可以正确获取用户信息
- MCP Tool 内部直接调用 `getUser()` 获取身份

#### 5) MCP Tool 实现（直接获取用户）

**文件**: `apps/aitoearn-server/src/core/account/account.mcp.controller.ts`

```typescript
@Tool({
  name: 'getAccountGroupList',
  description: 'Get all account groups for the authenticated user',
  parameters: z.object({}),
})
async getAccountGroupList(_params: z.infer<typeof schema>) {
  const user = getUser()  // 直接从 AsyncLocalStorage 获取
  const result = await this.accountGroupService.getAccountGroup(user.id)
  return toYamlTextResult(result)
}
```

**优势**:
- 工具代码无需关心 `userId` 从哪来
- 统一的鉴权方式，易于维护
- 自动处理未登录情况（抛出 UnauthorizedException）

---

## 2. ANIFORCE 的 MCP 鉴权适配方案

### 2.1 架构设计

```
┌──────────────────────────────────────────────────────────┐
│                  FastAPI Application                      │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │              API Endpoint (/v1/agent/task)         │  │
│  │  - 解析 JWT Token（通过 get_current_user）       │  │
│  │  - 提取 user_id, user_type                        │  │
│  └────────────────────────────────────────────────────┘  │
│                         ↓                                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │              AgentRuntime                          │  │
│  │  - 收集请求上下文（user_id, headers）            │  │
│  │  - 配置 MCP 服务（附加 headers）                 │  │
│  └────────────────────────────────────────────────────┘  │
│                         ↓                                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │          OpenAI Agents SDK (Python)                │  │
│  │  - MCPServerStreamableHttp(url, headers)           │  │
│  └────────────────────────────────────────────────────┘  │
└───────────────────────────┬───────────────────────────────┘
                            ↓ HTTP Request (with headers)
┌──────────────────────────────────────────────────────────┐
│              MCP Service (独立 FastAPI App)              │
│                                                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │          Middleware (AuthMiddleware)               │  │
│  │  - 解析 Authorization header                       │  │
│  │  - 验证 JWT Token                                  │  │
│  │  - 设置 request.state.user                         │  │
│  └────────────────────────────────────────────────────┘  │
│                         ↓                                 │
│  ┌────────────────────────────────────────────────────┐  │
│  │          MCP Tool (fastmcp)                        │  │
│  │  - 通过 request.state.user 获取用户信息           │  │
│  │  - 执行业务逻辑                                    │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 2.2 实现步骤

#### Step 1: 创建鉴权中间件

**文件**: `backend/app/agent_platform/mcp/middleware.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import HTTPException, status
from app.core.security import decode_jwt_token

class MCPAuthMiddleware(BaseHTTPMiddleware):
    """MCP 服务鉴权中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 提取 Authorization header
        auth_header = request.headers.get("authorization", "")
        
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = auth_header[7:]  # 去掉 "Bearer " 前缀
        
        try:
            # 解析 JWT Token
            payload = decode_jwt_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            # 将用户信息存入 request.state
            request.state.user_id = user_id
            request.state.user_type = payload.get("user_type", "user")
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}"
            )
        
        response = await call_next(request)
        return response
```

#### Step 2: 创建用户上下文工具

**文件**: `backend/app/agent_platform/mcp/context.py`

```python
from contextvars import ContextVar
from typing import Optional
from starlette.requests import Request

# 使用 ContextVar 存储请求上下文（类似 AsyncLocalStorage）
_request_context: ContextVar[Optional[Request]] = ContextVar(
    "_request_context", default=None
)

def set_request_context(request: Request):
    """设置当前请求上下文"""
    _request_context.set(request)

def get_current_user_id() -> str:
    """从上下文获取当前用户 ID"""
    request = _request_context.get()
    if request is None:
        raise RuntimeError("Request context not set")
    
    if not hasattr(request.state, "user_id"):
        raise RuntimeError("User not authenticated")
    
    return request.state.user_id

def get_current_user_type() -> str:
    """从上下文获取当前用户类型"""
    request = _request_context.get()
    if request is None:
        raise RuntimeError("Request context not set")
    
    return getattr(request.state, "user_type", "user")
```

#### Step 3: MCP 服务实现

**文件**: `backend/app/mcp_servers/campaign_server.py`

```python
from mcp.server.fastmcp import FastMCP
from app.agent_platform.mcp.middleware import MCPAuthMiddleware
from app.agent_platform.mcp.context import (
    get_current_user_id,
    set_request_context,
)

# 创建 MCP 服务
mcp = FastMCP(
    "Campaign Management Server",
    host="127.0.0.1",
    port=8001,
)

# 添加鉴权中间件
mcp.app.add_middleware(MCPAuthMiddleware)

# 添加上下文设置中间件
@mcp.app.middleware("http")
async def set_context_middleware(request, call_next):
    set_request_context(request)
    response = await call_next(request)
    return response

@mcp.tool()
def get_campaign_list() -> str:
    """获取用户的广告投放计划列表"""
    user_id = get_current_user_id()  # 直接获取当前用户
    
    # 查询数据库
    campaigns = db.query(Campaign).filter_by(user_id=user_id).all()
    
    return f"Found {len(campaigns)} campaigns for user {user_id}"

@mcp.tool()
def create_campaign(name: str, budget: float) -> str:
    """创建新的广告投放计划"""
    user_id = get_current_user_id()
    user_type = get_current_user_type()
    
    # 权限校验
    if user_type != "admin" and budget > 10000:
        return "Error: Regular users cannot create campaigns with budget > 10000"
    
    campaign = Campaign(
        user_id=user_id,
        name=name,
        budget=budget,
    )
    db.add(campaign)
    db.commit()
    
    return f"Campaign '{name}' created successfully"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

#### Step 4: Agent Runtime 配置

**文件**: `backend/app/agent_platform/runtime.py`

```python
from agents.mcp import MCPServerStreamableHttp

class AgentRuntime:
    def __init__(self, ...):
        # ...
    
    async def run_task(self, task: AgentTask, user_input: str):
        # 获取当前请求的 JWT Token
        from fastapi import Request
        from starlette.requests import Request as StarletteRequest
        
        # 假设我们在路由中传入了 request
        request: Request = task.context.get("request")
        auth_header = request.headers.get("authorization", "")
        
        # 构建 headers（传递给 MCP 服务）
        mcp_headers = {
            "authorization": auth_header,
            "x-user-id": task.user_id,  # 额外传递（可选）
        }
        
        # 配置 MCP 服务
        mcp_servers = [
            MCPServerStreamableHttp(
                params={
                    "url": "http://localhost:8001/mcp",
                    "headers": mcp_headers,  # 传递鉴权信息
                }
            ),
            MCPServerStreamableHttp(
                params={
                    "url": "http://localhost:8002/mcp",
                    "headers": mcp_headers,
                }
            ),
        ]
        
        # 创建 Agent
        agent = self.adapter.create_agent(
            name="ANIFORCE Assistant",
            instructions=self._get_system_prompt(task.task_type),
            mcp_servers=mcp_servers,  # 关联 MCP 服务
        )
        
        # ...
```

#### Step 5: API 路由集成

**文件**: `backend/app/api/v1/agent/routes.py`

```python
from fastapi import APIRouter, Depends, Request
from app.core.security import get_current_user

router = APIRouter()

@router.post("/task/stream")
async def create_task_stream(
    request: Request,
    dto: CreateTaskRequest,
    current_user = Depends(get_current_user),
):
    """创建 Agent 任务（流式）"""
    
    # 将 request 传递给 task context
    task = await agent_task_service.create_task(
        user_id=current_user.id,
        user_type=current_user.user_type,
        dto=dto,
        context={"request": request},  # 传递请求上下文
    )
    
    # 流式返回
    async def event_generator():
        async for event in runtime.run_task(task, dto.prompt):
            yield event.to_sse()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
```

---

## 3. 关键优势

### 3.1 与 AI2Earn 对比

| 维度 | AI2Earn (NestJS) | ANIFORCE (FastAPI) |
|------|------------------|---------------------|
| 上下文传递 | AsyncLocalStorage (Node.js) | ContextVar (Python) |
| 中间件 | NestJS Guards + Interceptor | Starlette Middleware |
| 请求作用域 | NestJS ContextIdFactory | Request.state + ContextVar |
| MCP 框架 | @yikart/nest-mcp | fastmcp |
| 用户获取 | `getUser()` | `get_current_user_id()` |

### 3.2 安全性保证

✅ **Token 验证**: 每次 MCP 请求都经过 JWT 验证
✅ **隔离性**: 使用 ContextVar 确保请求隔离
✅ **最小权限**: MCP Tool 只能访问当前用户的数据
✅ **审计追踪**: 所有操作都有 user_id 记录

### 3.3 代码简洁性

**Before (传递 user_id)**:
```python
@mcp.tool()
def get_campaigns(user_id: str) -> str:
    # 问题: user_id 可能被伪造
    campaigns = db.query(Campaign).filter_by(user_id=user_id).all()
    ...
```

**After (上下文获取)**:
```python
@mcp.tool()
def get_campaigns() -> str:
    user_id = get_current_user_id()  # 自动从鉴权上下文获取
    campaigns = db.query(Campaign).filter_by(user_id=user_id).all()
    ...
```

---

## 4. 部署注意事项

### 4.1 开发环境

```yaml
# docker-compose.yml
services:
  backend:
    # 主应用
    ports:
      - "8000:8000"
  
  mcp-campaign:
    # MCP 服务
    build: ./backend
    command: python app/mcp_servers/campaign_server.py
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://...
      - JWT_SECRET=same-as-backend
```

### 4.2 生产环境

建议使用反向代理统一管理：

```nginx
# nginx.conf
location /api/ {
    proxy_pass http://backend:8000;
}

location /mcp/campaign/ {
    proxy_pass http://mcp-campaign:8001/mcp;
}

location /mcp/content/ {
    proxy_pass http://mcp-content:8002/mcp;
}
```

---

## 5. 测试用例

```python
# tests/test_mcp_auth.py
import pytest
from fastapi.testclient import TestClient

def test_mcp_tool_without_auth():
    """测试未鉴权调用 MCP 工具"""
    response = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "get_campaigns"},
    })
    assert response.status_code == 401

def test_mcp_tool_with_auth():
    """测试鉴权调用 MCP 工具"""
    headers = {"authorization": f"Bearer {valid_token}"}
    response = client.post("/mcp", json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "get_campaigns"},
    }, headers=headers)
    assert response.status_code == 200

def test_mcp_tool_user_isolation():
    """测试用户数据隔离"""
    user1_token = create_token(user_id="user1")
    user2_token = create_token(user_id="user2")
    
    # 用户1创建 campaign
    response1 = client.post("/mcp", json={
        "method": "tools/call",
        "params": {
            "name": "create_campaign",
            "arguments": {"name": "Test", "budget": 1000}
        }
    }, headers={"authorization": f"Bearer {user1_token}"})
    
    # 用户2查询（不应该看到用户1的数据）
    response2 = client.post("/mcp", json={
        "method": "tools/call",
        "params": {"name": "get_campaigns"}
    }, headers={"authorization": f"Bearer {user2_token}"})
    
    campaigns = response2.json()["result"]
    assert "Test" not in campaigns
```

---

## 6. 总结

ANIFORCE 的 MCP 鉴权方案完全借鉴 AI2Earn 的设计思路：

**核心原则**:
- 无状态鉴权：每次请求都验证 JWT Token
- 上下文传递：使用 ContextVar 在异步调用链中传递用户信息
- 中间件拦截：统一在 MCP 服务入口验证身份
- 透明访问：业务代码直接调用 `get_current_user_id()`

**实施优先级**:
1. ✅ 创建 AuthMiddleware（1小时）
2. ✅ 实现 ContextVar 上下文（1小时）
3. ✅ 改造 MCP 服务集成中间件（2小时）
4. ✅ 更新 AgentRuntime 传递 headers（1小时）
5. ✅ 编写单元测试（2小时）

**总工作量**: 1天

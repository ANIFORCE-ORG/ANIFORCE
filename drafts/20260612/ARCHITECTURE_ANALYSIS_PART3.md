## 第三部分：推荐改造方案与实施路线图

### 1. 优先级评估

| 改造项 | 重要性 | 紧急度 | 工作量 | 优先级 |
|--------|--------|--------|--------|--------|
| 请求上下文传递 (ContextVar) | ⭐⭐⭐⭐⭐ | 高 | 2天 | P0 |
| 全局鉴权中间件 | ⭐⭐⭐⭐⭐ | 高 | 1天 | P0 |
| 统一日志系统 (structlog) | ⭐⭐⭐⭐ | 中 | 2天 | P1 |
| Prometheus Metrics | ⭐⭐⭐⭐ | 中 | 1天 | P1 |
| MCP 鉴权集成 | ⭐⭐⭐⭐⭐ | 高 | 2天 | P0 |
| 统一异常处理 | ⭐⭐⭐ | 低 | 1天 | P2 |
| 响应格式化中间件 | ⭐⭐⭐ | 低 | 0.5天 | P2 |

---

### 2. P0 任务：请求上下文传递系统

#### 2.1 创建上下文模块

**文件**: `backend/app/core/context.py`

```python
from contextvars import ContextVar
from typing import Optional, TypedDict
from fastapi import Request

class UserContext(TypedDict):
    id: str
    email: str
    name: str
    type: str  # user | admin

class RequestContext(TypedDict):
    user: Optional[UserContext]
    request_id: str
    tenant_id: Optional[str]

# 定义上下文变量
_request_context: ContextVar[Optional[RequestContext]] = ContextVar(
    "_request_context", default=None
)

def set_request_context(ctx: RequestContext):
    """设置请求上下文"""
    _request_context.set(ctx)

def get_request_context() -> RequestContext:
    """获取请求上下文"""
    ctx = _request_context.get()
    if ctx is None:
        raise RuntimeError("Request context not set")
    return ctx

def get_current_user() -> UserContext:
    """获取当前用户（快捷方法）"""
    ctx = get_request_context()
    if ctx.get("user") is None:
        from fastapi import HTTPException
        raise HTTPException(401, "Not authenticated")
    return ctx["user"]

def get_current_user_optional() -> Optional[UserContext]:
    """获取当前用户（可选）"""
    try:
        ctx = get_request_context()
        return ctx.get("user")
    except RuntimeError:
        return None

def get_request_id() -> str:
    """获取请求 ID"""
    ctx = get_request_context()
    return ctx["request_id"]
```

#### 2.2 创建上下文中间件

**文件**: `backend/app/middleware/context.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from uuid import uuid4
from app.core.context import set_request_context, UserContext
from app.core.security import decode_jwt_token_optional

class RequestContextMiddleware(BaseHTTPMiddleware):
    """请求上下文中间件 - 自动设置上下文变量"""
    
    async def dispatch(self, request: Request, call_next):
        # 1. 生成或获取 request_id
        request_id = request.headers.get("x-request-id", str(uuid4()))
        
        # 2. 解析用户信息（可选）
        user = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_jwt_token_optional(token)
                if payload:
                    user = UserContext(
                        id=payload["sub"],
                        email=payload.get("email", ""),
                        name=payload.get("name", ""),
                        type=payload.get("type", "user"),
                    )
            except Exception:
                pass  # 忽略无效 token
        
        # 3. 设置上下文
        set_request_context({
            "user": user,
            "request_id": request_id,
            "tenant_id": request.headers.get("x-tenant-id"),
        })
        
        # 4. 执行请求
        response = await call_next(request)
        
        # 5. 设置响应头
        response.headers["x-request-id"] = request_id
        
        return response
```

#### 2.3 注册中间件

**文件**: `backend/app/main.py`

```python
from app.middleware.context import RequestContextMiddleware

app = FastAPI(...)

# 添加上下文中间件（必须在最外层）
app.add_middleware(RequestContextMiddleware)
```

#### 2.4 更新业务代码

**Before**:
```python
@router.post("/task")
async def create_task(
    dto: CreateTaskRequest,
    current_user = Depends(get_current_user),  # ❌ 每次都要写
):
    return await service.create_task(
        user_id=current_user["id"],  # ❌ 手动传递
        dto=dto
    )

class TaskService:
    async def create_task(self, user_id: str, dto):
        # ❌ 每个函数都要加 user_id 参数
        task = await self.repo.create(user_id, dto)
        await self.notify(user_id, "created")
```

**After**:
```python
from app.core.context import get_current_user

@router.post("/task")
async def create_task(dto: CreateTaskRequest):  # ✅ 无需 Depends
    return await service.create_task(dto)

class TaskService:
    async def create_task(self, dto):
        user = get_current_user()  # ✅ 直接获取
        task = await self.repo.create(user["id"], dto)
        await self.notify("created")  # ✅ notify 内部自己获取
```

#### 2.5 兼容性考虑

保留 `get_current_user` Depends 作为显式鉴权标记：

```python
from app.core.context import get_current_user as _get_current_user

async def get_current_user() -> dict:
    """
    FastAPI Depends 包装器
    用途：明确标记此端点需要鉴权
    """
    return _get_current_user()

# 使用
@router.post("/task")
async def create_task(
    dto: CreateTaskRequest,
    _: dict = Depends(get_current_user),  # 明确标记需要鉴权
):
    # 内部直接用 _get_current_user()
    pass
```

---

### 3. P0 任务：全局鉴权中间件

#### 3.1 创建鉴权中间件

**文件**: `backend/app/middleware/auth.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import HTTPException

class AuthMiddleware(BaseHTTPMiddleware):
    """
    全局鉴权中间件
    - 自动验证需要鉴权的端点
    - 设置 request.state.user
    """
    
    # 公开端点（无需鉴权）
    PUBLIC_PATHS = {
        "/health",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
    }
    
    async def dispatch(self, request: Request, call_next):
        # 公开端点直接放行
        if any(request.url.path.startswith(path) for path in self.PUBLIC_PATHS):
            return await call_next(request)
        
        # 检查 Authorization header
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(401, "Missing authorization header")
        
        token = auth_header[7:]
        
        try:
            payload = decode_jwt_token(token)
            user = {
                "id": payload["sub"],
                "email": payload.get("email"),
                "name": payload.get("name"),
            }
            # 设置到 request.state（给 RequestContextMiddleware 使用）
            request.state.user = user
            
        except Exception as e:
            raise HTTPException(401, f"Invalid token: {str(e)}")
        
        return await call_next(request)
```

#### 3.2 与上下文中间件配合

```python
# main.py
app.add_middleware(RequestContextMiddleware)  # 第一层：设置上下文
app.add_middleware(AuthMiddleware)            # 第二层：鉴权
```

**执行顺序**:
```
请求 → AuthMiddleware (验证 token)
     → RequestContextMiddleware (设置上下文)
     → 业务代码
     ← RequestContextMiddleware
     ← AuthMiddleware
```

---

### 4. P0 任务：MCP 鉴权集成

已在 `MCP_AUTH_DESIGN.md` 详细说明，核心步骤：

1. 创建 MCP 鉴权中间件（`app/agent_platform/mcp/middleware.py`）
2. 创建上下文工具（`app/agent_platform/mcp/context.py`）
3. MCP 服务集成中间件
4. Agent Runtime 传递 headers

---

### 5. P1 任务：统一日志系统

#### 5.1 安装依赖

```bash
pip install structlog
```

#### 5.2 配置 structlog

**文件**: `backend/app/core/logging.py`

```python
import structlog
from structlog.stdlib import LoggerFactory

def configure_logging():
    structlog.configure(
        processors=[
            # 合并上下文变量
            structlog.contextvars.merge_contextvars,
            # 添加日志级别
            structlog.processors.add_log_level,
            # 添加时间戳
            structlog.processors.TimeStamper(fmt="iso"),
            # 添加调用位置
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            # JSON 输出
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

#### 5.3 日志中间件

```python
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 绑定请求上下文到日志
        from app.core.context import get_request_id, get_current_user_optional
        
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=get_request_id(),
            user_id=get_current_user_optional()["id"] if get_current_user_optional() else None,
            method=request.method,
            path=request.url.path,
        )
        
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=int(duration * 1000),
        )
        
        return response
```

#### 5.4 使用示例

```python
import structlog

logger = structlog.get_logger()

# 自动包含上下文（request_id, user_id）
logger.info("task_created", task_id=task.id, task_type="campaign")

# 输出:
# {
#   "event": "task_created",
#   "task_id": "xxx",
#   "task_type": "campaign",
#   "request_id": "yyy",
#   "user_id": "zzz",
#   "timestamp": "2025-01-01T12:00:00Z",
#   "level": "info"
# }
```

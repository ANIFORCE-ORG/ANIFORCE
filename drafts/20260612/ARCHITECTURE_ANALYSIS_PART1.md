# ANIFORCE 架构分析与 AI2Earn 最佳实践对比

## 第一部分：当前 ANIFORCE 鉴权系统分析

### 1. 当前实现概览

#### 1.1 鉴权流程

```
客户端请求 (带 JWT Token)
    ↓
FastAPI Endpoint
    ↓
Depends(get_current_user)  ← 每个端点单独依赖
    ↓
解析 JWT Token
    ↓
返回 user dict
    ↓
业务逻辑 (手动传递 user_id)
```

#### 1.2 核心代码

**文件**: `app/api/deps.py`

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import jwt

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    # Demo 模式
    if settings.DEMO_MODE:
        return {
            "id": "user_test_001",
            "email": "test@animagus.com",
            "name": "测试用户",
        }
    
    # 生产模式
    if credentials is None:
        raise HTTPException(status_code=401, detail="缺少认证信息")
    
    payload = jwt.decode(
        credentials.credentials,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    return {
        "id": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name"),
    }
```

**使用方式**:

```python
@router.post("/task/stream")
async def create_task_stream(
    dto: CreateTaskRequest,
    current_user = Depends(get_current_user),  # 每个端点都要写
):
    # 手动传递 user_id
    task = await service.create_task(
        user_id=current_user["id"],  # 手动传递
        dto=dto,
    )
```

### 2. 当前系统的问题

#### 问题 1: 无全局拦截器 ❌

**现状**: 
- 每个需要鉴权的端点都要手动添加 `Depends(get_current_user)`
- 没有全局中间件统一处理认证

**风险**:
- 容易遗漏鉴权（开发者忘记添加 Depends）
- 维护成本高（修改鉴权逻辑要改很多地方）
- 不一致性（不同端点可能用不同的鉴权方式）

**AI2Earn 的做法**:
```typescript
// 全局注册拦截器
providers: [
  {
    provide: APP_INTERCEPTOR,
    useClass: RequestContextInterceptor,  // 全局自动执行
  },
]
```

#### 问题 2: 无请求上下文传递 ❌

**现状**:
- `user_id` 需要在每个函数调用中手动传递
- 深层嵌套调用需要层层传递参数

**示例**:
```python
# Controller
async def create_task(current_user):
    await service.create_task(user_id=current_user["id"])

# Service
async def create_task(user_id: str):
    await repo.create(user_id=user_id)
    await another_service.do_something(user_id=user_id)

# Repository
async def create(user_id: str):
    # 使用 user_id
```

**风险**:
- 代码冗余（每个函数都要加 user_id 参数）
- 易出错（忘记传递 user_id）
- 难以重构（修改参数需要改很多地方）

**AI2Earn 的做法**:
```typescript
// Controller
async create() {
  await service.create()  // 无需传递
}

// Service
async create() {
  const user = getUser()  // 直接从上下文获取
  await repo.create(user.id)
}
```

#### 问题 3: 无统一日志上下文 ❌

**现状**:
- 没有自动注入 `request_id`、`user_id` 到日志
- 无法方便地追踪一个请求的完整调用链

**AI2Earn 的做法**:
```typescript
// 自动生成 request_id
genReqId: (req, res) => {
  const requestId = req.headers['x-request-id'] || generateId()
  res.setHeader('x-request-id', requestId)
  return requestId
}

// 日志自动包含上下文
logger.log("Task created")  // 自动附加 request_id, user_id
```

#### 问题 4: 缺少全局异常处理器 ⚠️

**现状**:
- 有基础的异常处理器，但没有统一的错误响应格式
- 没有区分业务异常和系统异常

**当前代码**:
```python
# app/main.py
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, general_exception_handler)
```

**AI2Earn 的做法**:
```typescript
{
  provide: APP_FILTER,
  useValue: new GlobalExceptionFilter({
    returnBadRequestDetails: config.enableBadRequestDetails,
  }),
}
```

#### 问题 5: 缺少监控和指标 ❌

**现状**:
- 没有请求耗时统计
- 没有 Prometheus metrics
- 没有健康检查接口（只有简单的 /health）

**AI2Earn 的做法**:
```typescript
// 全局 HTTP 指标拦截器
{
  provide: APP_INTERCEPTOR,
  useClass: HttpMetricsInterceptor,
}

// Prometheus metrics
app.use('/metrics', async (req, res) => {
  const metrics = await client.register.metrics()
  res.end(metrics)
})
```

#### 问题 6: MCP 服务无鉴权 ❌

**现状**:
- MCP 服务尚未实现
- 未来集成时需要考虑鉴权问题

**AI2Earn 的做法**:
- MCP 服务通过 headers 传递 JWT Token
- MCP 服务有独立的鉴权中间件
- 使用 AsyncLocalStorage 传递用户上下文

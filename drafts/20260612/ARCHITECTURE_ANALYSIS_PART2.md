## 第二部分：AI2Earn 架构设计最佳实践

### 1. 全局拦截器模式 ⭐⭐⭐⭐⭐

#### 1.1 设计理念

AI2Earn 使用 NestJS 的 `APP_INTERCEPTOR` 模式，在应用启动时全局注册拦截器：

```typescript
// libs/common/src/starter.ts
const providers: Provider[] = [
  {
    provide: APP_INTERCEPTOR,
    useClass: HttpMetricsInterceptor,     // HTTP 指标收集
  },
  {
    provide: APP_INTERCEPTOR,
    useClass: RequestContextInterceptor,  // 请求上下文设置
  },
  {
    provide: APP_INTERCEPTOR,
    useClass: PropagationInterceptor,     // 上下文传播
  },
  {
    provide: APP_PIPE,
    useClass: ZodValidationPipe,          // 参数校验
  },
  {
    provide: APP_INTERCEPTOR,
    useClass: ResponseInterceptor,        // 响应格式化
  },
  {
    provide: APP_FILTER,
    useClass: GlobalExceptionFilter,      // 全局异常处理
  },
]
```

#### 1.2 拦截器职责分离

**HttpMetricsInterceptor** - 监控指标收集
- 记录每个请求的耗时
- 统计请求成功/失败数量
- 暴露 Prometheus metrics

**RequestContextInterceptor** - 请求上下文设置
```typescript
export class RequestContextInterceptor implements NestInterceptor {
  public intercept(context: ExecutionContext, next: CallHandler) {
    const locale = this.parseLocale(context)
    const user = this.extractUser(context)  // 从 request.user 提取
    
    // 使用 AsyncLocalStorage 设置上下文
    return requestContext.run({ locale, user }, () => next.handle())
  }
}
```

**PropagationInterceptor** - 上下文传播
- 确保跨服务调用时传递上下文（如微服务间 RPC）

**ResponseInterceptor** - 统一响应格式
```typescript
{
  "code": 0,
  "message": "success",
  "data": { ... },
  "timestamp": 1234567890
}
```

#### 1.3 与 ANIFORCE 对比

| 维度 | ANIFORCE | AI2Earn | 推荐 |
|------|----------|---------|------|
| 拦截器注册 | 无全局拦截器 | 全局 APP_INTERCEPTOR | ✅ AI2Earn |
| 请求上下文 | 手动传递 | AsyncLocalStorage | ✅ AI2Earn |
| 指标收集 | 无 | HttpMetricsInterceptor | ✅ AI2Earn |
| 响应格式 | 手动构造 | ResponseInterceptor | ✅ AI2Earn |

---

### 2. AsyncLocalStorage 上下文传递 ⭐⭐⭐⭐⭐

#### 2.1 核心原理

```typescript
// 定义上下文存储
export const requestContext = new AsyncLocalStorage<RequestContextStore>()

interface RequestContextStore {
  locale: Locale
  user?: TokenInfo
}

// 拦截器设置上下文
export class RequestContextInterceptor {
  intercept(context, next) {
    const user = this.extractUser(context)
    return requestContext.run({ user }, () => next.handle())
  }
}

// 任何地方获取用户
export function getUser(): TokenInfo {
  const user = requestContext.getStore()?.user
  if (!user) throw new UnauthorizedException()
  return user
}
```

#### 2.2 使用示例

**Before (手动传递)**:
```typescript
// Controller
async createCampaign(userId: string, dto: CreateDto) {
  return this.service.createCampaign(userId, dto)
}

// Service
async createCampaign(userId: string, dto: CreateDto) {
  await this.repo.save(userId, dto)
  await this.notificationService.notify(userId, "created")
  await this.analyticsService.track(userId, "campaign_created")
}

// 每个函数都要传递 userId！
```

**After (上下文获取)**:
```typescript
// Controller
async createCampaign(dto: CreateDto) {
  return this.service.createCampaign(dto)  // 无需传递
}

// Service
async createCampaign(dto: CreateDto) {
  const user = getUser()  // 直接获取
  await this.repo.save(user.id, dto)
  await this.notificationService.notify("created")  // 内部自己获取
  await this.analyticsService.track("campaign_created")
}
```

#### 2.3 Python 等价实现

Python 使用 `contextvars.ContextVar`:

```python
from contextvars import ContextVar
from typing import Optional

# 定义上下文变量
_request_context: ContextVar[Optional[dict]] = ContextVar(
    "_request_context", default=None
)

# 中间件设置上下文
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        user = extract_user(request)
        _request_context.set({"user": user})
        response = await call_next(request)
        return response

# 任何地方获取用户
def get_current_user() -> dict:
    ctx = _request_context.get()
    if ctx is None or "user" not in ctx:
        raise HTTPException(401, "Not authenticated")
    return ctx["user"]
```

#### 2.4 优势总结

✅ **代码简洁**: 消除大量重复的参数传递
✅ **类型安全**: TypeScript 自动推导类型
✅ **易于测试**: Mock `getUser()` 即可
✅ **线程安全**: 基于异步上下文隔离
✅ **易于扩展**: 可以添加更多上下文信息（locale、tenant_id 等）

---

### 3. 统一日志系统 ⭐⭐⭐⭐

#### 3.1 多 Stream 日志

AI2Earn 使用 `pino` + 多 stream 输出：

```typescript
const loggers: StreamEntry[] = []

// Console 日志
if (config.logger?.console?.enable) {
  loggers.push({
    level: config.logger.console.level,
    stream: new ConsoleLogger(config.logger.console),
  })
}

// CloudWatch 日志
if (config.logger?.cloudWatch?.enable) {
  loggers.push({
    level: config.logger.cloudWatch.level,
    stream: new CloudWatchLogger(config.logger.cloudWatch),
  })
}

// 飞书告警日志
if (config.logger?.feishu?.enable) {
  loggers.push({
    level: config.logger.feishu.level,
    stream: new FeishuLogger(config.logger.feishu),
  })
}

// 组合多个 stream
pino.multistream(loggers)
```

#### 3.2 自动注入 Request ID

```typescript
genReqId: (req, res) => {
  // 优先使用客户端传递的 request-id
  const incomingRequestId = req.headers['x-request-id']
  const requestId = incomingRequestId || reqIdGenerator()
  
  // 设置到 header
  req.headers['x-request-id'] = requestId
  res.setHeader('x-request-id', requestId)
  
  return requestId
}
```

#### 3.3 结构化日志

```typescript
// 自动包含上下文
logger.log({
  message: "Task created",
  taskId: task.id,
  userId: getUser().id,  // 自动从上下文获取
  // pino 自动附加:
  // - req.id (request_id)
  // - req.method
  // - req.url
  // - responseTime
})
```

#### 3.4 ANIFORCE 建议实现

```python
# 使用 structlog + 多 handler
import structlog
from structlog.stdlib import LoggerFactory

# 配置日志
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,  # 合并上下文变量
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=LoggerFactory(),
)

# 中间件自动绑定上下文
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id", generate_id())
        
        # 绑定上下文
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            user_id=get_current_user()["id"] if authenticated else None,
            method=request.method,
            path=request.url.path,
        )
        
        response = await call_next(request)
        return response

# 使用
logger.info("task_created", task_id=task.id)
# 输出: {"event": "task_created", "task_id": "xxx", "request_id": "yyy", "user_id": "zzz"}
```

---

### 4. Prometheus Metrics ⭐⭐⭐⭐

#### 4.1 HTTP 指标拦截器

```typescript
export class HttpMetricsInterceptor implements NestInterceptor {
  private httpRequestDuration = new client.Histogram({
    name: 'http_request_duration_ms',
    help: 'Duration of HTTP requests in ms',
    labelNames: ['method', 'route', 'status_code'],
  })

  intercept(context: ExecutionContext, next: CallHandler) {
    const start = Date.now()
    const request = context.switchToHttp().getRequest()
    
    return next.handle().pipe(
      tap(() => {
        const duration = Date.now() - start
        const response = context.switchToHttp().getResponse()
        
        this.httpRequestDuration.observe(
          {
            method: request.method,
            route: request.route.path,
            status_code: response.statusCode,
          },
          duration
        )
      })
    )
  }
}
```

#### 4.2 暴露 Metrics 端点

```typescript
app.use('/metrics', async (req, res) => {
  res.set('Content-Type', client.register.contentType)
  const metrics = await client.register.metrics()
  res.end(metrics)
})
```

#### 4.3 ANIFORCE 建议实现

```python
from prometheus_client import Histogram, Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

# 定义指标
http_request_duration = Histogram(
    'http_request_duration_seconds',
    'Duration of HTTP requests',
    ['method', 'endpoint', 'status']
)

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 中间件收集指标
class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        
        http_request_duration.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).observe(duration)
        
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        return response

# 暴露端点
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

# Block 0 补充：生产边界问题与解决方案

> 更新：2026-06-12  
> 基于：AiToEarn 生产实践 + OpenAI Agents SDK 能力

---

## 1. 异常兜底

### 1.1 AiToEarn 的异常处理

**分层异常处理：**

```typescript
// 1. SDK 层异常捕获
try {
  const result = await agent.query(...)
  for await (const chunk of result) {
    // 处理
  }
} catch (error) {
  // 捕获 SDK 异常
  this.logger.error({ error, taskId }, 'SDK error')
  throw new AppException(ResponseCode.AgentRuntimeError, error.message)
}

// 2. Runtime 层异常转换
catch (error) {
  if (error instanceof AppException) {
    throw error  // 业务异常直接抛出
  }
  // 未知异常转换
  throw new AppException(ResponseCode.InternalServerError, 'Unknown error')
}

// 3. Controller 层全局异常拦截
@UseFilters(AllExceptionsFilter)
export class AgentController {
  // ...
}
```

**关键点：**

1. **SDK 错误必须捕获并转换**：不让原始 SDK 错误泄漏到用户。
2. **Task 状态必须更新**：异常时写入 `error` 状态和错误详情。
3. **事件流必须推送错误事件**：前端可以展示错误信息。

### 1.2 ANIFORCE 的异常处理设计

```python
# Runtime 层
class AgentRuntime:
    async def run_task(
        self, 
        task: AgentTask
    ) -> AsyncIterator[AgentTaskEvent]:
        try:
            # 1. 更新为 running
            await self._repo.update_status(task.task_id, AgentTaskStatus.RUNNING)
            yield AgentTaskEvent(type="runtime.started", ...)
            
            # 2. 执行 SDK
            result = Runner.run_streamed(agent, input, session=session)
            async for event in result.stream_events():
                yield self._transform_event(event)
            
            # 3. 成功完成
            await self._repo.update_status(task.task_id, AgentTaskStatus.COMPLETED)
            yield AgentTaskEvent(type="runtime.completed", ...)
            
        except asyncio.CancelledError:
            # 用户取消
            await self._repo.update_status(task.task_id, AgentTaskStatus.ABORTED)
            yield AgentTaskEvent(type="runtime.aborted", ...)
            
        except AppError as e:
            # 业务异常
            await self._repo.update_task_error(task.task_id, {
                "code": e.code.value,
                "message": e.message,
                "category": e.category.value,
            })
            await self._repo.update_status(task.task_id, AgentTaskStatus.ERROR)
            yield AgentTaskEvent(type="runtime.error", payload={
                "code": e.code.value,
                "message": e.message,
            })
            
        except Exception as e:
            # 未知异常
            self.logger.exception(f"Unexpected error in task {task.task_id}")
            await self._repo.update_task_error(task.task_id, {
                "code": "UNKNOWN_ERROR",
                "message": "An unexpected error occurred",
                "internal_message": str(e),
            })
            await self._repo.update_status(task.task_id, AgentTaskStatus.ERROR)
            yield AgentTaskEvent(type="runtime.error", payload={
                "code": "UNKNOWN_ERROR",
                "message": "An unexpected error occurred",
            })
```

**关键决策：**

- 异常时必须更新 Task 状态和 error 字段。
- 必须推送 `runtime.error` 事件。
- 用户看到的错误信息要友好，内部日志保留完整堆栈。

---

## 2. 超时控制

### 2.1 AiToEarn 的超时机制

**两层超时：**

1. **连接超时（AbortController）**

```typescript
const abortController = new AbortController()

res.on('close', () => {
  // 用户断开连接，取消任务
  abortController.abort()
})

// 传给 SDK
await agent.query(..., { signal: abortController.signal })
```

2. **任务超时（定时任务恢复）**

```typescript
// Scheduler：每 10 分钟检查一次
@Cron(CronExpression.EVERY_10_MINUTES)
async recoverTimeoutRunningTasks() {
  const timeoutMs = 30 * 60 * 1000  // 30 分钟
  const timeoutDate = new Date(Date.now() - timeoutMs)
  
  // 查询超时 running 任务
  const timeoutTasks = await repo.find({
    status: 'running',
    updatedAt: { $lt: timeoutDate },
    deletedAt: null,
  })
  
  // 批量更新为 error
  await repo.batchUpdateStatus(
    timeoutTasks.map(t => t.id),
    'error'
  )
}
```

### 2.2 ANIFORCE 的超时设计

**1. 实时取消（用户断开或主动取消）**

```python
# API 层
@router.post("/tasks/{task_id}/stream")
async def stream_task(
    task_id: str,
    user: dict = Depends(get_current_user),
    request: Request,
):
    # 监听断开
    disconnected = asyncio.Event()
    
    async def on_disconnect():
        await request.is_disconnected()
        disconnected.set()
    
    disconnect_task = asyncio.create_task(on_disconnect())
    
    try:
        async for event in runtime.run_task(task):
            if disconnected.is_set():
                # 用户断开，取消任务
                await service.cancel_task(user["id"], task_id)
                break
            yield sse_format(event)
    finally:
        disconnect_task.cancel()
```

**2. 定时任务恢复（APScheduler / Celery Beat）**

```python
# scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('interval', minutes=10)
async def recover_timeout_tasks():
    """每 10 分钟恢复超时任务"""
    timeout_ms = 30 * 60 * 1000  # 30 分钟
    timeout_date = datetime.utcnow() - timedelta(milliseconds=timeout_ms)
    
    # 查询超时任务
    timeout_tasks = await repo.list_timeout_tasks(
        status=AgentTaskStatus.RUNNING,
        updated_before=timeout_date,
    )
    
    for task in timeout_tasks:
        logger.warn(f"Task {task.task_id} timeout, marking as error")
        await repo.update_task_error(task.task_id, {
            "code": "AGENT_TIMEOUT",
            "message": "Task execution timeout",
        })
        await repo.update_status(task.task_id, AgentTaskStatus.ERROR)
```

**关键点：**

- `updatedAt` 必须在每次写入事件时更新。
- 定时任务用分布式锁避免重复执行（Redlock / DB 锁）。
- 超时后更新状态，前端下次查询时能看到。

---

## 3. 断点续传

### 3.1 断点续传的两种场景

**场景 1：SSE 断开后恢复（前端刷新）**

```python
# 前端逻辑
const lastEventId = localStorage.getItem(`task_${taskId}_last_event`)

const response = await fetch(`/agent/tasks/${taskId}/events`, {
  headers: {
    'Last-Event-ID': lastEventId || '0',
  }
})

for await (const event of parseSSE(response)) {
  // 渲染事件
  localStorage.setItem(`task_${taskId}_last_event`, event.sequence)
}
```

**后端支持：**

```python
@router.get("/tasks/{task_id}/events")
async def stream_task_events(
    task_id: str,
    user: dict = Depends(get_current_user),
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
):
    task = await service.get_task(user["id"], task_id)
    
    # 从 last_event_id 之后的事件开始推送
    after_sequence = int(last_event_id) if last_event_id else None
    
    async for event in service.stream_task_events(
        user["id"], 
        task_id, 
        after_sequence=after_sequence
    ):
        yield sse_format(event)
```

**场景 2：对话续接（session_id 复用）**

```python
# 用户在已有 session 中继续对话
task = await service.create_task(
    user_id=user["id"],
    task_type="conversation",
    session_id=existing_task.session_id,  # 复用已有 session
    input={"message": "继续上一个话题"},
)
```

### 3.2 AiToEarn 的续接实现

```typescript
// 续接对话
async resumeConversation(userId: string, originalTaskId: string, newPrompt: string) {
  // 1. 查询原任务
  const originalTask = await this.repo.getUserTask(userId, originalTaskId)
  if (!originalTask || !originalTask.sessionId) {
    throw new AppException(ResponseCode.AgentTaskNotFound)
  }
  
  // 2. 创建新任务，复用 sessionId
  const newTask = await this.repo.create({
    userId,
    sessionId: originalTask.sessionId,  // 关键：复用
    status: 'running',
    messages: [{ role: 'user', content: newPrompt }],
  })
  
  // 3. SDK 会自动加载历史上下文
  const result = await this.runtime.claudeQuery(
    systemPrompt,
    userPrompt,
    abortController,
    { sessionId: originalTask.sessionId }
  )
  
  return newTask
}
```

---

## 4. Tracing 机制

### 4.1 OpenAI Agents SDK 的 Tracing

**内置能力：**

```python
from agents import Runner, trace, set_tracing_disabled, flush_traces

# 1. 默认开启，自动上报到 OpenAI Traces 平台
result = Runner.run_streamed(agent, input)

# 2. 自定义 trace
with trace("Campaign Planning Workflow") as t:
    t.set_metadata({"user_id": user_id, "task_id": task_id})
    
    result = Runner.run_streamed(agent, input)
    async for event in result.stream_events():
        yield event

# 3. 强制刷新（长任务 / 异步队列）
try:
    with trace("background_job"):
        result = Runner.run_sync(agent, input)
finally:
    flush_traces()  # 确保立即上报

# 4. 禁用 tracing
set_tracing_disabled(True)
```

**自动记录的 Span：**

- `agent_span()` - Agent 执行
- `generation_span()` - LLM 生成
- `function_span()` - 工具调用
- `guardrail_span()` - 防护栏
- `handoff_span()` - Agent 切换

**敏感数据控制：**

```python
from agents import RunConfig

result = Runner.run_streamed(
    agent, 
    input,
    run_config=RunConfig(
        trace_include_sensitive_data=False  # 不记录 LLM 输入输出
    )
)
```

### 4.2 ANIFORCE 的 Tracing 设计

**方案 1：使用 OpenAI 原生 Tracing**

```python
# runtime.py
from agents import Runner, trace, flush_traces

class AgentRuntime:
    async def run_task(self, task: AgentTask) -> AsyncIterator[AgentTaskEvent]:
        with trace(f"Agent Task {task.task_id}") as t:
            t.set_metadata({
                "task_id": task.task_id,
                "user_id": task.user_id,
                "task_type": task.task_type,
            })
            
            try:
                result = Runner.run_streamed(agent, input, session=session)
                async for event in result.stream_events():
                    yield self._transform_event(event)
            finally:
                # 长任务立即上报
                flush_traces()
```

**方案 2：自定义 Trace Processor（推送到自己的系统）**

```python
from agents import add_trace_processor, TraceProcessor

class CustomTraceProcessor(TraceProcessor):
    async def export_traces(self, traces):
        for trace in traces:
            # 推送到自己的日志 / 监控系统
            await self.logger.info({
                "trace_id": trace.trace_id,
                "workflow_name": trace.workflow_name,
                "spans": [s.to_dict() for s in trace.spans],
            })

# 启动时注册
add_trace_processor(CustomTraceProcessor())
```

**关键决策：**

- 开发环境：使用 OpenAI Traces 平台（免费）。
- 生产环境：可选禁用或推送到内部系统。
- 敏感数据：默认 `trace_include_sensitive_data=False`。

---

## 5. 日志系统

### 5.1 AiToEarn 的日志实践

**结构化日志：**

```typescript
// 使用 NestJS Logger
this.logger.debug({ taskId, sessionId, chunk }, `Task ${taskId} received message`)
this.logger.error({ error, taskId }, `Task ${taskId} failed`)
this.logger.warn({ taskId, code }, `Claude process exited with code ${code}`)
```

**日志装饰器：**

```typescript
@WithLoggerContext()  // 自动注入 requestId / userId
async createTask(...) {
  // 日志自动带上下文
}
```

### 5.2 ANIFORCE 的日志设计

**1. 使用 loguru（Python 简洁日志）**

```python
from loguru import logger

# 配置（启动时）
logger.remove()  # 移除默认 handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | {extra[task_id]} | {extra[user_id]} | <level>{message}</level>",
    level="DEBUG",
)
logger.add(
    "logs/agent_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {extra[task_id]} | {extra[user_id]} | {message}",
    level="INFO",
    serialize=True,  # JSON 格式
)

# 绑定上下文
logger_ctx = logger.bind(task_id=task.task_id, user_id=task.user_id)

# 结构化日志
logger_ctx.info(f"Task started: {task.task_type}")
logger_ctx.debug(f"SDK event received: {event.type}")
logger_ctx.error(f"Task failed: {error.code} - {error.message}")
```

**2. 日志分级：**

- `DEBUG`: SDK 事件、工具调用参数
- `INFO`: Task 状态变化、Runtime 启动
- `WARN`: 超时恢复、重试
- `ERROR`: 异常、失败

**3. 日志输出：**

- 开发环境：Console（彩色）
- 生产环境：JSON Lines → 文件 / ELK / Loki

**4. 敏感信息脱敏：**

```python
def sanitize_message(message: dict) -> dict:
    """脱敏敏感字段"""
    if "password" in message:
        message["password"] = "***"
    if "api_key" in message:
        message["api_key"] = message["api_key"][:8] + "..."
    return message

logger.debug("tool_call", args=sanitize_message(tool_args))
```

---

## 6. 断线重连与状态恢复

### 6.1 SSE 断线重连

**前端实现：**

```typescript
function connectSSE(taskId: string) {
  const lastEventId = localStorage.getItem(`task_${taskId}_last_event`) || '0'
  
  const eventSource = new EventSource(
    `/api/v1/agent/tasks/${taskId}/events`,
    { 
      headers: { 'Last-Event-ID': lastEventId }
    }
  )
  
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    localStorage.setItem(`task_${taskId}_last_event`, data.sequence)
    // 渲染事件
  }
  
  eventSource.onerror = () => {
    eventSource.close()
    // 3秒后重连
    setTimeout(() => connectSSE(taskId), 3000)
  }
}
```

**后端支持增量推送：**

```python
@router.get("/tasks/{task_id}/events")
async def stream_events(
    task_id: str,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
):
    after_sequence = int(last_event_id) if last_event_id else None
    
    # 1. 先推送历史事件
    history = await repo.list_events(task_id, after_sequence=after_sequence)
    for event in history:
        yield sse_format(event)
    
    # 2. 如果任务未完成，继续推送实时事件
    task = await repo.get_by_id(task_id)
    if task.status in [AgentTaskStatus.PENDING, AgentTaskStatus.RUNNING]:
        async for event in realtime_stream(task_id):
            yield sse_format(event)
```

### 6.2 Task 状态恢复

**刷新页面后恢复 UI：**

```typescript
async function recoverTaskUI(taskId: string) {
  // 1. 获取 task 状态
  const task = await fetch(`/api/v1/agent/tasks/${taskId}`)
  
  // 2. 获取所有事件
  const events = await fetch(`/api/v1/agent/tasks/${taskId}/events`)
  
  // 3. 重建 UI
  for (const event of events) {
    if (event.type === 'message.updated') {
      appendToUI(event.payload.delta)
    }
    if (event.type === 'tool_call.started') {
      showToolStatus(event.payload.tool, 'running')
    }
    if (event.type === 'tool_call.completed') {
      showToolStatus(event.payload.tool, 'completed')
    }
  }
  
  // 4. 如果未完成，继续监听
  if (task.status === 'running') {
    connectSSE(taskId)
  }
}
```

---

## 7. 生产边界检查清单

### 7.1 异常兜底

- [ ] SDK 异常必须捕获并转换为 AppError
- [ ] 异常时必须更新 Task 状态为 ERROR
- [ ] 异常时必须推送 `runtime.error` 事件
- [ ] 用户看到友好错误，日志保留完整堆栈
- [ ] 全局异常 handler 捕获所有未处理异常

### 7.2 超时控制

- [ ] SSE 断开时取消任务（AbortController / asyncio.cancel）
- [ ] 定时任务每 10 分钟恢复超时 running 任务
- [ ] `updatedAt` 在写入事件时更新
- [ ] 定时任务使用分布式锁避免重复执行
- [ ] 超时阈值可配置（默认 30 分钟）

### 7.3 断点续传

- [ ] SSE 支持 `Last-Event-ID` 增量推送
- [ ] 事件有序号 `sequence`
- [ ] 前端缓存 `last_event_id`
- [ ] 刷新页面后可恢复 UI
- [ ] 对话续接支持 `session_id` 复用

### 7.4 Tracing

- [ ] 开发环境开启 OpenAI Tracing
- [ ] 生产环境可选禁用或推送到内部系统
- [ ] 敏感数据不记录（`trace_include_sensitive_data=False`）
- [ ] 长任务调用 `flush_traces()`
- [ ] Trace 包含 `task_id`、`user_id`、`task_type` 元数据

### 7.5 日志

- [ ] 使用结构化日志（structlog）
- [ ] 日志包含 `task_id`、`user_id` 上下文
- [ ] 敏感信息脱敏
- [ ] 日志分级：DEBUG / INFO / WARN / ERROR
- [ ] 生产环境输出 JSON Lines

### 7.6 状态恢复

- [ ] 事件持久化到 DB
- [ ] 前端可从事件流重建 UI
- [ ] 任务状态可查询
- [ ] SSE 断线自动重连
- [ ] 服务重启后未完成任务可恢复或标记失败

---

## 8. Block 1-8 补充任务

**Block 1（Task 生命周期）：**
- [ ] Task 包含 `error` 字段
- [ ] 事件包含 `sequence` 序号
- [ ] Repository 支持 `after_sequence` 增量查询
- [ ] SSE 支持 `Last-Event-ID`

**Block 2（异常体系）：**
- [ ] 定义 `AGENT_TIMEOUT` 错误码
- [ ] 定义 `AGENT_ABORTED` 错误码
- [ ] 实现全局异常 handler

**Block 3（Runtime）：**
- [ ] 捕获 SDK 异常并转换
- [ ] 监听用户断开并取消任务
- [ ] 集成 OpenAI Tracing

**Block 7（队列/定时任务）：**
- [ ] 实现超时恢复定时任务
- [ ] 使用分布式锁

**Block 8（可观测性）：**
- [ ] 配置 structlog
- [ ] 实现日志上下文绑定
- [ ] 敏感信息脱敏

---

> 下一步：在实现各 Block 时，严格遵循本规范，确保生产可用。

# Block 0 补充：用户鉴权与权限隔离

> 更新：2026-06-12  
> 基于：AiToEarn 鉴权架构 + ANIFORCE 当前实现

---

## 1. AiToEarn 的鉴权方案

### 1.1 多层鉴权机制

AiToEarn 使用统一的 `AitoearnAuthGuard`，支持三种认证方式：

```typescript
// 1. Internal Token（服务间调用）
if (token === this.options.internalToken) {
  return true
}

// 2. API Key（外部服务）
const apiKey = request.headers['x-api-key']
if (apiKey) {
  request['user'] = await this.options.getTokenInfoByApiKey(apiKey)
  return true
}

// 3. JWT Bearer Token（用户）
const payload = await this.jwtService.verifyAsync<TokenPayload>(token)
request['user'] = await this.options.getTokenInfo(payload)
```

### 1.2 装饰器控制

```typescript
// Controller 方法上使用
@GetToken() token: TokenInfo     // 获取当前用户信息
@Public()                         // 标记为公开接口
@Internal()                       // 标记为内部接口
```

### 1.3 Repository 层权限隔离

**关键原则：Repository 方法直接接收 `userId`，而不是从全局上下文获取。**

```typescript
// ❌ 不好的做法
async getTask(taskId: string) {
  return await this.model.findById(taskId)
}

// ✅ 正确做法
async getUserTask(userId: string, taskId: string) {
  return await this.findOne({ userId, _id: taskId, deletedAt: null })
}

async getUserTasksWithPagination(userId: string, params: Pagination) {
  const filter = { userId, deletedAt: null }
  return await this.findWithPagination({ filter, ...params })
}
```

**核心优势：**

- 不会误查其他用户数据。
- Repository 可独立测试。
- 不依赖 HTTP 上下文。

### 1.4 Service 层校验

```typescript
// Service 层从 Controller 接收 userId，传给 Repository
async getTask(userId: string, taskId: string) {
  const task = await this.contentGenerateRepository.getUserTask(userId, taskId)
  if (!task) {
    throw new AppException(ResponseCode.AgentTaskNotFound)
  }
  return task
}

async deleteTask(userId: string, taskId: string) {
  const task = await this.contentGenerateRepository.getUserTask(userId, taskId)
  if (!task) {
    throw new AppException(ResponseCode.AgentTaskNotFound)
  }
  await this.contentGenerateRepository.softDeleteTask(userId, taskId)
}
```

**Controller 调用：**

```typescript
@Get('tasks/:taskId')
async getContentGenerationTask(
  @GetToken() token: TokenInfo,
  @Param('taskId') taskId: string,
) {
  const task = await this.agentService.getTask(token.id, taskId)
  return ContentGenerationTaskVo.create(task)
}
```

---

## 2. ANIFORCE 当前实现

### 2.1 当前鉴权方式

```python
# backend/app/api/deps.py
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    settings = get_settings()
    
    # Demo 模式
    if settings.DEMO_MODE or credentials is None:
        return {
            "id": "user_test_001",
            "email": "test@animagus.com",
            "name": "测试用户",
        }
    
    # 生产模式
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

### 2.2 API 层使用

```python
@router.get("/projects")
async def list_projects(
    user: dict = Depends(get_current_user),
    service: ProjectService = Depends(get_project_service),
):
    return await service.list_by_user(user["id"])
```

---

## 3. ANIFORCE Agent 平台的鉴权设计

### 3.1 核心原则

```text
1. Repository 方法必须显式接收 user_id
2. 不允许 Repository 从全局上下文获取 user_id
3. Service 从 API 接收 user_id，传给 Repository
4. 所有用户数据查询都加 user_id 过滤
```

### 3.2 AgentTaskRepository 设计

```python
class AgentTaskRepository(ABC):
    @abstractmethod
    async def create(self, task: AgentTask) -> AgentTask:
        """创建任务（task 已包含 user_id）"""
    
    @abstractmethod
    async def get_user_task(self, user_id: str, task_id: str) -> Optional[AgentTask]:
        """查询用户任务（必须同时匹配 user_id 和 task_id）"""
    
    @abstractmethod
    async def list_user_tasks(
        self, 
        user_id: str, 
        limit: int = 20,
        offset: int = 0
    ) -> List[AgentTask]:
        """查询用户任务列表"""
    
    @abstractmethod
    async def append_event(self, user_id: str, event: AgentTaskEvent) -> None:
        """追加事件（校验 task 归属）"""
    
    @abstractmethod
    async def list_user_task_events(
        self, 
        user_id: str,
        task_id: str,
        after_sequence: Optional[int] = None
    ) -> List[AgentTaskEvent]:
        """查询用户任务事件"""
```

### 3.3 内存实现示例

```python
class MemoryAgentTaskRepository(AgentTaskRepository):
    def __init__(self):
        self._tasks: Dict[str, AgentTask] = {}
        self._events: Dict[str, List[AgentTaskEvent]] = {}
    
    async def get_user_task(self, user_id: str, task_id: str) -> Optional[AgentTask]:
        task = self._tasks.get(task_id)
        if not task:
            return None
        # 关键：校验归属
        if task.user_id != user_id:
            return None
        return task
    
    async def list_user_tasks(
        self, 
        user_id: str, 
        limit: int = 20,
        offset: int = 0
    ) -> List[AgentTask]:
        # 关键：只返回该用户的任务
        user_tasks = [
            task for task in self._tasks.values()
            if task.user_id == user_id
        ]
        return sorted(
            user_tasks, 
            key=lambda t: t.created_at, 
            reverse=True
        )[offset:offset + limit]
```

### 3.4 Service 层设计

```python
class AgentTaskService:
    def __init__(self, repo: AgentTaskRepository):
        self._repo = repo
    
    async def get_task(self, user_id: str, task_id: str) -> AgentTask:
        """获取任务（含权限校验）"""
        task = await self._repo.get_user_task(user_id, task_id)
        if not task:
            raise AppError(
                code=AgentErrorCode.TASK_NOT_FOUND,
                message="Task not found or access denied"
            )
        return task
    
    async def list_tasks(
        self, 
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[AgentTask]:
        """查询任务列表"""
        return await self._repo.list_user_tasks(user_id, limit, offset)
    
    async def cancel_task(self, user_id: str, task_id: str) -> None:
        """取消任务（含权限校验）"""
        task = await self._repo.get_user_task(user_id, task_id)
        if not task:
            raise AppError(
                code=AgentErrorCode.TASK_NOT_FOUND,
                message="Task not found or access denied"
            )
        if task.status not in [AgentTaskStatus.PENDING, AgentTaskStatus.RUNNING]:
            raise AppError(
                code=AgentErrorCode.TASK_STATUS_INVALID,
                message="Task cannot be cancelled in current status"
            )
        await self._repo.update_status(task_id, AgentTaskStatus.ABORTED)
```

### 3.5 API 层设计

```python
@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
):
    """获取任务详情"""
    task = await service.get_task(user["id"], task_id)
    return {"task": task}

@router.get("/tasks")
async def list_tasks(
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
    limit: int = 20,
    offset: int = 0,
):
    """查询任务列表"""
    tasks = await service.list_tasks(user["id"], limit, offset)
    return {"tasks": tasks, "total": len(tasks)}

@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
):
    """取消任务"""
    await service.cancel_task(user["id"], task_id)
    return {"message": "Task cancelled"}
```

---

## 4. 兼容层的权限处理

当前前端使用 `/agent/chat/sessions`，内部实现为 Task：

```python
@router.post("/agent/chat/sessions")
async def create_chat_session(
    req: AgentChatSessionCreateRequest,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
):
    """创建对话（内部创建 conversation Task）"""
    task = await service.create_task(
        user_id=user["id"],
        task_type="conversation",
        title=req.title or "新对话",
    )
    # 返回兼容格式
    return {
        "id": task.task_id,
        "title": task.title,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }

@router.get("/agent/chat/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    service: AgentTaskService = Depends(get_agent_task_service),
):
    """查询对话（内部查询 Task + events）"""
    task = await service.get_task(user["id"], session_id)
    events = await service.list_task_events(user["id"], session_id)
    
    # 转换为前端期望的 messages 格式
    messages = convert_events_to_messages(events)
    
    return {
        "session": {
            "id": task.task_id,
            "title": task.title,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        },
        "messages": messages,
    }
```

---

## 5. 关键安全原则

### 5.1 永远不信任客户端输入

```python
# ❌ 错误：从请求体获取 user_id
@router.get("/tasks/{task_id}")
async def get_task(task_id: str, user_id: str):  # 危险！
    task = await repo.get_by_id(task_id)
    if task.user_id != user_id:
        raise HTTPException(403)
    return task

# ✅ 正确：从 JWT token 获取 user_id
@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    user: dict = Depends(get_current_user),
):
    task = await service.get_task(user["id"], task_id)
    return task
```

### 5.2 Repository 必须隔离用户数据

```python
# ❌ 错误：Repository 返回所有用户数据，Service 过滤
async def list_tasks(self) -> List[AgentTask]:
    return list(self._tasks.values())

# ✅ 正确：Repository 只返回指定用户数据
async def list_user_tasks(self, user_id: str) -> List[AgentTask]:
    return [t for t in self._tasks.values() if t.user_id == user_id]
```

### 5.3 事件流也要校验归属

```python
async def stream_task_events(
    self, 
    user_id: str, 
    task_id: str
) -> AsyncIterator[AgentTaskEvent]:
    # 先校验 task 归属
    task = await self._repo.get_user_task(user_id, task_id)
    if not task:
        raise AppError(AgentErrorCode.TASK_NOT_FOUND)
    
    # 再推送事件
    async for event in self._stream_events(task_id):
        yield event
```

---

## 6. 测试要求

每个 Repository 实现必须包含权限隔离测试：

```python
async def test_get_user_task_isolation():
    repo = MemoryAgentTaskRepository()
    
    # 用户 A 创建任务
    task_a = await repo.create(AgentTask(
        task_id="task_001",
        user_id="user_a",
        ...
    ))
    
    # 用户 B 尝试访问用户 A 的任务
    task = await repo.get_user_task("user_b", "task_001")
    assert task is None  # 必须返回 None
    
    # 用户 A 可以访问自己的任务
    task = await repo.get_user_task("user_a", "task_001")
    assert task is not None
```

---

## 7. Block 1 补充任务

在 Block 1 实现 Task 生命周期时，必须同时实现：

- [ ] Repository 所有方法接收 `user_id` 参数
- [ ] Service 从 API 接收 `user_id`，传给 Repository
- [ ] API 从 `get_current_user` 获取 `user_id`
- [ ] 编写权限隔离测试

---

## 8. 总结

**AiToEarn 的核心经验：**

1. **Repository 显式接收 user_id**：不依赖全局上下文，可独立测试。
2. **查询时过滤 user_id**：`{ userId, _id: taskId, deletedAt: null }`。
3. **Service 校验归属**：先查询，校验归属，再操作。
4. **不返回 403**：Task 不存在和无权限都返回 404，避免信息泄露。

**ANIFORCE 采纳：**

- 所有 `AgentTaskRepository` 方法显式接收 `user_id`。
- `get_user_task(user_id, task_id)` 同时匹配两个条件。
- 不允许 `get_by_id(task_id)` 这种无用户过滤的方法。
- Service 不需要二次校验归属，直接依赖 Repository 过滤。

---

> 下一步：在 Block 1 实现时，严格遵循本规范。

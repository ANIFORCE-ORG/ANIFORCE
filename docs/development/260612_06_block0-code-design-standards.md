# Block 0：ANIFORCE Agent 代码开发规范

> 版本：v2.0.0  
> 更新：2026-06-12  
> 核心原则：**Task 是唯一模型，对话是 Task 的一种表现形式。**

---

## 1. 核心设计决策：Task 统一模型

### 1.1 为什么 Task 是唯一模型

**AiToEarn 的经验：**

AiToEarn 没有单独的 Chat 系统，所有 Agent 交互都建模为 `ContentGenerationTask`。

```typescript
ContentGenerationTask {
  taskId: string
  userId: string
  sessionId?: string           // Claude SDK session
  status: running | completed | error | aborted | requires_action
  messages: Array<AgentMessage>
  title?: string
  rating?: number
  result?: TaskResult
  publicShareToken?: string
}
```

**ANIFORCE 的采纳：**

```python
AgentTask {
  task_id: str
  user_id: str
  task_type: str               # conversation / campaign_planning / asset_review
  status: AgentTaskStatus
  session_id: Optional[str]    # OpenAI SDK Session
  title: str
  events: List[AgentTaskEvent]
  result: Optional[dict]
  error: Optional[dict]
  rating: Optional[int]
  public_share_token: Optional[str]
  created_at: datetime
  updated_at: datetime
}
```

### 1.2 对话能力如何提供

**不是靠单独的 ChatSession 实体，而是靠：**

```text
task_type = "conversation"
+ session_id（OpenAI SDK 管理上下文）
+ events（完整事件流）
```

**用户体验仍然是对话：**

- 用户发消息 → 创建/继续 conversation Task → Agent 回复 → 前端渲染成聊天气泡。
- 刷新页面 → 查询 Task events → 恢复消息列表。
- 续聊 → 复用 `session_id`，SDK 自动管理上下文。

### 1.3 当前前端兼容策略

**当前 API：**

```text
POST   /agent/chat/sessions
GET    /agent/chat/sessions
GET    /agent/chat/sessions/{id}
POST   /agent/chat/sessions/{id}/stream
```

**兼容方案：**

```text
保留这些 API 作为兼容层
内部实现改为 Task：
  - create session → 创建 task_type=conversation 的 Task
  - stream chat → 运行该 Task
  - get session → 查询 Task + events
```

**未来统一 API：**

```text
POST   /agent/tasks
GET    /agent/tasks
GET    /agent/tasks/{id}
GET    /agent/tasks/{id}/events        # SSE
POST   /agent/tasks/{id}/cancel
POST   /agent/tasks/{id}/resume
```

---

## 2. 分层架构与职责边界

### 2.1 层级结构

```text
┌─────────────────────────────────────────┐
│ API Layer (FastAPI routes)              │
│ 职责：路由、参数绑定、响应序列化           │
│ 禁止：业务逻辑、直接访问 DB               │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ Service Layer                            │
│ 职责：业务编排、权限校验                  │
│ 禁止：直接写 SQL、硬编码配置              │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ Platform Layer (agent_platform/)         │
│ 职责：Runtime、MCP、队列、Skill、Session   │
│ 独立性：逻辑独立，未来可拆服务              │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ Repository Layer                         │
│ 职责：数据访问                            │
│ 禁止：业务逻辑                            │
└─────────────────────────────────────────┘
```

### 2.2 核心原则

- API 层不写业务。
- Service 不关心 DB 细节。
- Platform 不依赖具体业务。
- Repository 只做 CRUD。

---

## 3. 目录结构

```text
backend/app/
  agent_platform/              # Platform 层（可独立拆服务）
    __init__.py
    errors.py                  # AppError / ErrorCode
    models.py                  # AgentTask / AgentTaskEvent
    events.py                  # 事件定义和转换
    runtime.py                 # AgentRuntime（封装 SDK）
    
    adapters/
      openai_adapter.py        # OpenAI SDK adapter
    
    repositories/
      base.py                  # Repository 接口
      memory.py                # 内存实现
      postgres.py              # PostgreSQL 实现
    
    mcp/
      registry.py              # MCP 工具注册
      schemas.py
    
    queue/
      base.py                  # TaskQueue 接口
      in_process.py            # 进程内队列
    
    skills/
      registry.py              # Skill 注册
    
    sessions/
      manager.py               # Session 管理
  
  agents/                      # Agent 编排层
    marketing_agent.py
    prompts/
      marketing.py
    skills/
      campaign-planning/SKILL.md
      project-analysis/SKILL.md
  
  services/                    # Service 层
    agent_task_service.py
  
  api/                         # API 层
    v1/
      agent/
        routes.py              # FastAPI routes
        schemas.py             # Pydantic request/response
```

**边界原则：**

- `agent_platform/` 不依赖 `agents/` 和 `services/`。
- `agents/` 可以依赖 `agent_platform/` 和 `services/`。
- `api/` 只依赖 `services/`，不直接调 `agent_platform/`。

---

## 4. 核心模型定义

### 4.1 AgentTask

```python
class AgentTask:
    task_id: str                       # 任务 ID
    user_id: str                       # 用户 ID
    task_type: str                     # conversation / campaign_planning / asset_review
    status: AgentTaskStatus            # 任务状态
    session_id: Optional[str]          # OpenAI SDK Session ID
    title: str                         # 任务标题
    input: Optional[dict]              # 任务输入
    result: Optional[dict]             # 结构化结果
    error: Optional[dict]              # 错误详情
    rating: Optional[int]              # 用户评分
    rating_comment: Optional[str]      # 评分评论
    public_share_token: Optional[str]  # 公开分享 token
    created_at: datetime
    updated_at: datetime
```

### 4.2 AgentTaskStatus

```python
class AgentTaskStatus(Enum):
    PENDING = "pending"                # 已创建，等待执行
    RUNNING = "running"                # 执行中
    COMPLETED = "completed"            # 成功完成
    ERROR = "error"                    # 失败
    ABORTED = "aborted"                # 用户取消
    REQUIRES_ACTION = "requires_action"  # 等待用户动作
```

**状态转换：**

```text
PENDING → RUNNING → COMPLETED
              ↓
            ERROR
              ↓
           ABORTED

RUNNING → REQUIRES_ACTION → RUNNING
```

### 4.3 AgentTaskEvent

```python
class AgentTaskEvent:
    event_id: str                      # 事件 ID
    task_id: str                       # 归属任务
    event_type: str                    # 事件类型
    payload: dict                      # 事件载荷
    sequence: int                      # 序号（从 0 开始）
    created_at: datetime
```

**核心事件类型：**

```python
EVENT_TYPES = {
    "runtime.started",          # 任务开始
    "message.started",          # 消息开始
    "message.updated",          # 消息增量（delta）
    "message.completed",        # 消息完成
    "tool_call.started",        # 工具调用开始
    "tool_call.completed",      # 工具调用完成
    "tool_call.error",          # 工具调用失败
    "runtime.completed",        # 任务完成
    "runtime.error",            # 运行时错误
    "runtime.aborted",          # 用户取消
}
```

---

## 5. 命名规范

| 类型 | 规则 | 示例 |
|---|---|---|
| 模型 | PascalCase | `AgentTask`, `AgentTaskEvent` |
| 服务 | PascalCase + Service | `AgentTaskService` |
| Repository | PascalCase + Repository | `AgentTaskRepository` |
| 状态枚举 | PascalCase + Status | `AgentTaskStatus` |
| 错误码 | UPPER_SNAKE_CASE | `TASK_NOT_FOUND` |
| DTO | PascalCase + Request/Response | `CreateTaskRequest` |
| 函数 | snake_case | `create_task` |
| 私有方法 | `_` 前缀 | `_transform_event` |
| 常量 | UPPER_SNAKE_CASE | `DEFAULT_TIMEOUT` |
| 包 | snake_case | `agent_platform` |

---

## 6. 抽象与扩展性设计

### 6.1 接口优先

```python
# ❌ 直接依赖实现
from sqlalchemy import create_engine
engine = create_engine("postgresql://...")

# ✅ 先定义接口
class AgentTaskRepository(ABC):
    @abstractmethod
    async def create(self, task: AgentTask) -> AgentTask: ...
    
    @abstractmethod
    async def get_by_id(self, task_id: str) -> Optional[AgentTask]: ...
    
    @abstractmethod
    async def update_status(
        self, 
        task_id: str, 
        status: AgentTaskStatus
    ) -> None: ...

# 再提供实现
class PostgreSQLAgentTaskRepository(AgentTaskRepository):
    ...

class MemoryAgentTaskRepository(AgentTaskRepository):
    ...
```

### 6.2 配置外部化

```python
# ❌ 硬编码
timeout_ms = 600000

# ✅ 配置化
from app.config import settings
timeout_ms = settings.agent.task_timeout_ms
```

### 6.3 SDK 适配层

```python
# ❌ 业务代码直接调 SDK
from agents import Agent, Runner
result = Runner.run_streamed(agent, input, session=session)

# ✅ 封装 Runtime
class AgentRuntime:
    def __init__(self, sdk_adapter: SDKAdapter):
        self._adapter = sdk_adapter
    
    async def run_task(
        self, 
        task: AgentTask
    ) -> AsyncIterator[AgentTaskEvent]:
        # 内部调 SDK，但业务层不感知
        ...
```

**为什么需要适配层：**

- 业务代码不直接依赖 OpenAI SDK。
- 未来可以换 SDK（Claude / Gemini / 自研）。
- 统一事件格式。
- 统一错误处理。

---

## 7. 事件驱动架构

### 7.1 为什么用事件而不是消息

```python
# ❌ 只记录消息
messages = [
    {"role": "user", "content": "帮我分析项目"},
    {"role": "assistant", "content": "好的，分析中..."}
]

# ✅ 记录事件
events = [
    {"type": "runtime.started", "timestamp": "2026-06-12T10:00:00Z"},
    {"type": "message.started", "role": "assistant"},
    {"type": "tool_call.started", "tool": "get_project_info", "args": {"project_id": "123"}},
    {"type": "tool_call.completed", "result": {"name": "Game X", "budget": 10000}},
    {"type": "message.updated", "delta": "根据项目数据，"},
    {"type": "message.updated", "delta": "建议投放..."},
    {"type": "message.completed", "content": "根据项目数据，建议投放..."},
    {"type": "runtime.completed", "result": {...}}
]
```

**优势：**

- **可恢复**：刷新页面后，前端读取事件流，重建 UI 状态。
- **可追溯**：每一步都有时间戳和序号。
- **可扩展**：新增事件类型不影响旧逻辑。
- **可调试**：完整记录 Agent 执行过程。
- **支持多种渲染**：同一事件流可以渲染成聊天 UI、任务面板、日志视图。

### 7.2 事件设计原则

- 事件不可变。
- 事件有序（sequence）。
- 事件有明确 schema。
- 事件可独立解释。

---

## 8. 错误体系

### 8.1 错误分类

```python
class ErrorCategory(Enum):
    TASK_ERROR = "task"                # 任务相关错误
    RUNTIME_ERROR = "runtime"          # 运行时错误
    UPSTREAM_ERROR = "upstream"        # 上游服务错误
    VALIDATION_ERROR = "validation"    # 参数校验错误
    BUSINESS_ERROR = "business"        # 业务错误
```

### 8.2 统一错误码

```python
class AgentErrorCode(Enum):
    # Task 错误
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_STATUS_INVALID = "TASK_STATUS_INVALID"
    
    # Runtime 错误
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_ABORTED = "AGENT_ABORTED"
    SDK_ERROR = "SDK_ERROR"
    
    # 上游错误
    UPSTREAM_NETWORK_ERROR = "UPSTREAM_NETWORK_ERROR"
    UPSTREAM_RATE_LIMIT = "UPSTREAM_RATE_LIMIT"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    
    # 业务错误
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    INSUFFICIENT_BUDGET = "INSUFFICIENT_BUDGET"
    PLATFORM_NOT_SUPPORTED = "PLATFORM_NOT_SUPPORTED"
```

### 8.3 错误类

```python
class AppError(Exception):
    def __init__(
        self,
        code: AgentErrorCode,
        message: str,
        category: ErrorCategory = ErrorCategory.RUNTIME_ERROR,
        data: Optional[dict] = None
    ):
        self.code = code
        self.message = message
        self.category = category
        self.data = data
```

### 8.4 错误处理

```python
def get_error_payload(error: AppError) -> dict:
    return {
        "code": error.code.value,
        "message": error.message,
        "category": error.category.value,
        "data": error.data or {}
    }
```

---

## 9. Repository 规范

### 9.1 方法前缀

| 前缀 | 返回 | 示例 |
|---|---|---|
| `get` | 单个或 None | `get_by_id` |
| `list` | 列表 | `list_by_user` |
| `create` | 创建对象 | `create` |
| `update` | None | `update_status` |
| `delete` | None | `delete` |
| `count` | int | `count_by_status` |
| `exists` | bool | `exists_by_id` |

### 9.2 Repository 接口

```python
class AgentTaskRepository(ABC):
    @abstractmethod
    async def create(self, task: AgentTask) -> AgentTask:
        """创建任务"""
    
    @abstractmethod
    async def get_by_id(self, task_id: str) -> Optional[AgentTask]:
        """根据 ID 查询任务"""
    
    @abstractmethod
    async def list_by_user(
        self, 
        user_id: str, 
        limit: int = 20,
        offset: int = 0
    ) -> List[AgentTask]:
        """查询用户任务列表"""
    
    @abstractmethod
    async def update_status(
        self, 
        task_id: str, 
        status: AgentTaskStatus
    ) -> None:
        """更新任务状态"""
    
    @abstractmethod
    async def append_event(self, event: AgentTaskEvent) -> None:
        """追加事件"""
    
    @abstractmethod
    async def list_events(
        self, 
        task_id: str,
        after_sequence: Optional[int] = None
    ) -> List[AgentTaskEvent]:
        """查询任务事件"""
```

---

## 10. OpenAI Agents SDK 集成

### 10.1 SDK Session vs 产品 Task

**OpenAI SDK Session：**

```python
from agents import SQLiteSession

# SDK Session 管理模型上下文
session = SQLiteSession(session_id, db_path="chat.db")
```

**作用：**

- 自动管理多轮对话历史。
- 传递历史消息给模型。
- 不是产品的 Task 实体。

**AgentTask.session_id：**

- 指向 SDK Session ID。
- 一个 Task 可以复用已有 session_id（续聊）。
- 也可以创建新 session_id（新对话）。

### 10.2 流式执行

```python
from agents import Agent, Runner

result = Runner.run_streamed(agent, input, session=session)

async for event in result.stream_events():
    if event.type == "raw_response_event":
        # 原始 LLM 事件
        delta = event.data.delta
    elif event.type == "run_item_stream_event":
        # 工具调用、输出等
        item = event.item
```

### 10.3 事件类型

```python
StreamEvent = (
    RawResponsesStreamEvent |      # LLM 原始事件
    RunItemStreamEvent |           # 工具调用、输出
    AgentUpdatedStreamEvent        # Agent 切换
)
```

---

## 11. 验收标准

每个 Block 完成后，必须能回答：

- **边界清晰**：这个模块的职责是什么？
- **依赖明确**：它依赖哪些模块？
- **能力稳定**：它为哪些模块提供能力？
- **接口稳定**：它的接口是否稳定？
- **可测试**：它是否可以独立测试？
- **可替换**：它的实现是否可以替换？

---

## 12. 关键原则总结

1. **Task 是唯一模型**：对话是 Task，营销任务也是 Task。
2. **事件驱动**：记录事件流，不只是消息列表。
3. **状态机清晰**：每个状态转换都有明确语义。
4. **接口优先**：先定义抽象，再提供实现。
5. **SDK 隔离**：业务层不直接依赖 OpenAI SDK。
6. **逻辑独立**：agent_platform/ 可以独立拆服务。
7. **配置外部化**：不硬编码常量。
8. **错误分类**：统一错误码和错误处理。

---

> 下一步：参照本规范，实现 Block 1 - Task 生命周期基建。

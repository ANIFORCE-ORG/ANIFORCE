# ANIFORCE Agent 工业化开发手册

> 版本：v2.1.0  
> 更新日期：2026-06-12  
> 核心原则：**所有 Agent 交互都是 Task，对话只是 Task 的一种表现形式。**

---

## 1. 核心设计决策：Task 是唯一模型

### 1.1 为什么不搞 Chat 和 Task 两套架构

**错误思路：**

```text
Chat 系统管对话
Task 系统管业务任务
两者并行开发
```

**正确思路（AiToEarn 范式）：**

```text
所有 Agent 交互都是 Task
普通对话 = task_type 为 conversation 的 Task
营销任务 = task_type 为 campaign_planning 的 Task
```

**为什么这样设计：**

- 工业化：统一的生命周期、错误处理、恢复机制、可观测性。
- 可扩展：新增任务类型不需要改架构。
- 可追溯：所有交互都有完整事件流和状态机。
- 易维护：不需要维护两套持久化、两套事件流、两套前端接口。

### 1.2 对话能力怎么提供

**不是靠 ChatSession 实体，而是靠：**

```python
AgentTask {
  task_id: str
  task_type: "conversation"     # 标记为对话任务
  status: running | completed | error | aborted
  session_id: str               # OpenAI SDK Session（模型上下文）
  events: List[AgentTaskEvent]  # 事件流
  title: str
  user_id: str
  result: Optional[dict]        # 对话类任务可为空
  created_at: datetime
  updated_at: datetime
}
```

**前端仍然看到的是对话界面：**

- 用户发消息 → 创建/继续 Task → Agent 回复 → 事件流推送 → 前端渲染成聊天气泡。
- 刷新页面 → 查询 Task events → 恢复消息列表。
- 续聊 → 复用 `session_id`，OpenAI SDK 自动管理上下文。

### 1.3 与当前前端的兼容策略

**当前前端 API：**

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
  - stream chat → 运行该 Task，返回事件流
  - get session → 查询 Task + events
```

**最终目标：**

```text
前端逐步迁移到统一的 Task API：
  POST   /agent/tasks
  GET    /agent/tasks
  GET    /agent/tasks/{id}
  GET    /agent/tasks/{id}/events     # SSE 流式订阅
  POST   /agent/tasks/{id}/cancel
  POST   /agent/tasks/{id}/resume
```

---

## 2. 从 AiToEarn 学到的架构设计

### 2.1 Task 是一等公民

AiToEarn 的 `ContentGenerationTask`：

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
  createdAt: datetime
  updatedAt: datetime
}
```

**核心能力：**

- 持久化任务实体，不是一次性请求。
- 明确状态机。
- 可恢复、可取消、可分享。
- 事件驱动，不是消息列表。

### 2.2 分服务但逻辑独立

AiToEarn 后端是 Nx monorepo：

```text
apps/
  aitoearn-ai      # AI / Agent / MCP / Skill
  aitoearn-server  # 主业务 API
libs/
  common           # 异常、响应、日志
  nest-mcp         # MCP 协议
  aitoearn-queue   # 队列
  mongodb          # 数据访问
```

ANIFORCE 当前是 FastAPI 单服务，但应按"逻辑独立、物理可拆"设计：

```text
backend/app/
  agent_platform/      # Agent 平台基建（未来可拆服务）
    __init__.py
    errors.py
    models.py          # AgentTask / AgentTaskEvent
    events.py
    runtime.py
    adapters/
      openai_adapter.py
    repositories/
      base.py
      memory.py
      postgres.py
    mcp/
      registry.py
    queue/
      base.py
    skills/
      registry.py
    sessions/
      manager.py
  
  agents/              # Agent 编排层
    marketing_agent.py
    prompts/
    skills/
      campaign-planning/SKILL.md
  
  services/            # Service 层
    agent_task_service.py
  
  api/                 # API 层
    v1/
      agent/
        routes.py
        schemas.py
```

**关键边界：**

- `agent_platform/` 不依赖 `agents/` 和 `services/`。
- `agents/` 可以依赖 `agent_platform/`。
- `api/` 只依赖 `services/`，不直接调 `agent_platform/`。

### 2.3 MCP 是能力协议，不只是 Tool

AiToEarn 的 MCP 基建：

- 装饰器声明 Tool / Resource / Prompt。
- Registry 自动发现能力。
- Executor 按请求上下文执行。
- SSE / HTTP 两种传输。

ANIFORCE 的映射：

```text
业务 Service → 能力 Adapter → SDK Tool / MCP Tool 双出口
```

不要把业务能力直接写死在 OpenAI Agents SDK 的函数里。

### 2.4 Skill 是领域操作手册

AiToEarn 把复杂能力写成 Skill：

```markdown
# SKILL.md
---
name: campaign-planning
description: "生成广告投放计划"
---

## 目标
根据项目、预算、目标市场生成完整投放计划。

## 输入
- project_id
- budget
- target_regions

## 输出
- platforms
- budget_allocation
- creative_requirements

## 工作流
1. 调用 get_project_info
2. 分析目标市场
3. 选择投放平台
4. 分配预算
5. 生成结构化结果
```

Skill 不是代码，是给 Agent 看的操作手册。

---

## 3. 分层架构与职责边界

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

---

## 4. AgentTask 核心模型

### 4.1 Task 状态机

```python
class AgentTaskStatus(Enum):
    PENDING = "pending"           # 已创建，等待执行
    RUNNING = "running"           # 执行中
    COMPLETED = "completed"       # 成功完成
    ERROR = "error"               # 失败
    ABORTED = "aborted"           # 用户取消
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

### 4.2 Task 实体

```python
class AgentTask:
    task_id: str
    user_id: str
    task_type: str               # conversation / campaign_planning / asset_review
    status: AgentTaskStatus
    session_id: Optional[str]    # OpenAI SDK Session ID
    title: str
    input: Optional[dict]        # 任务输入
    result: Optional[dict]       # 结构化结果
    error: Optional[dict]        # 错误详情
    rating: Optional[int]
    rating_comment: Optional[str]
    public_share_token: Optional[str]
    created_at: datetime
    updated_at: datetime
```

### 4.3 Task Event

```python
class AgentTaskEvent:
    event_id: str
    task_id: str
    event_type: str              # started / message_delta / tool_call / completed / error
    payload: dict
    sequence: int                # 事件序号
    created_at: datetime
```

**核心事件类型：**

```text
runtime.started          任务开始
message.started          消息开始
message.updated          消息增量（delta）
message.completed        消息完成
tool_call.started        工具调用开始
tool_call.completed      工具调用完成
runtime.completed        任务完成
runtime.error            运行时错误
runtime.aborted          用户取消
```

---

## 5. OpenAI Agents SDK 核心能力

### 5.1 Session（模型上下文）

```python
from agents import SQLiteSession

# OpenAI SDK Session 管理对话历史
session = SQLiteSession(session_id, db_path="chat.db")
```

**SDK Session 的作用：**

- 自动管理多轮上下文。
- 传递历史消息给模型。
- 不是产品的 Task/Chat 实体。

**我们的 AgentTask.session_id：**

- 指向 SDK Session ID。
- 一个 Task 可以复用已有 session_id（续聊）。
- 也可以创建新 session_id（新对话）。

### 5.2 流式执行

```python
from agents import Agent, Runner

result = Runner.run_streamed(agent, input, session=session)

async for event in result.stream_events():
    if event.type == "raw_response_event":
        # ResponseTextDeltaEvent
        delta = event.data.delta
```

### 5.3 事件类型

```python
StreamEvent = (
    RawResponsesStreamEvent |      # LLM 原始事件
    RunItemStreamEvent |           # 工具调用、输出
    AgentUpdatedStreamEvent        # Agent 切换
)
```

---

## 6. 命名规范

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

---

## 7. 抽象与扩展性设计

### 7.1 接口优先

```python
# ❌ 直接依赖实现
task = PostgreSQLTaskRepository().get(task_id)

# ✅ 先定义接口
class AgentTaskRepository(ABC):
    @abstractmethod
    async def create(self, task: AgentTask) -> AgentTask: ...
    
    @abstractmethod
    async def get_by_id(self, task_id: str) -> Optional[AgentTask]: ...

# 再提供实现
class PostgreSQLAgentTaskRepository(AgentTaskRepository):
    ...
```

### 7.2 SDK 适配层

```python
# ❌ 业务代码直接调 SDK
from agents import Agent, Runner
result = Runner.run_streamed(agent, input)

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

---

## 8. 事件驱动架构

### 8.1 为什么用事件

```python
# ❌ 只记录消息
messages = [
    {"role": "user", "content": "帮我分析项目"},
    {"role": "assistant", "content": "好的，分析中..."}
]

# ✅ 记录事件
events = [
    {"type": "runtime.started", "timestamp": ...},
    {"type": "message.started", "role": "assistant"},
    {"type": "tool_call.started", "tool": "get_project_info", "args": {...}},
    {"type": "tool_call.completed", "result": {...}},
    {"type": "message.updated", "delta": "根据项目数据..."},
    {"type": "message.completed", "content": "..."},
    {"type": "runtime.completed", "result": {...}}
]
```

**优势：**

- 可恢复：刷新页面后重建 UI。
- 可追溯：每一步都有时间戳和序号。
- 可扩展：新增事件类型不影响旧逻辑。
- 可调试：完整记录 Agent 执行过程。

---

## 9. 错误体系

### 9.1 错误分类

```python
class AgentErrorCode(Enum):
    # Task 错误
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_STATUS_INVALID = "TASK_STATUS_INVALID"
    
    # Runtime 错误
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_ABORTED = "AGENT_ABORTED"
    
    # 上游错误
    UPSTREAM_NETWORK_ERROR = "UPSTREAM_NETWORK_ERROR"
    UPSTREAM_RATE_LIMIT = "UPSTREAM_RATE_LIMIT"
    
    # 业务错误
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    INSUFFICIENT_BUDGET = "INSUFFICIENT_BUDGET"
```

### 9.2 错误类

```python
class AppError(Exception):
    def __init__(
        self,
        code: AgentErrorCode,
        message: str,
        data: Optional[dict] = None
    ):
        self.code = code
        self.message = message
        self.data = data
```

---

## 10. 开发路线图

### Phase 1：Task 核心基建（Block 1-4）

- [ ] Block 1：Task 生命周期 + 事件模型
- [ ] Block 2：统一异常体系
- [ ] Block 3：Agent Runtime 骨架
- [ ] Block 4：Session 恢复机制

### Phase 2：能力协议层（Block 5-6）

- [ ] Block 5：Skill 系统
- [ ] Block 6：MCP 基础层

### Phase 3：异步与观测（Block 7-8）

- [ ] Block 7：异步队列抽象
- [ ] Block 8：可观测性

### Phase 4：业务能力（Block 9-10）

- [ ] Block 9：首个业务能力（项目查询）
- [ ] Block 10：营销 Agent 编排

---

## 11. 验收标准

每个 Block 完成后，必须能回答：

- 这个模块的边界是什么？
- 它依赖哪些模块？
- 它为哪些模块提供能力？
- 它的接口是否稳定？
- 它是否可测试？
- 它是否可替换实现？

---

## 12. 关键原则总结

1. **Task 是唯一模型**：对话是 Task，营销任务也是 Task。
2. **事件驱动**：记录事件流，不只是消息列表。
3. **状态机清晰**：每个状态转换都有明确语义。
4. **接口优先**：先定义抽象，再提供实现。
5. **SDK 隔离**：业务层不直接依赖 OpenAI SDK。
6. **逻辑独立**：agent_platform/ 可以独立拆服务。
7. **工业化优先**：可恢复、可取消、可追溯、可观测。

---

> 下一步：开始 Block 1 - Task 生命周期基建。

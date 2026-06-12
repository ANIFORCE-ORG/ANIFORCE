# Block 0 补充：基于真实 SDK 和前端的设计决策

> 更新：2026-06-12  
> 基于：OpenAI Agents Python SDK + 当前 ANIFORCE 前端实现

---

## 1. 当前实现：Session 模型（对话）

### 1.1 前端期望

```typescript
// 前端调用
AgentSession { id, title, created_at, updated_at }
createAgentSession() → session
streamAgentMessage(sessionId, message) → SSE events
```

**SSE 事件：**
- `runtime.started`
- `message.started`
- `message.updated` (delta)
- `message.completed`
- `runtime.completed`

### 1.2 当前后端实现

```python
# backend/app/agents/runtime.py
session = SQLiteSession(session_id, db_path="...")
result = Runner.run_streamed(agent, message, session=session)

async for event in result.stream_events():
    if event.type == "raw_response_event":
        delta = event.data.delta
        yield sse("message.updated", {"delta": delta})
```

**特点：**
- SDK Session 自动管理对话历史。
- 前端刷新后从 DB 恢复消息。
- 没有 `status`、`cancel`、`resume`。

---

## 2. AiToEarn 的实现：Task 模型（任务）

```typescript
ContentGenerationTask {
  taskId: string
  status: running | completed | error | aborted
  sessionId?: string
  messages: Array<AgentMessage>
  result?: TaskResult  // 结构化输出
  publicShareToken?: string
}
```

**特点：**
- 有状态机。
- 可取消、可恢复、可分享。
- 适合长周期任务。

---

## 3. ANIFORCE 的决策：两者并存

### 3.1 当前阶段（MVP）：保持 Session

- 当前前端和后端已用 Session 模型。
- Block 1-8 **不需要** Task 模型。
- 快速问答用 Session 足够。

### 3.2 未来阶段：引入 Task

```python
# Session：快速对话
/agent/chat/sessions/{id}/stream

# Task：营销任务
/agent/tasks
/agent/tasks/{id}
/agent/tasks/{id}/events      # SSE
/agent/tasks/{id}/cancel
/agent/tasks/{id}/resume
```

**什么时候用 Task：**
- 广告投放计划生成。
- 素材审核任务。
- 需要结构化输出、可取消、可恢复。

**什么时候用 Session：**
- 快速问答。
- 探索性对话。

---

## 4. OpenAI Agents SDK 核心能力

### 4.1 Session

```python
from agents import SQLiteSession

session = SQLiteSession(session_id, db_path="chat.db")
# 自动管理对话历史
```

### 4.2 流式执行

```python
from agents import Agent, Runner

result = Runner.run_streamed(agent, input, session=session)
async for event in result.stream_events():
    if event.type == "raw_response_event":
        # ResponseTextDeltaEvent
        delta = event.data.delta
```

### 4.3 事件类型

```python
StreamEvent = (
    RawResponsesStreamEvent |      # LLM 原始事件
    RunItemStreamEvent |           # 工具调用、输出
    AgentUpdatedStreamEvent        # Agent 切换
)
```

---

## 5. Block 1-8 的实现范围

**不需要做：**
- ❌ Task 模型。
- ❌ 状态机。
- ❌ 取消/恢复 API。

**需要做：**
- ✅ 完善异常处理。
- ✅ MCP 工具注册。
- ✅ Skill 系统。
- ✅ 业务能力接入（项目查询等）。
- ✅ 可观测性（日志、tracing）。

---

## 6. Block 0 验收标准（修正）

- [x] 明确 Session vs Task 的区别。
- [x] 确认当前阶段用 Session 模型。
- [x] 确认 Block 1-8 不需要 Task 模型。
- [ ] 目录结构初始化（下一步）。
- [ ] 抽象接口定义（下一步）。

# ANIFORCE Agent 基建优先快速开始

> 不先写业务 Tool，先搭工业 Agent 地基。

---

## 1. 新路线一句话

```text
AgentTask 生命周期 → 统一异常 → Runtime → Session 恢复 → Skill → MCP → 队列 → 业务 Tool
```

为什么：成熟 Agent 系统不是一次 `/chat` 请求，而是一套可恢复、可观测、可取消、可扩展的任务系统。

---

## 2. AiToEarn 给我们的关键启发

| AiToEarn 设计 | ANIFORCE 对应做法 |
|---|---|
| `aitoearn-ai` 独立承载 Agent | 先在 FastAPI 中建 `agent_platform`，逻辑独立 |
| `ContentGenerationTask` 为核心 | 建 `AgentTask`，不要只做 ChatMessage |
| SSE 流式输出 + 消息落库 | 每个 Agent 事件都写入事件表/存储 |
| `sessionId` 支持 resume | task 绑定 SDK session，支持断点续聊 |
| `SkillInitService` 初始化 Skill | 建 `SkillRegistry`，启动校验 Skill |
| `nest-mcp` 注册/执行工具 | 建 MCP registry/adapter，能力协议化 |
| `QueueService` 统一队列 | 先做 `TaskQueue` 抽象，MVP 用进程内队列 |
| `AppException + ResponseCode` | 建 `AppError + ErrorCode + 全局异常处理` |

---

## 3. 第一阶段不要做什么

暂时不要先做：

- 项目查询 Tool。
- 广告投放 Tool。
- 多 Agent 分工。
- 复杂投放策略。

先做：

- 任务状态。
- 事件流。
- 错误规范。
- 取消和恢复。
- Skill/MCP/队列接口。

---

## 4. MVP 地基 Block

### Block 1：Agent Task 生命周期

目标：创建任务、查任务、查事件、SSE 订阅。

最小状态：

```text
pending
running
completed
error
aborted
requires_action
```

最小事件：

```text
started
message_delta
message_completed
tool_call_started
tool_call_completed
error
keepalive
completed
```

验收：刷新页面后能重新看到历史事件。

---

### Block 2：统一异常体系

目标：业务错误统一编码，Agent 错误能落到任务事件里。

最小错误分类：

```text
TASK_NOT_FOUND
TASK_STATUS_INVALID
AGENT_RUNTIME_ERROR
AGENT_TIMEOUT
AGENT_ABORTED
UPSTREAM_NETWORK_ERROR
UPSTREAM_RATE_LIMIT
```

验收：任务不存在、运行失败、取消任务都有统一响应。

---

### Block 3：Agent Runtime 骨架

目标：封装 OpenAI Agents SDK，提供统一运行接口。

Runtime 负责：

- 创建/运行 Agent。
- 把 SDK stream 转为内部事件。
- 写入 task event。
- 管理 running task。
- 支持取消。
- 记录 usage。

验收：能跑一个最小 Agent 任务，并通过 SSE 接收输出。

---

### Block 4：Session 与断点恢复

目标：任务可恢复，不怕页面刷新。

分两层：

- UI 恢复：从 task events 恢复展示。
- LLM 恢复：用 SDK session 或摘要上下文续聊。

验收：已有 task 可以继续发送下一轮消息。

---

## 5. 第二阶段基建 Block

### Block 5：Skill 系统

首批 Skill：

```text
campaign-planning
market-research
creative-brief
performance-analysis
```

验收：系统能扫描、校验、列出 Skill，Agent 能按目标选择 Skill。

---

### Block 6：MCP 基础层

目标：让业务能力未来能被外部 Agent 调用。

最小能力：

- list tools。
- call demo tool。
- 同一 capability 转为 OpenAI SDK Tool。

验收：demo tool 同时支持内部 Agent 和 MCP 调用。

---

### Block 7：异步队列抽象

目标：长任务不绑死 HTTP 请求。

MVP：

```text
TaskQueue interface
InProcessTaskQueue
job_id 幂等
attempts/backoff
```

验收：后台 job 可提交、重试、失败落事件。

---

## 6. 第一个业务闭环何时开始

等 Block 1-7 结束后，再做业务 Tool：

```text
Project capability
→ SDK Tool adapter
→ MCP Tool adapter
→ Agent 调用
→ 事件落库
```

这样第一条业务能力一接入，就天然具备：任务化、SSE、恢复、异常、MCP、日志。

---

## 7. 详细文档

- 完整手册：`docs/development/AGENT_DEVELOPMENT_HANDBOOK.md`
- TODO 追踪：`docs/development/AGENT_TODO.md`

# ANIFORCE Agent 开发进度追踪

> 最后更新：2026-06-12  
> 核心路线：**Task 统一模型，基建优先，业务能力后置。**

---

## 总体进度

```text
Block 0 架构学习与规范    ██████████ 100%
Block 1 Task 生命周期      ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%
Block 2 异常体系          ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%
Block 3 Runtime 骨架       ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%
Block 4 Session 管理       ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%
Block 5 Skill 系统         ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%
Block 6 MCP 基础层         ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%
Block 7 队列抽象           ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%
Block 8 可观测性           ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%
Block 9 首个业务能力       ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%
Block 10 营销 Agent 编排   ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%
```

---

## 已完成

### Block 0：架构学习与代码规范

- [x] 阅读 AiToEarn 架构文档和源码。
- [x] 分析当前 ANIFORCE 前端 API 契约。
- [x] 调研 OpenAI Agents Python SDK 真实能力。
- [x] 确认核心设计决策：**Task 是唯一模型，对话是 Task 的一种表现形式**。
- [x] 编写 `AGENT_DEVELOPMENT_HANDBOOK.md`。
- [x] 编写 `BLOCK_0_CODE_DESIGN_STANDARDS.md`。
- [x] 明确目录结构、分层架构、命名规范。

**关键结论：**

- AiToEarn 所有 Agent 交互都是 `ContentGenerationTask`，没有单独的 Chat 系统。
- ANIFORCE 采用同样范式：所有交互都是 `AgentTask`，普通对话是 `task_type=conversation`。
- 当前前端 `/agent/chat/sessions` API 保留作为兼容层，内部实现改为 Task。
- OpenAI SDK 的 `Session` 只管理模型上下文，不是产品核心实体。

---

## 当前待办

### Block 1：Agent Task 生命周期基建

**优先级**：P0  
**状态**：未开始  
**目标**：建立 Task 核心模型、事件模型、Repository、API。

**任务清单：**

- [ ] 初始化 `backend/app/agent_platform/` 目录结构
- [ ] 定义 `AgentTaskStatus` 枚举
- [ ] 定义 `AgentTask` Pydantic 模型
- [ ] 定义 `AgentTaskEvent` Pydantic 模型
- [ ] 定义核心事件类型常量
- [ ] 实现 `AgentTaskRepository` 抽象接口
- [ ] 实现 `MemoryAgentTaskRepository`（内存实现）
- [ ] 实现 `AgentTaskService`
- [ ] 实现 Task API routes：
  - [ ] `POST /agent/tasks` - 创建任务
  - [ ] `GET /agent/tasks` - 查询任务列表
  - [ ] `GET /agent/tasks/{id}` - 查询任务详情
  - [ ] `GET /agent/tasks/{id}/events` - 查询任务事件（支持 SSE）
  - [ ] `POST /agent/tasks/{id}/cancel` - 取消任务
- [ ] 兼容当前前端 API：
  - [ ] `POST /agent/chat/sessions` 内部创建 Task
  - [ ] `GET /agent/chat/sessions/{id}` 内部查询 Task + events
  - [ ] `POST /agent/chat/sessions/{id}/stream` 内部运行 Task
- [ ] 编写基础测试或验证脚本

**验收标准：**

- [ ] 创建 Task 后返回 `task_id`
- [ ] Task 状态可从 `pending` 转换到 `running/completed/error/aborted`
- [ ] 事件可以追加并按序查询
- [ ] 支持 `after_sequence` 查询增量事件
- [ ] SSE 可以持续推送事件和 keepalive
- [ ] 页面刷新后可通过事件恢复 UI
- [ ] 当前前端不需要修改代码即可工作

**教学重点：**

- 为什么工业 Agent 要以 Task 为中心？
- 为什么事件流比消息列表更适合恢复？
- SSE 是传输层，不是存储层。

---

### Block 2：统一异常与响应体系

**优先级**：P0  
**状态**：未开始  
**依赖**：可与 Block 1 并行设计，落地时联动。

**任务清单：**

- [ ] 创建 `backend/app/agent_platform/errors.py`
- [ ] 定义 `ErrorCategory` 枚举
- [ ] 定义 `AgentErrorCode` 枚举
- [ ] 实现 `AppError` 异常类
- [ ] 实现 `get_error_payload` 辅助函数
- [ ] 实现 FastAPI 全局异常 handler
- [ ] 定义错误事件结构：`{"type": "runtime.error", "payload": {...}}`
- [ ] 实现错误到 Task status 的映射逻辑
- [ ] 区分业务错误、协议错误、上游错误、运行时错误
- [ ] 编写错误处理测试

**验收标准：**

- [ ] Task 不存在返回 `TASK_NOT_FOUND`
- [ ] Task 状态非法返回 `TASK_STATUS_INVALID`
- [ ] Runtime 异常能写入 `runtime.error` 事件
- [ ] 用户响应不暴露内部堆栈
- [ ] 日志保留完整异常上下文
- [ ] 错误事件可被前端解析并友好展示

**教学重点：**

- AiToEarn 的 `ResponseCode + AppException` 思想
- 错误码为什么不能随手写字符串
- 用户友好错误和开发者错误上下文的分离

---

### Block 3：Agent Runtime 最小骨架

**优先级**：P0  
**状态**：未开始  
**依赖**：Block 1、Block 2

**任务清单：**

- [ ] 创建 `backend/app/agent_platform/runtime.py`
- [ ] 创建 `backend/app/agent_platform/adapters/openai_adapter.py`
- [ ] 实现 `SDKAdapter` 抽象接口
- [ ] 实现 `OpenAISDKAdapter`
- [ ] 实现 `AgentRuntime` 类：
  - [ ] `run_task(task: AgentTask) -> AsyncIterator[AgentTaskEvent]`
  - [ ] 封装 OpenAI SDK `Runner.run_streamed`
  - [ ] 将 SDK 事件转换为 `AgentTaskEvent`
- [ ] 实现事件转换逻辑：
  - [ ] `RawResponsesStreamEvent` → `message.updated`
  - [ ] `RunItemStreamEvent` → `tool_call.started/completed`
- [ ] 集成到 `AgentTaskService`
- [ ] 更新 `/agent/chat/sessions/{id}/stream` 使用 Runtime

**验收标准：**

- [ ] 可以启动一个 Task 并流式返回事件
- [ ] 事件格式统一为 `AgentTaskEvent`
- [ ] 业务代码不直接依赖 OpenAI SDK
- [ ] SDK 错误被捕获并转换为 `AppError`
- [ ] 当前前端 Chat 功能正常工作

**教学重点：**

- 为什么要封装 SDK，而不是直接调用？
- 适配器模式的价值。
- 事件转换的边界。

---

### Block 4：Session 管理

**优先级**：P1  
**状态**：未开始  
**依赖**：Block 3

**任务清单：**

- [ ] 创建 `backend/app/agent_platform/sessions/manager.py`
- [ ] 实现 `SessionManager` 类：
  - [ ] `create_session(session_id: str) -> SQLiteSession`
  - [ ] `get_session(session_id: str) -> SQLiteSession`
  - [ ] 管理 SDK Session 生命周期
- [ ] Task 创建时自动创建或复用 session_id
- [ ] 实现 session_id 与 task_id 的映射
- [ ] 支持续聊：新 Task 复用已有 session_id
- [ ] 实现 Session 清理逻辑（可选）

**验收标准：**

- [ ] 对话上下文可以跨多个 Task 保持
- [ ] 用户可以在同一 session 内续聊
- [ ] Session 数据持久化到本地 SQLite
- [ ] Session 不会泄漏或无限增长

**教学重点：**

- OpenAI SDK Session 和产品 Task 的关系
- 为什么需要单独管理 Session？

---

### Block 5：Skill 系统

**优先级**：P1  
**状态**：未开始  
**依赖**：Block 3

**任务清单：**

- [ ] 创建 `backend/app/agent_platform/skills/registry.py`
- [ ] 定义 Skill 文件规范（YAML frontmatter + Markdown）
- [ ] 实现 `SkillRegistry` 类：
  - [ ] `load_skills(skill_dir: Path)`
  - [ ] `get_skill(name: str) -> Skill`
  - [ ] `list_skills() -> List[Skill]`
- [ ] 在 Runtime 启动时加载 Skill
- [ ] 将 Skill 内容注入到 Agent instructions
- [ ] 创建第一个示例 Skill：`agents/skills/campaign-planning/SKILL.md`
- [ ] 编写 Skill 开发文档

**验收标准：**

- [ ] Skill 可以被自动发现和加载
- [ ] Agent 可以读取 Skill 内容
- [ ] Skill 可以引用其他 Skill
- [ ] Skill 可以动态更新，无需重启服务

**教学重点：**

- Skill 是给 Agent 看的操作手册
- Skill 和 Tool 的区别
- 如何设计可复用的 Skill

---

### Block 6：MCP 基础层

**优先级**：P2  
**状态**：未开始  
**依赖**：Block 3

**任务清单：**

- [ ] 创建 `backend/app/agent_platform/mcp/registry.py`
- [ ] 创建 `backend/app/agent_platform/mcp/schemas.py`
- [ ] 定义 MCP Tool schema
- [ ] 实现 `MCPRegistry` 类：
  - [ ] `register_tool(tool: MCPTool)`
  - [ ] `get_tool(name: str) -> MCPTool`
  - [ ] `list_tools() -> List[MCPTool]`
- [ ] 实现装饰器 `@mcp_tool`
- [ ] 将 MCP Tool 转换为 OpenAI SDK Tool
- [ ] 实现第一个 MCP Tool：`get_project_info`
- [ ] 编写 MCP 开发文档

**验收标准：**

- [ ] 可以通过装饰器声明 MCP Tool
- [ ] MCP Tool 可以被 Agent 调用
- [ ] MCP Tool 可以独立测试
- [ ] 未来可以暴露为 MCP 协议端点

**教学重点：**

- MCP 是能力协议，不只是 SDK Tool
- 为什么业务能力要先写成 Service，再暴露为 Tool？

---

### Block 7：异步队列抽象

**优先级**：P2  
**状态**：未开始  
**依赖**：Block 3

**任务清单：**

- [ ] 创建 `backend/app/agent_platform/queue/base.py`
- [ ] 定义 `TaskQueue` 抽象接口
- [ ] 实现 `InProcessQueue`（进程内队列，用于开发）
- [ ] 设计 Task 入队、出队、重试逻辑
- [ ] 实现 Task 超时检测
- [ ] 实现 Task 失败重试
- [ ] 集成到 `AgentTaskService`
- [ ] 编写队列使用文档

**验收标准：**

- [ ] Task 可以异步执行
- [ ] Task 超时后自动标记为 ERROR
- [ ] Task 失败后可以重试
- [ ] 可以替换为生产队列（Redis/RabbitMQ）

**教学重点：**

- 为什么长任务不能堵在 HTTP 请求里？
- 队列抽象的价值。

---

### Block 8：可观测性

**优先级**：P2  
**状态**：未开始  
**依赖**：Block 1-7

**任务清单：**

- [ ] 实现结构化日志
- [ ] 集成 OpenTelemetry（可选）
- [ ] 记录 Task 生命周期日志
- [ ] 记录 Runtime 执行日志
- [ ] 记录 Tool 调用日志
- [ ] 实现 Task 执行统计：
  - [ ] 平均执行时间
  - [ ] 成功率
  - [ ] 失败原因分布
- [ ] 实现健康检查端点
- [ ] 编写可观测性文档

**验收标准：**

- [ ] 每个 Task 执行都有完整日志
- [ ] 可以追踪 Task 执行路径
- [ ] 可以统计 Agent 性能指标
- [ ] 可以快速定位问题

**教学重点：**

- 工业 Agent 系统的可观测性要求
- 日志、指标、追踪的区别

---

## 未来待办

### Block 9：首个业务能力

**优先级**：P3  
**状态**：未计划  
**依赖**：Block 1-8

**目标**：接入第一个真实业务能力。

**候选能力：**

- 项目查询：`get_project_info(project_id)`
- 项目列表：`list_projects(user_id)`
- 平台查询：`get_platform_info(platform)`

---

### Block 10：营销 Agent 编排

**优先级**：P3  
**状态**：未计划  
**依赖**：Block 9

**目标**：实现第一个完整营销任务。

**候选任务：**

- 广告投放计划生成
- 项目市场分析
- 素材审核建议

---

## 关键里程碑

- [x] **Milestone 0**：架构学习与规范制定（完成）
- [ ] **Milestone 1**：Task 核心基建（Block 1-4）
- [ ] **Milestone 2**：能力协议层（Block 5-6）
- [ ] **Milestone 3**：异步与观测（Block 7-8）
- [ ] **Milestone 4**：业务能力接入（Block 9-10）

---

## 当前焦点

**下一步行动：开始 Block 1 - Task 生命周期基建**

具体步骤：

1. 初始化 `backend/app/agent_platform/` 目录
2. 定义 `AgentTask` / `AgentTaskEvent` / `AgentTaskStatus` 模型
3. 实现 `AgentTaskRepository` 接口和内存实现
4. 实现 Task CRUD API
5. 实现事件追加和查询 API
6. 实现 SSE 事件流
7. 兼容当前前端 Chat API
8. 手工验证或编写测试

---

## 风险与注意事项

- 不要急于接入业务能力，先把基建做扎实。
- 不要跳过测试，每个 Block 完成后必须验证。
- 不要偏离 Task 统一模型，对话也是 Task。
- 不要让业务代码直接依赖 OpenAI SDK。
- 不要硬编码配置，必须外部化。

---

> 最后更新：2026-06-12  
> 下一步：Block 1 - Task 生命周期基建

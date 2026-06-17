# ANIFORCE Agent 重构总结（2026-06-17）

## 核心决策

**彻底去 AG-UI/CopilotKit 化**，改用通用任务模型 + 业务事件系统。

---

## 完成内容

### 1. 新架构落地

**新入口**：
- `POST /api/agent/runs`（替代旧 `/copilotkit/agent/default/run`）
- 删除 `/copilotkit/info` 和整个 `/copilotkit` 路由

**新事件协议**（5个通用事件）：
```
TaskCreated          → 任务创建
TaskProgressUpdated  → 进度更新（初始化/工具调用/生成回复/完成）
TaskOutputDelta      → 流式文本增量（打字机效果，不落库）
TaskOutputProduced   → 结构化产物落库
TaskCompleted        → 任务完成汇总
```

**运行元数据**（每个事件都带）：
```json
{
  "runtime": {
    "model": "claude-sonnet-4-6",
    "sessionId": "...",
    "tools": ["Task", "AskUserQuestion", "Bash", ...],
    "skills": ["test-skill", "deep-research", ...]
  },
  "telemetry": {
    "inputTokens": 1234,
    "outputTokens": 567,
    "totalTokens": 1801,
    "charPerSecond": 14.2,
    "durationMs": 6204,
    "costUsd": 0.080232
  }
}
```

### 2. 通用数据模型

**新模型**：
- `TaskOutput`：通用任务产物（insight / recommendation / alert / report / text）
- `OutputType` / `OutputStatus`：类型和状态枚举
- `BusinessEvent`：业务事件模型

**新数据库表**：
```sql
task_outputs         -- 任务结构化产物
evidence_snapshots   -- 证据快照（预留）
```

**Repository**：
- `OutputRepository`：产物 CRUD
- 扩展 `database.py` 初始化逻辑

### 3. 核心适配器

**`BusinessEventAdapter`**（`app/services/business_event_adapter.py`）：
- SDK 消息流 → 业务事件流
- 自动注入 runtime / telemetry
- 同步写入 tasks / events / task_outputs 表
- 支持 SDK 原始事件透传（`include_raw_events=True`）

### 4. 文件清理

**删除**：
- `app/api/copilotkit.py`
- `app/services/copilotkit_adapter.py`

**更新**：
- `app/main.py`：移除 copilotkit_router，注册 runs_router
- `tests/e2e/block1_basic_connectivity.py`：改用新 `/tasks` 检查
- `tests/e2e/block2_claude_sdk.py`：改用 `/runs` 入口和新事件名
- `tests/e2e/DEV_MANUAL.md`：更新 Block 3 为通过状态

**新增**：
- `app/api/runs.py`
- `app/models/output.py`
- `app/models/business_event.py`
- `app/repositories/output_repo.py`
- `tests/e2e/block3_business_events.py`

### 5. E2E 验证

**Block 3 测试通过（15/15）**：
```
✅ 新入口请求成功
✅ 收到 TaskCreated
✅ 收到 TaskProgressUpdated
✅ 收到 TaskOutputDelta
✅ 收到 TaskOutputProduced
✅ 收到 TaskCompleted
✅ 文本增量非空
✅ 运行元数据包含 model
✅ 运行元数据包含 tools
✅ 运行元数据包含 skills
✅ telemetry 包含 duration
✅ telemetry 包含 cost
✅ tasks 表有记录
✅ events 表有记录
✅ task_outputs 表有 text 类型记录
```

---

## 前端需求满足情况

✅ **吐字速度**：telemetry.charPerSecond  
✅ **输入/输出统计**：telemetry.inputTokens / outputTokens / totalTokens  
✅ **模型选型**：runtime.model  
✅ **tool 工具调用**：TaskProgressUpdated.progress.tool / toolResult  
✅ **skill 使用说明**：runtime.skills（显示加载了哪些 skill）  

---

## 架构优势

### vs AG-UI/CopilotKit

**旧方案问题**：
- 聊天驱动抽象（TextMessage* / ActionExecution*），不贴合任务驱动场景
- 强行映射丢失业务语义（InsightGenerated 被抽象成 TextMessage）
- 可扩展性差（每个新任务要定义新事件类型）

**新方案优势**：
- 事件类型固定（5个），业务差异体现在 payload
- 通用数据模型（Task / Output / Evidence），DB schema 不随任务类型膨胀
- 业务语义清晰（Output.type=insight / recommendation / alert）
- 运行元数据统一注入（model / tools / skills / telemetry）

### 新任务接入成本

只需 3 步：
1. 加枚举值：`TaskType.NEW_TASK = "new_task"`
2. 写执行器：返回 `List[TaskOutput]`
3. 注册执行器：`TASK_EXECUTORS[TaskType.NEW_TASK] = executor`

不需要改：
- ❌ 数据库 schema
- ❌ SSE 事件类型
- ❌ 前端 UI 组件
- ❌ API 接口

---

## 后续工作

### Block 4-9（按新架构继续）

- Block 4：通用任务模型完整实现（已有基础，补充查询/验证 API）
- Block 5：第一个任务执行器（性能分析）
- Block 6：SDK 集成（Sandbox + Skill）
- Block 7：MCP 工具接 backend
- Block 8：多租户隔离（需重测，旧脚本还引用 /copilotkit）
- Block 9：对话历史 + resume

### 遗留清理

- `tests/e2e/block7_multi_tenant.py` 还残留旧 `/copilotkit` 调用
- `drafts/260617/260617_08_real_runs_e2e.py` 探针可删（已有正式 block3 脚本）

---

## 关键文件清单

### 新增/重写
```
app/api/runs.py
app/services/business_event_adapter.py
app/models/output.py
app/models/business_event.py
app/repositories/output_repo.py
tests/e2e/block3_business_events.py
```

### 删除
```
app/api/copilotkit.py
app/services/copilotkit_adapter.py
```

### 修改
```
app/main.py
app/config/database.py
app/models/__init__.py
tests/e2e/block1_basic_connectivity.py
tests/e2e/block2_claude_sdk.py
tests/e2e/DEV_MANUAL.md
```

---

**最后更新**：2026-06-17  
**测试环境**：aniforce-agent/.venv (Python 3.11 + Claude SDK 0.2.101)  
**验证方式**：真实 Claude API 调用 + 数据库落盘检查  

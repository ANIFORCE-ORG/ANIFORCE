# ANIFORCE Agent 开发手册 v2.0

**性质**：开发交付物 + E2E 验证一体。改一个 Block，测一个 Block。
**依据**：`AGENTS.md`（架构设计与 SDK 协议）
**原则**：真实生产场景，不造假数据；每个 Block = 一个交付物。

---

## 架构方向变更（2026-06-17）

**重要决策**：不强行拥抱 AG-UI/CopilotKit 协议，改用**通用任务模型 + 业务事件系统**。

### 变更理由

**AG-UI 的局限**：
- 聊天驱动的通用抽象（`TextMessage*` / `ActionExecution*`），不贴合广告投放的任务驱动场景
- 强行映射会丢失业务语义（`InsightGenerated` / `OptimizationRecommended` 等具体事件被抽象成通用的 `TextMessage`）
- 可扩展性差：每个新任务类型要定义新事件、新 DB 表、新 UI 组件

**新方案核心**：
1. **暴露 Claude SDK 原始事件**（透传，供调试）
2. **业务事件翻译器**（SDK 消息 → 业务领域事件，如 `InsightGenerated` / `TaskCompleted`）
3. **通用任务模型**（`Task` + `Output` + `Evidence`，DB schema 固定，任务类型可扩展）
4. **事件驱动状态同步**（前后端通过 DB + SSE 共享状态，不需要主动"同步"）

详见本手册「核心架构设计」章节。

---

## 总览

| Block | 交付物 | 状态 | 脚本 |
|-------|--------|------|------|
| 1 | 基础连通性 + JWT(sub) | ✅ 通过 | `block1_basic_connectivity.py` |
| 2 | Claude SDK 调通（最小闭环） | ✅ SDK 调通 | `block2_claude_sdk.py` |
| 3 | 业务事件系统基础 | ✅ 通过 | `block3_business_events.py` |
| 4 | 通用任务模型 + DB Schema | ✅ 通过 | `block4_task_model.py` |
| 5 | 第一个任务：性能分析 | 📋 TODO | - |
| 6 | SDK 集成（Sandbox + Skill） | ✅ 通过 | `block6_sandbox_skill.py` |
| 7 | MCP 工具接 backend | ✅ 通过 | `block7_mcp_backend.py` |
| 8 | 多租户隔离 | ✅ 通过 | `block8_multi_tenant.py` |
| 9 | 对话历史 + resume | ✅ 通过 | `block9_history_resume.py` |

**执行顺序**：1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9

**Block 3 已完成**（2026-06-17）：
- 新入口 `POST /api/agent/runs` 生效
- 业务事件流：TaskCreated / TaskProgressUpdated / TaskOutputDelta / TaskOutputProduced / TaskCompleted
- 运行元数据注入：runtime.model / runtime.tools / runtime.skills / telemetry（duration / cost / charPerSecond / tokens）
- 数据库落盘：tasks / events / task_outputs 表
- 旧 `/copilotkit` 路由和 AG-UI 适配器已删除

---

## 核心架构设计

### 架构全景图

```
┌─────────────────────────────────────┐
│           前端                      │
│  订阅两类事件：                     │
│  1. SDK 原始事件 (调试)             │
│  2. 业务事件 (UI 更新)              │
└──────────────┬──────────────────────┘
               │ SSE
┌──────────────┴──────────────────────┐
│          Backend                    │
│  ┌────────────────────────────┐    │
│  │ Claude SDK Event Stream    │    │
│  │ (StreamEvent / Message)    │    │
│  └──────────┬─────────────────┘    │
│             ↓                       │
│  ┌──────────────────────────────┐  │
│  │ Event Forwarder (可选)       │  │
│  │ 透传 SDK 原始事件            │  │
│  └──────────┬───────────────────┘  │
│             ↓                       │
│  ┌──────────────────────────────┐  │
│  │ Business Event Translator    │  │
│  │ SDK 事件 → 业务事件          │  │
│  └──────────┬───────────────────┘  │
│             ↓                       │
│  ┌──────────────────────────────┐  │
│  │ SSE Publisher                │  │
│  │ 推送给前端                   │  │
│  └──────────┬───────────────────┘  │
│             ↓                       │
│  ┌──────────────────────────────┐  │
│  │ DB Writer (Task/Output)      │  │
│  │ 写入通用表                   │  │
│  └──────────────────────────────┘  │
│             ↓                       │
│  ┌──────────────────────────────┐  │
│  │ Database (真相源)            │  │
│  │ agent_tasks / task_outputs   │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 通用任务模型

**核心实体**：

1. **Task（任务）**：Agent 执行的最小工作单元
2. **Output（产物）**：任务产生的结构化结果（Insight / Recommendation / Alert / Report）
3. **Evidence（证据）**：支撑 Output 的数据快照

### 数据库 Schema

#### 1. agent_tasks 表

```sql
CREATE TABLE agent_tasks (
  id UUID PRIMARY KEY,
  type VARCHAR(100) NOT NULL,  -- 任务类型枚举（可扩展）
  category VARCHAR(50) NOT NULL,  -- analysis / optimization / monitoring / automation
  
  -- 输入
  target_type VARCHAR(50),  -- campaign / ad_group / creative / account
  target_ids JSONB,  -- ["camp_a", "camp_b"]
  params JSONB,  -- 任务特定参数（JSON）
  
  -- 上下文
  user_id UUID NOT NULL,
  workspace_id UUID,
  triggered_by VARCHAR(50),  -- user / schedule / webhook
  parent_task_id UUID,  -- 如果是子任务
  
  -- 状态
  status VARCHAR(50) NOT NULL,  -- pending / running / paused / completed / failed / cancelled
  progress JSONB,  -- {phase, currentStep, totalSteps, percentage, message}
  
  -- 元信息
  metadata JSONB,  -- {estimatedDuration, priority, tags}
  
  -- 时间
  created_at TIMESTAMP NOT NULL,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (parent_task_id) REFERENCES agent_tasks(id)
);

CREATE INDEX idx_agent_tasks_user_type ON agent_tasks(user_id, type);
CREATE INDEX idx_agent_tasks_status ON agent_tasks(status);
CREATE INDEX idx_agent_tasks_target ON agent_tasks(target_type, (target_ids::text));
```

**任务类型枚举（可扩展）**：
```typescript
enum TaskType {
  // 分析类
  PERFORMANCE_ANALYSIS = "performance_analysis",
  AUDIENCE_ANALYSIS = "audience_analysis",
  CREATIVE_ANALYSIS = "creative_analysis",
  COMPETITOR_ANALYSIS = "competitor_analysis",
  AUDIENCE_OVERLAP_ANALYSIS = "audience_overlap_analysis",
  
  // 优化类
  BUDGET_OPTIMIZATION = "budget_optimization",
  BID_OPTIMIZATION = "bid_optimization",
  AUDIENCE_OPTIMIZATION = "audience_optimization",
  
  // 监控类
  ANOMALY_DETECTION = "anomaly_detection",
  PERFORMANCE_MONITORING = "performance_monitoring",
  
  // 自动化类
  AUTO_RULE_EXECUTION = "auto_rule_execution",
  BATCH_UPDATE = "batch_update"
}
```

#### 2. task_outputs 表

```sql
CREATE TABLE task_outputs (
  id UUID PRIMARY KEY,
  task_id UUID NOT NULL,
  
  type VARCHAR(50) NOT NULL,  -- insight / recommendation / alert / report / artifact
  category VARCHAR(100),  -- 业务分类（自定义，如 "overlap_percentage"）
  
  -- 内容（类型化 JSON，根据 type 有不同结构）
  content JSONB NOT NULL,
  
  -- 元数据
  confidence FLOAT,  -- 0.0-1.0
  importance VARCHAR(20),  -- low / medium / high
  actionable BOOLEAN,
  requires_review BOOLEAN,
  
  -- 状态
  status VARCHAR(50) DEFAULT 'pending_review',  -- pending_review / verified / outdated / conflicted
  verified_by UUID,
  verified_at TIMESTAMP,
  
  -- 版本控制
  supersedes UUID,  -- 替代了哪条旧 Output
  superseded_by UUID,
  
  created_at TIMESTAMP NOT NULL,
  
  FOREIGN KEY (task_id) REFERENCES agent_tasks(id),
  FOREIGN KEY (verified_by) REFERENCES users(id),
  FOREIGN KEY (supersedes) REFERENCES task_outputs(id),
  FOREIGN KEY (superseded_by) REFERENCES task_outputs(id)
);

CREATE INDEX idx_task_outputs_task ON task_outputs(task_id);
CREATE INDEX idx_task_outputs_type ON task_outputs(type);
CREATE INDEX idx_task_outputs_status ON task_outputs(status);
```

**Output 类型化内容示例**：

```typescript
// Insight（分析结论）
interface InsightContent {
  finding: string  // "camp_a 的点击率比 camp_b 高 30%"
  reasoning: string  // "基于过去 7 天数据分析..."
  evidence: Evidence[]
  relatedOutputs?: string[]  // 关联的其他 Output ID
}

// Recommendation（优化建议）
interface RecommendationContent {
  action: string  // "adjust_budget" / "change_audience"
  current: any  // 当前值
  recommended: any  // 建议值
  expectedImpact: {
    metric: string  // "CTR" / "CPA"
    change: string  // "+15%"
  }
  rationale: string
  evidence: Evidence[]
}

// Alert（异常告警）
interface AlertContent {
  severity: "info" | "warning" | "critical"
  message: string
  affectedTargets: string[]
  detectedAt: string
  suggestedActions?: string[]
}
```

#### 3. evidence_snapshots 表

```sql
CREATE TABLE evidence_snapshots (
  id UUID PRIMARY KEY,
  output_id UUID NOT NULL,
  
  type VARCHAR(50) NOT NULL,  -- metric / screenshot / api_response / document
  source VARCHAR(200) NOT NULL,  -- "meta_ads_api" / "hotjar"
  data JSONB,  -- 实际数据（如果是 API 响应）
  url TEXT,  -- 外部链接
  snapshot_url TEXT,  -- 归档 URL (S3/OSS)
  
  captured_at TIMESTAMP NOT NULL,
  
  FOREIGN KEY (output_id) REFERENCES task_outputs(id)
);
```

#### 4. output_relationships 表（可选）

```sql
CREATE TABLE output_relationships (
  id UUID PRIMARY KEY,
  source_output_id UUID NOT NULL,
  target_output_id UUID NOT NULL,
  relationship_type VARCHAR(50) NOT NULL,  -- supports / contradicts / depends_on
  
  created_at TIMESTAMP NOT NULL,
  
  FOREIGN KEY (source_output_id) REFERENCES task_outputs(id),
  FOREIGN KEY (target_output_id) REFERENCES task_outputs(id)
);
```

### 业务事件定义

**只需 5 个通用事件类型**（不管什么任务都一样）：

```typescript
// 1. 任务创建
type TaskCreated = {
  type: "TaskCreated"
  data: {
    taskId: string
    taskType: string
    goal: string
    targets: { type: string, ids: string[] }
  }
}

// 2. 进度更新
type TaskProgressUpdated = {
  type: "TaskProgressUpdated"
  data: {
    taskId: string
    progress: {
      phase: string  // "数据获取" / "分析中" / "生成建议"
      currentStep: number
      totalSteps: number
      percentage: number
      message?: string
    }
  }
}

// 3. 产物生成（核心）
type TaskOutputProduced = {
  type: "TaskOutputProduced"
  data: {
    taskId: string
    output: {
      id: string
      type: "insight" | "recommendation" | "alert" | "report"
      category: string
      content: any  // 类型化内容
      confidence: number
      requiresReview: boolean
    }
  }
}

// 4. 状态变更
type TaskStatusChanged = {
  type: "TaskStatusChanged"
  data: {
    taskId: string
    status: "pending" | "running" | "paused" | "completed" | "failed"
    reason?: string
  }
}

// 5. 任务完成
type TaskCompleted = {
  type: "TaskCompleted"
  data: {
    taskId: string
    summary: {
      outputsProduced: number
      duration: number
      cost: number
    }
  }
}
```

**扩展性验证**：
- 新增"受众重叠分析"任务 → 只需加 `TaskType.AUDIENCE_OVERLAP_ANALYSIS` 枚举值 + 实现执行器
- 事件类型不变（还是那 5 个）
- DB schema 不变（通用表）
- 前端 UI 组件不变（通用的任务卡片 + Output 卡片）

---

## 环境准备

### 启动 agent 服务

```bash
cd /workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE/aniforce-agent
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8020
```

### 环境变量（.env）

```bash
ANTHROPIC_API_KEY=sk-xxx
ANTHROPIC_AUTH_TOKEN=sk-xxx
ANTHROPIC_BASE_URL=https://copilot.huya.info/api/anthropic
CLAUDE_AGENT_MODEL=claude-sonnet-4-6
JWT_SECRET=xxx
BACKEND_URL=http://localhost:18003
TASK_DB_PATH=runtime/agent/tasks.db
SESSION_DB_PATH=runtime/agent/sessions.db
RUNTIME_DIR=runtime/sessions
SKILLS_SOURCE_DIR=app/skills
```

---

## Block 1: 基础连通性 + JWT(sub)

**交付物**：FastAPI 服务 + JWT 认证中间件
**状态**：✅ 通过（2026-06-17）

### 执行
```bash
.venv/bin/python tests/e2e/block1_basic_connectivity.py
```

### 验证点
- [x] `GET /health` 返回 200
- [x] `GET /api/agent/tasks` 未认证返回 401，认证后可访问
- [x] 无 Token 请求返回 401
- [x] 带 Token（`sub` 字段）可创建任务

---

## Block 2: Claude SDK 调通（最小闭环）

**交付物**：agent 服务能通过 Claude SDK 返回真实文本
**状态**：✅ SDK 调通（2026-06-17）

### 验证点
- [x] 最小 query 探针返回 3 条消息
- [x] HTTP 接口返回 200 + SSE 事件流
- [x] Session Store 落盘

### 已修复
`app/agent/runtime.py` `_build_options`：
1. `env` 只带 `ANTHROPIC_*`/`CLAUDE_*` 前缀
2. 新增 `CLAUDE_CONFIG_DIR` 隔离
3. 新增 `CLAUDE_AGENT_SDK_CLIENT_APP`

---

## Block 3: 事件系统基础（重构中）

**交付物**：SDK 原始事件透传 + 业务事件翻译器
**状态**：🔧 重构中（2026-06-17）

### 目标

1. **SDK 原始事件透传**（可选，供调试）
   - 直接序列化 SDK 消息（`StreamEvent` / `AssistantMessage` 等）
   - 推送 SSE 事件：`{type: "sdk_raw_event", data: {...}}`
   - 前端开发者工具可查看，生产环境可关闭

2. **业务事件翻译器**（核心）
   - 把 SDK 消息流翻译成 5 个通用业务事件
   - 同步写入 DB（`agent_tasks` / `task_outputs` / `evidence_snapshots`）
   - 推送 SSE 给前端

### 实现要点

**业务事件翻译器伪码**：
```python
async def translate_to_business_events(sdk_stream, task: Task):
    # 1. TaskCreated
    yield {"type": "TaskCreated", "data": serialize_task(task)}
    
    async for message in sdk_stream:
        # 2. 根据 SDK 消息更新进度
        if should_update_progress(message):
            yield {"type": "TaskProgressUpdated", "data": {...}}
        
        # 3. 产生 Output
        if is_output_ready(message):
            output = extract_output(message)
            await db.task_outputs.insert(output)
            yield {"type": "TaskOutputProduced", "data": output}
        
        # 4. 状态变更
        if task.status_changed:
            yield {"type": "TaskStatusChanged", "data": {...}}
    
    # 5. TaskCompleted
    yield {"type": "TaskCompleted", "data": {...}}
```

### 待开发内容

1. 实现 `raw_event_forwarder.py`（透传 SDK 事件）
2. 实现 `business_event_translator.py`（SDK → 业务事件）
3. 实现 DB Writer（事件 → 写 `agent_tasks` / `task_outputs` 表）
4. 前端消费示例（订阅 SSE，更新 UI）

### 验证点
- [ ] SDK 原始事件可透传（开发者工具可见）
- [ ] 业务事件正确翻译（5 个事件类型）
- [ ] DB 正确写入（`agent_tasks` / `task_outputs` 表有数据）
- [ ] 前端能消费业务事件（TaskCard / OutputCard 更新）

---

## Block 4: 通用任务模型 + DB Schema

**交付物**：数据库迁移脚本 + ORM 模型定义
**状态**：⏸️ 待开发

### 目标

1. 创建通用表（`agent_tasks` / `task_outputs` / `evidence_snapshots` / `output_relationships`）
2. 实现 ORM 模型（SQLAlchemy / Prisma）
3. 实现基础 CRUD API

### 验证点
- [ ] 数据库表创建成功
- [ ] 可以插入/查询 Task 和 Output
- [ ] 证据快照关联正确
- [ ] Output 版本控制（supersedes）生效

---

## Block 5: 第一个任务：性能分析

**交付物**：`performance_analysis` 任务执行器 + 端到端流程
**状态**：⏸️ 待开发

### 目标

1. 实现任务执行器：`tasks/performance_analysis.py`
2. 产生 2-3 种 Output 类型（Insight / Recommendation）
3. 前端通用组件渲染
4. 验证完整流程：创建任务 → Agent 执行 → 产生 Outputs → 前端展示

### 验证点
- [ ] 可以通过 API 创建性能分析任务
- [ ] Agent 调用 Meta Ads API 获取数据
- [ ] 生成至少 2 条 Insights
- [ ] 生成至少 1 条 Recommendation
- [ ] 前端 TaskCard 显示任务进度
- [ ] 前端 OutputCard 显示 Insights 和 Recommendations
- [ ] PM 可以验证/拒绝 Output

---

## Block 6: SDK 集成（Sandbox + Skill）

**交付物**：Sandbox 隔离 + Skill 动态注入
**状态**：⏸️ 待开发

### 验证点
- [ ] Session 目录自动创建在 `runtime/sessions/{uuid}/`
- [ ] Agent 在 cwd 内操作文件，不越界
- [ ] Skill 复制路径正确
- [ ] Agent 回复能体现 Skill 内容

---

## Block 7: MCP 工具接 backend

**交付物**：Agent 通过 MCP 调 backend API，JWT 透传
**状态**：⏸️ 待开发

### 验证点
- [ ] Agent 调用 list_projects / create_project 等后端工具
- [ ] 后端日志显示 JWT 中的 user_id 正确
- [ ] 工具调用产生 `TaskProgressUpdated` 业务事件，payload.tool/toolResult 可用于前端工具面板
- [ ] Agent 基于工具结果生成回复

---

## Block 8: 多租户隔离

**交付物**：不同用户的数据/Session/对话完全隔离
**状态**：⏸️ 待重测

### 验证点
- [ ] User B 无法访问 User A 的任务（API 403/404）
- [ ] 数据库查询都带 user_id 过滤
- [ ] Session 目录按 session_id 隔离

---

## Block 9: 对话历史 + resume

**交付物**：SDK session 为主，backend 存业务元数据
**状态**：⏸️ 待开发

### 验证点
- [ ] `sessions.db` 按 session_id 存对话条目
- [ ] 同 session_id 多轮 query 上下文保持
- [ ] client 实例销毁后重建可 resume
- [ ] backend agent_task 表有完整业务索引

---

## 新任务如何接入？

### 场景：新增"受众重叠分析"任务

**Step 1：加枚举值**
```python
# app/agent/task_types.py
class TaskType(str, Enum):
    # ... 已有的
    AUDIENCE_OVERLAP_ANALYSIS = "audience_overlap_analysis"
```

**Step 2：实现执行器**
```python
# tasks/audience_overlap_analysis.py
async def execute_audience_overlap_analysis(task: Task) -> List[TaskOutput]:
    campaign_ids = task.inputs["params"]["campaign_ids"]
    
    # 1. 获取数据
    audiences = await fetch_audience_data(campaign_ids)
    
    # 2. 分析
    overlap_result = calculate_overlap(audiences)
    
    # 3. 生成 Outputs
    outputs = [
        TaskOutput(
            type=OutputType.INSIGHT,
            category="overlap_percentage",
            content={
                "finding": f"重叠率为 {overlap_result.percentage}%",
                "reasoning": "基于平台受众数据计算...",
                "evidence": [...]
            }
        )
    ]
    
    return outputs
```

**Step 3：注册执行器**
```python
# app/agent/task_registry.py
TASK_EXECUTORS = {
    TaskType.AUDIENCE_OVERLAP_ANALYSIS: execute_audience_overlap_analysis,
    # ... 其他任务
}
```

**完成！**
- ✅ DB schema 不变（用通用表）
- ✅ 事件类型不变（还是那 5 个）
- ✅ 前端 UI 组件不变（通用卡片）

---

## 维护规则

- 改一个 Block 代码 → 立刻跑对应 Block 测试 → 更新本手册状态
- 新增交付物 → 在总览表加行
- 状态变更：⏸️待开发 / 🔧开发中 / ⚠️部分 / ✅通过 / ❌失败
- 详细架构依据查 `AGENTS.md`，本手册只记 Block 级执行

---

**最后更新**：2026-06-17
**版本**：v2.0（架构重构：通用任务模型 + 业务事件系统）

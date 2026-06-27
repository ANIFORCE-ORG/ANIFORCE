# ANIFORCE Agent 编排完整设计

## 🎯 目标

基于对工业级产品（Cursor、Windsurf、Claude Code、Devin、Manus、AiToEarn）及 OpenAI Agents SDK 的深入分析，为 ANIFORCE 设计一个高效、可扩展的 Agent 编排体系。

**核心原则**：
- 单智能体架构（暂不引入 Sub-Agents）
- Plan-ReAct 混合模式
- Sandbox + Skills 领域知识封装
- 极简输出，工具调用克制
- 完全基于 MCP Tools 操作数据

---

## 📋 完整环节拆解

### 1. System Prompt（核心指令）

**职责**：定义 Agent 身份、能力、工作流程、约束

**关键要素**：
- 工作模式（Planning/Execution/Verification）
- 工具调用原则（克制、批量、并行）
- 输出风格（极简、直接）
- 任务分类策略（简单/复杂/长程）
- Skills 使用规则

**示例结构**：
```python
SYSTEM_PROMPT = """
你是 ANIFORCE 助手，使用 Plan-ReAct 混合模式。

## 工作流程
1. Analyze: 理解需求，判断任务类型
2. Plan: 复杂任务制定计划
3. Execute: 
   - 简单查询：直接回答
   - 确定步骤：批量执行工具
   - 探索步骤：ReAct 循环（观察-推理-行动）
4. Verify: 验证完成

## 工具调用原则
- 简单查询不用工具
- 独立工具批量并行调用
- 回答简洁（2-3 句话）

## Skills 使用规则
可用 Skills：
{skills_index}

使用方式：
1. 根据任务需求判断是否需要 Skill
2. 调用 load_skill 工具加载对应 Skill
3. 读取 Skill 的 SKILL.md 获取完整工作流
4. 严格按照 Skill 定义的步骤执行

## 可用工具
{mcp_tools_list}
"""
```

---

### 2. Skills 体系（领域知识库）

**职责**：封装可复用的领域工作流

#### 2.1 什么是 Skills？

Skills 是 **Sandbox Agent 的能力**，用于封装领域专业知识和工作流程。每个 Skill 包含：
- `SKILL.md`：工作流定义、步骤、约束
- 可选的脚本、参考资料、模板

#### 2.2 Skills 目录结构

```
backend/runtime/skills/                    # 宿主机 Skills 目录
├── project-management/
│   └── SKILL.md
├── campaign-optimization/
│   └── SKILL.md
├── data-reporting/
│   ├── SKILL.md
│   ├── scripts/
│   │   └── generate_report.py
│   └── templates/
│       └── report_template.md
└── batch-operations/
    └── SKILL.md
```

#### 2.3 SKILL.md 格式

```markdown
---
name: project-management
description: 项目管理：创建、查询、更新、删除、预算分析
---

# 项目管理 Skill

## 目标
帮助用户管理广告投放项目的全生命周期

## 输入
- 用户自然语言需求
- 项目 ID（可选，用于更新/查询）

## 输出
- 结构化项目信息
- 操作确认消息
- 预算分析报告（如需要）

## 工作流

### 1. 创建项目
1. 提取项目信息：名称、预算、描述、游戏类型
2. 调用 MCP Tool: `create_project`
3. 确认创建成功，返回项目 ID

### 2. 查询项目
1. 调用 MCP Tool: `list_projects` 或 `get_project_detail`
2. 格式化展示项目信息
3. 如用户需要分析，生成预算使用报告

### 3. 更新项目
1. 获取当前项目状态：`get_project_detail`
2. 确认要修改的字段
3. 调用 MCP Tool: `update_project`
4. 确认更新成功

## 硬约束
- 预算必须 > 0
- 项目名称不能为空
- 删除操作需要二次确认
```

#### 2.4 Skills 集成方式

```python
from pathlib import Path
from agents.sandbox import SandboxAgent, Manifest
from agents.sandbox.capabilities import Capabilities, Skills, LocalDirLazySkillSource
from agents.sandbox.entries import LocalDir

# Skills 在宿主机的位置
HOST_SKILLS_DIR = Path("backend/runtime/skills")

agent = SandboxAgent(
    name="ANIFORCE Assistant",
    instructions=SYSTEM_PROMPT,
    default_manifest=Manifest(
        entries={
            # 可以放项目文件、配置等
        }
    ),
    capabilities=Capabilities.default() + [
        Skills(
            lazy_from=LocalDirLazySkillSource(
                source=LocalDir(src=HOST_SKILLS_DIR)  # 宿主机路径
            )
        )
    ]
)
```

#### 2.5 Skills 工作流程

1. **发现**：SDK 扫描 `HOST_SKILLS_DIR`，生成 Skills 索引注入到 Agent instructions
2. **决策**：Agent 看到索引，根据任务决定使用某个 Skill
3. **加载**：Agent 调用 `load_skill("project-management")` 工具
4. **物化**：SDK 将该 Skill 复制到 Sandbox 的 `.agents/skills/project-management/` 目录
5. **执行**：Agent 在 Sandbox 中读取 `SKILL.md` 并按工作流执行

#### 2.6 推荐的 Skills

| Skill 名称 | 描述 | 何时使用 |
|-----------|------|---------|
| `project-management` | 项目 CRUD 和预算分析 | 涉及项目操作 |
| `campaign-optimization` | 广告计划创建和优化 | 涉及广告计划操作 |
| `data-reporting` | 数据分析和报告生成 | 用户需要数据分析 |
| `batch-operations` | 批量创建/更新 | 需要批量操作 |

---

### 3. MCP Tools（基础数据操作）

**职责**：与业务数据交互

**已实现**（10 个）：
- `list_projects` - 列出项目
- `create_project` - 创建项目
- `get_project_detail` - 查看项目详情
- `update_project` - 更新项目
- `delete_project` - 删除项目
- `list_campaigns` - 列出广告计划
- `create_campaign` - 创建广告计划
- `get_campaign_detail` - 查看广告计划详情
- `update_campaign` - 更新广告计划
- `delete_campaign` - 删除广告计划

**待扩展**：
- 素材管理：upload_material, list_materials, delete_material
- 数据分析：get_campaign_analytics, get_project_analytics
- 平台授权：list_platform_accounts, create_platform_auth

**集成方式**：
```python
from agents.mcp import MCPServerStreamableHttp

mcp_server = MCPServerStreamableHttp(
    name="aniforce",
    params={
        "url": "http://127.0.0.1:18003/api/v1/mcp",
        "headers": {"Authorization": f"Bearer {auth_token}"}
    }
)

agent = SandboxAgent(
    name="ANIFORCE Assistant",
    instructions=SYSTEM_PROMPT,
    mcp_servers=[mcp_server],
    capabilities=Capabilities.default() + [Skills(...)]
)
```

---

### 4. Runtime 执行引擎

**职责**：管理 Agent 生命周期、Session、事件流

**核心组件**：

#### 4.1 Task 管理
```python
class AgentTask:
    task_id: str          # 任务 ID
    user_id: str          # 用户 ID
    status: TaskStatus    # running/completed/error/aborted
    context: dict         # {"auth_token": "..."}
    session_id: str       # OpenAI SDK Session ID
    created_at: datetime
    updated_at: datetime
```

#### 4.2 Sandbox Session 管理

**重要**：ANIFORCE 使用 Sandbox Agent，需要 Sandbox 客户端

```python
from agents import Runner
from agents.run import RunConfig
from agents.sandbox import SandboxRunConfig
from agents.sandbox.sandboxes import UnixLocalSandboxClient

# SDK-owned lifecycle（推荐）
result = await Runner.run(
    agent,
    input=user_input,
    run_config=RunConfig(
        sandbox=SandboxRunConfig(
            client=UnixLocalSandboxClient()
        )
    )
)
```

#### 4.3 事件流管理
```python
async def run_task(task: AgentTask, user_input: str):
    # 1. 推送 runtime.started
    yield RuntimeStartedEvent(task_id, user_input)
    
    # 2. 执行 Sandbox Agent
    result = await Runner.run(
        agent,
        input=user_input,
        run_config=RunConfig(
            sandbox=SandboxRunConfig(client=UnixLocalSandboxClient())
        )
    )
    
    # 3. 流式推送事件
    async for event in result.stream_events():
        if event.type == "message.delta":
            yield MessageDeltaEvent(content=event.content)
        elif event.type == "tool_call.started":
            yield ToolCallStartedEvent(tool_name=event.tool_name)
        elif event.type == "tool_call.completed":
            yield ToolCallCompletedEvent(result=event.result)
    
    # 4. 推送 runtime.completed
    yield RuntimeCompletedEvent(final_output=result.final_output)
```

#### 4.4 MCP 连接管理
```python
async def _create_agent(task: AgentTask):
    """创建带 MCP 和 Skills 的 Sandbox Agent"""
    auth_token = task.context.get("auth_token")
    
    mcp_server = MCPServerStreamableHttp(
        name="aniforce",
        params={
            "url": "http://127.0.0.1:18003/api/v1/mcp",
            "headers": {"Authorization": f"Bearer {auth_token}"}
        }
    )
    
    return SandboxAgent(
        name="ANIFORCE Assistant",
        instructions=self._build_instructions(),
        mcp_servers=[mcp_server],
        capabilities=Capabilities.default() + [
            Skills(
                lazy_from=LocalDirLazySkillSource(
                    source=LocalDir(src=Path("backend/runtime/skills"))
                )
            )
        ]
    )
```

---

### 5. 前端集成（Chat UI）

**职责**：展示 Agent 工作过程

**关键功能**：

#### 5.1 流式输出
```typescript
async function* streamChat(sessionId: string, message: string) {
  const response = await fetch(
    `/api/v1/agent/chat/sessions/${sessionId}/stream`,
    {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ message })
    }
  )
  
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    
    const chunk = decoder.decode(value)
    for (const line of chunk.split('\n\n')) {
      if (line.startsWith('data: ')) {
        const event = JSON.parse(line.slice(6))
        yield event
      }
    }
  }
}
```

#### 5.2 消息展示
```typescript
interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  toolCalls?: ToolCall[]
  skillUsed?: string  // 使用的 Skill 名称
}

interface ToolCall {
  name: string
  status: 'started' | 'completed' | 'failed'
  result?: string
}
```

---

### 6. 工具调用策略

**职责**：优化效率

#### 6.1 批量并行调用
System Prompt 强调：
```
当有多个独立工具调用时，一次性并行调用，不要串行。
```

#### 6.2 克制调用
System Prompt 强调：
```
- 简单查询直接回答，不调用工具
- 能一次完成的不分多次
```

#### 6.3 Skills 优先
System Prompt 强调：
```
遇到复杂工作流：
1. 先判断是否有对应 Skill
2. 有 Skill：加载并按流程执行
3. 无 Skill：使用 ReAct 模式逐步探索
```

---

### 7. 错误处理与恢复

**职责**：处理异常

#### 7.1 Task 超时处理
```python
@scheduler.scheduled_job('interval', minutes=10)
async def recover_timeout_tasks():
    """兜底机制：将超时的 running 任务标记为 error"""
    timeout_ms = 30 * 60 * 1000  # 30 分钟
    tasks = await repo.list_timeout_tasks(timeout_ms)
    
    for task in tasks:
        await repo.update_status(task.id, TaskStatus.ERROR)
        await repo.append_message(task.id, {
            "type": "error",
            "message": "Task timeout after 30 minutes"
        })
```

#### 7.2 MCP 连接失败
```python
try:
    mcp_server = MCPServerStreamableHttp(...)
    async with mcp_server:
        # 执行任务
        ...
except MCPConnectionError as e:
    logger.error(f"MCP connection failed: {e}")
    # 降级：返回错误消息
    yield ErrorEvent("MCP 服务不可用，请稍后重试")
```

#### 7.3 用户中断
```python
# API: POST /api/v1/agent/chat/sessions/{session_id}/abort
async def abort_task(session_id: str):
    task_info = running_tasks.get(session_id)
    if task_info:
        task_info.abort_controller.abort()
        await repo.update_status(session_id, TaskStatus.ABORTED)
```

---

### 8. 监控与调试

**职责**：可观测性

#### 8.1 Tracing
```python
from agents import trace, gen_trace_id

trace_id = gen_trace_id()
with trace(workflow_name="ANIFORCE Task", trace_id=trace_id):
    result = await Runner.run(agent, input, run_config=...)

logger.info(f"Trace: https://platform.openai.com/traces/trace?trace_id={trace_id}")
```

#### 8.2 日志
```python
# 关键节点记录
logger.info(f"[RUNTIME] Task {task_id} started")
logger.debug(f"[SKILL] Loading skill: {skill_name}")
logger.debug(f"[MCP] Tool call: {tool_name}({args})")
logger.info(f"[RUNTIME] Task {task_id} completed in {duration}ms")
logger.error(f"[ERROR] Task {task_id} failed: {error}")
```

#### 8.3 Metrics
```python
# 记录到数据库
await ai_log_repo.create({
    "task_id": task_id,
    "user_id": user_id,
    "duration_ms": duration,
    "tool_calls_count": len(tool_calls),
    "skills_used": skills_used,
    "tokens_used": usage.total_tokens,
    "cost_usd": usage.total_cost
})
```

---

### 9. 部署与配置

**职责**：生产运行

#### 9.1 环境变量
```bash
# backend/.env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# MCP Server
MCP_SERVER_URL=http://127.0.0.1:18003/api/v1/mcp

# Skills
SKILLS_DIR=backend/runtime/skills

# Database
AGENT_DB_PATH=./runtime/agent/tasks.db

# Demo Mode
DEMO_MODE=false
```

#### 9.2 启动脚本
```bash
#!/bin/bash
# scripts/start-dev.sh

# Backend
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 18003 --reload &

# Frontend
cd frontend && npm run dev &

wait
```

---

## 🎯 实施计划

### Phase 1: Skills 基础设施（2 天）
- [ ] 创建 `backend/runtime/skills/` 目录
- [ ] 编写 4 个核心 Skills：
  - `project-management`
  - `campaign-optimization`
  - `data-reporting`
  - `batch-operations`
- [ ] 实现 Skills 加载机制
- [ ] 测试 Skills 索引生成

### Phase 2: Sandbox Agent 集成（2 天）
- [ ] 将 `Agent` 改为 `SandboxAgent`
- [ ] 集成 `Skills` capability
- [ ] 集成 `UnixLocalSandboxClient`
- [ ] 优化 System Prompt（添加 Skills 使用规则）
- [ ] 测试 Skill 加载和执行

### Phase 3: Runtime 优化（1-2 天）
- [ ] 调整 Runtime 支持 Sandbox
- [ ] 优化事件流管理
- [ ] 增强错误恢复机制

### Phase 4: MCP Tools 扩展（2-3 天）
- [ ] 素材管理工具（3 个）
- [ ] 数据分析工具（2 个）
- [ ] 平台授权工具（2 个）

### Phase 5: 前端优化（1-2 天）
- [ ] 优化流式输出展示
- [ ] 添加 Skill 使用提示
- [ ] 添加工具调用进度显示
- [ ] 完善错误提示

---

## 📝 关键代码位置

```
backend/
├── skills/                         # Skills 定义（新增）
│   ├── project-management/
│   │   └── SKILL.md
│   ├── campaign-optimization/
│   │   └── SKILL.md
│   └── data-reporting/
│       └── SKILL.md
│
├── app/agent_platform/
│   ├── runtime.py                  # Runtime 执行引擎
│   ├── adapters/
│   │   └── openai_adapter.py       # OpenAI SDK 适配器
│   ├── models.py                   # 数据模型
│   └── repositories/
│       └── sqlite.py               # SQLite 存储
│
├── app/api/v1/
│   ├── mcp.py                      # MCP 工具定义
│   └── agent/
│       └── routes.py               # Agent API 路由
│
└── app/services/
    └── agent_task_service.py       # Agent Task 服务层
```

---

## 🔑 核心设计决策

1. **单智能体 + Sandbox**：使用 `SandboxAgent`，不引入 Sub-Agents
2. **Skills 封装领域知识**：将复杂工作流封装为 Skills
3. **Plan-ReAct 混合**：简单任务直接执行，复杂任务优先使用 Skills
4. **MCP 为中心**：所有数据操作通过 MCP Tools
5. **极简输出**：2-3 句话，不解释不总结
6. **Lazy Loading**：Skills 按需加载，不预先物化
7. **事件驱动**：流式推送所有事件
8. **错误恢复**：超时兜底、连接降级、用户可中断


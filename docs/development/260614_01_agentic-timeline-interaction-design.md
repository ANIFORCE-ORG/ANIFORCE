# Agentic Timeline 交互设计与落地规范

日期：2026-06-14

## 1. 背景与问题

当前 ANIFORCE Home Agent 的交互仍然偏传统 SaaS：

- 工具调用状态显示在页面顶部或独立状态区，例如“Agent Run / 执行轨迹”。
- 用户真正关注的“Agent 正在做什么、查到了什么、结果是什么”没有出现在对话流中。
- 项目查询结果仍主要以 Markdown 文本返回，缺少业务卡片。
- 前端存在多套 Agent UI 路径：`AgentShell/ChatWindow` 与 `pages/Home.vue` 自有布局并存，导致改了一处但真实页面未生效。
- 后端 SDK 事件适配曾把真实工具调用映射成 `unknown {}`，导致前端无法识别业务工具。

本规范的目标是统一交互模型：**Agent 的动作、计划、工具结果、业务对象，都必须作为对话流中的结构化 Timeline Block 呈现。**

## 2. 核心原则

### 2.1 对话流是 Agent 行动审计流

Home Agent 的主展示区域不应只显示文本消息，而应显示混合时间线：

- 用户消息
- Agent 文本消息
- 工具调用卡片
- 工具结果卡片
- 执行计划卡片
- 项目列表卡片
- 项目详情卡片
- 投放计划草稿卡片
- 素材生成卡片
- 用户确认卡片
- 错误与重试卡片

### 2.2 工具状态必须内联展示

工具调用发生时，必须在对话流当前位置插入一个小组件，而不是在顶部状态栏或侧边栏单独显示。

错误示例：

```text
Agent Run
执行轨迹
check list_projects {"limit":20}
完成
```

正确示例：

```text
Agent：我来查询你当前账号下的项目。

[工具活动卡]
正在查询项目列表
从 ANIFORCE 项目库读取当前账号可访问项目
参数：全部状态 · 最多 20 个

[项目列表卡]
你的项目，共 11 个
- 项目 A ... [查看详情] [创建投放计划]
- 项目 B ... [查看详情] [创建投放计划]
```

### 2.3 工具名要翻译成业务语义

前端不能直接把 `list_projects` 当产品文案展示。

需要一层 Tool Presentation Registry：

```ts
list_projects => {
  runningTitle: '正在查询项目列表',
  completedTitle: '项目列表查询完成',
  description: '从 ANIFORCE 项目库读取当前账号可访问项目',
  resultBlock: 'project_list'
}
```

### 2.4 业务结果优先组件化

项目查询结果不应只靠 Markdown 文本表达。模型可以继续总结，但主要结果必须是业务组件。

项目查询的主结果应为 `ProjectListBlock`，包含：

- 项目名称
- 项目 ID
- 预算
- 已花费
- 状态
- 描述
- 操作按钮：查看详情、创建投放计划

### 2.5 侧边栏只能做概览，不能替代对话流

侧边栏或工作台可以保留，用于长期任务、当前业务对象、上下文摘要。

但实时工具状态与业务结果必须首先进入对话流。

## 3. 目标交互：查看项目列表

### 3.1 用户输入

```text
查看项目列表
```

### 3.2 期望时间线

#### Block 1：用户消息

```text
用户：查看项目列表
```

#### Block 2：Agent 简短说明

```text
Agent：我来查询你当前账号下的项目。
```

#### Block 3：工具活动卡，running

```text
┌──────────────────────────────┐
│ 正在查询项目列表              │
│ 从 ANIFORCE 项目库读取当前账号可访问项目 │
│ 全部状态 · 最多 20 个          │
└──────────────────────────────┘
```

#### Block 4：同一个工具活动卡更新为 completed

```text
┌──────────────────────────────┐
│ 项目列表查询完成              │
│ 找到 11 个项目                │
│ list_projects                 │
└──────────────────────────────┘
```

#### Block 5：项目列表业务卡

```text
┌──────────────────────────────┐
│ 你的项目                      │
│ 共 11 个项目                  │
│                              │
│ 260614                       │
│ ID: fb20...                  │
│ 预算 ¥50,000 · 状态 active    │
│ [查看详情] [创建投放计划]      │
│                              │
│ Candy Blast - 全球推广        │
│ ID: 296...                   │
│ 预算 ¥50,000 · 状态 active    │
│ [查看详情] [创建投放计划]      │
└──────────────────────────────┘
```

#### Block 6：Agent 总结与下一步建议

```text
Agent：找到 11 个项目。你可以继续查看某个项目详情，或为某个项目创建投放计划。
```

## 4. 前端架构设计

### 4.1 统一 Timeline Block 类型

建议在 `useHomeAgentSession` 中维护统一时间线：

```ts
type AgentTimelineBlock =
  | TextBlock
  | ToolActivityBlock
  | PlanBlock
  | ProjectListBlock
  | ProjectDetailBlock
  | CampaignDraftBlock
  | AssetGenerationBlock
  | ApprovalBlock
  | ErrorBlock
```

当前 MVP 至少实现：

```ts
type AgentTimelineBlock =
  | {
      type: 'tool_activity'
      id: string
      toolName: string
      status: 'running' | 'completed' | 'error'
      title: string
      description?: string
      summary?: string
      arguments?: Record<string, unknown>
      result?: unknown
    }
  | {
      type: 'project_list'
      id: string
      summary: string
      projects: Project[]
      sourceToolCallId?: string
    }
  | {
      type: 'plan'
      id: string
      todos: TodoItem[]
    }
```

### 4.2 Home 页面必须接入 Timeline

真实页面是 `frontend/packages/main-app/src/pages/Home.vue`，不能只改 `AgentShell/ChatWindow`。

Home 页面应按顺序渲染：

```text
历史消息
当前流式 assistant 消息
本轮 timeline blocks
加载中状态
输入框
```

旧的 `execution-trace` 区域必须删除或隐藏，不能继续展示 `Agent Run / 执行轨迹`。

### 4.3 Timeline Renderer

建议新增：

```text
frontend/packages/main-app/src/components/agent/timeline/TimelineBlockRenderer.vue
frontend/packages/main-app/src/components/agent/timeline/ToolActivityBlock.vue
frontend/packages/main-app/src/components/agent/timeline/ProjectListBlock.vue
frontend/packages/main-app/src/components/agent/timeline/PlanTimelineBlock.vue
```

渲染规则：

```vue
<TimelineBlockRenderer
  v-for="block in agent.timelineBlocks.value"
  :key="block.id"
  :block="block"
  @action="agent.handleTimelineAction"
/>
```

### 4.4 Tool Presentation Registry

需要把工具事件映射成产品文案。

第一批工具：

| tool_name | running 文案 | completed 文案 | 结果组件 |
|---|---|---|---|
| `list_projects` | 正在查询项目列表 | 项目列表查询完成 | `project_list` |
| `get_project_detail` | 正在读取项目详情 | 项目详情读取完成 | `project_detail` |
| `create_project` | 正在创建项目 | 项目创建完成 | `project_created` |
| `list_campaigns` | 正在查询投放计划 | 投放计划查询完成 | `campaign_list` |
| `create_campaign` | 正在创建投放计划 | 投放计划创建完成 | `campaign_created` |

### 4.5 项目列表解析规则

后端短期可能返回两类结果。

结构化结果：

```json
{
  "type": "project.list",
  "projects": []
}
```

MCP 文本结果：

```json
{
  "type": "text",
  "text": "找到 11 个项目:\n\n1. **260614**\n   - ID: ..."
}
```

前端必须兼容这两种形态。

长期目标是后端 MCP 直接返回结构化结果，文本只作为模型总结输入。

## 5. 后端事件要求

### 5.1 工具调用事件必须包含稳定 ID

`tool_call.started`：

```json
{
  "event_type": "tool_call.started",
  "payload": {
    "tool_call_id": "call_xxx",
    "tool_name": "list_projects",
    "arguments": { "limit": 20 }
  }
}
```

`tool_call.completed`：

```json
{
  "event_type": "tool_call.completed",
  "payload": {
    "tool_call_id": "call_xxx",
    "tool_name": "list_projects",
    "result": {
      "type": "text",
      "text": "找到 11 个项目..."
    }
  }
}
```

### 5.2 禁止把非工具事件映射成工具

以下 SDK item 不应生成工具卡：

- `message_output_item`
- `reasoning_item`
- `mcp_list_tools_item`
- 普通 `message_output_created`

只有 SDK `tool_call_item` 和 `tool_call_output_item` 才能映射成工具事件。

### 5.3 修复点

OpenAI Agents SDK 的 `run_item_stream_event.item` 是 wrapper：

- `ToolCallItem`：真实工具名在 `item.tool_name` 或 `item.raw_item.name`
- `ToolCallOutputItem`：结果在 `item.output`，工具名需要通过 `call_id` 关联前面的 call

不能直接读：

```py
item.name
item.arguments
item.content
```

## 6. 验收标准

### 6.1 查看项目列表

输入：

```text
查看项目列表
```

必须看到：

- 对话流中出现“正在查询项目列表”工具卡。
- 工具卡完成后显示“项目列表查询完成”。
- 对话流中出现“你的项目”项目列表卡。
- 项目卡中至少展示项目名称、ID、预算、状态。
- 项目卡中有“查看详情”“创建投放计划”按钮。
- 不再出现顶部或独立区域的 `Agent Run / 执行轨迹`。
- 不再出现 `unknown {}`。

### 6.2 SSE 验收

真实 SSE 必须包含：

```text
event: tool_call.started
"tool_name":"list_projects"
"tool_call_id":"call_..."
```

以及：

```text
event: tool_call.completed
"tool_name":"list_projects"
"tool_call_id":"call_..."
```

### 6.3 构建验收

必须通过：

```bash
cd frontend && npm_config_cache=./npm_cache npm run build
cd backend && UV_CACHE_DIR=./uv_cache uv run python -m py_compile app/agent_platform/adapters/openai_adapter.py
```

## 7. 当前待办

### P0：必须立即完成

- 删除或隐藏 `Home.vue` 中旧的 `execution-trace` 区域。
- 在 `Home.vue` 的消息流中接入 `agent.timelineBlocks.value`。
- 确保 `TimelineBlockRenderer` 在真实 Home 页面渲染，而不是只在 `AgentShell/ChatWindow` 渲染。
- 修复 `ProjectListBlock` 的样式和字段空值展示。

### P1：短期完善

- 后端 MCP `list_projects` 返回结构化 JSON，而不是只返回 Markdown 文本。
- `tool_call.completed` 的 result 统一为 `{ type, data, text }` 结构。
- 给 `ProjectListBlock` 增加分页或折叠，避免 11 个项目全部撑满屏幕。
- 点击“查看详情”时优先在 workspace 打开项目详情，而不是直接跳路由。

### P2：后续扩展

- `ProjectDetailBlock`
- `CampaignListBlock`
- `CampaignDraftBlock`
- `AssetGenerationBlock`
- `ApprovalBlock`
- `ErrorRetryBlock`

## 8. AG-UI 咬合设计

补充 CopilotKit AG-UI 设计约束后，ANIFORCE 不能只做“前端自己拼卡片”，而要把现有事件适配成一套可演进的 AG-UI-like 时间线模型。

### 8.1 AG-UI 核心事件关系

AG-UI 的关键实体关系是：

```text
RUN_STARTED / RUN_FINISHED
  └─ TEXT_MESSAGE_START / CONTENT / END
       └─ parentMessageId
            └─ TOOL_CALL_START / ARGS / END
                 └─ toolCallId
                      └─ TOOL_CALL_RESULT

ACTIVITY_SNAPSHOT / ACTIVITY_DELTA
  └─ messageId
       └─ content 可用 JSON Patch 增量更新
```

也就是说，UI 组件不是孤立插入的，它必须能回答：

- 属于哪一次 run？
- 属于哪一条 assistant message？
- 对应哪个 toolCallId？
- 是 snapshot 还是 delta 更新？
- 完成后是否产生 business result surface？

### 8.2 当前 ANIFORCE 事件到 AG-UI 的映射

当前后端已有事件：

| ANIFORCE SSE | AG-UI 语义 | UI 行为 |
|---|---|---|
| `runtime.started` | `RUN_STARTED` | 创建本轮 run 上下文 |
| `message.started` | `TEXT_MESSAGE_START` | 创建 assistant streaming message |
| `message.updated` | `TEXT_MESSAGE_CONTENT` | 增量写入文本 |
| `message.completed` | `TEXT_MESSAGE_END` | 固化 assistant message |
| `runtime.completed` | `RUN_FINISHED` | 结束本轮 run |
| `tool_call.started` | `TOOL_CALL_START` + args snapshot | 创建/更新工具 activity |
| `tool_call.completed` | `TOOL_CALL_RESULT` | 完成工具 activity，并派生业务 result block |
| `tool_call.error` | `RUN_ERROR` 或 tool error | 标记工具 activity 失败 |
| `CUSTOM plan.*` | `ACTIVITY_SNAPSHOT/DELTA` | 创建/更新 plan activity |

短期不强制后端改成标准 AG-UI event type，但前端状态层必须按 AG-UI 语义建模。

### 8.3 Timeline Block 必须带 AG-UI 关联字段

`AgentTimelineBlock` 不能只有展示字段，必须保留协议关联字段：

```ts
interface TimelineMeta {
  runId?: string
  parentMessageId?: string
  messageId: string
  toolCallId?: string
  activityType?: string
  createdAt: number
  updatedAt: number
}
```

工具活动块：

```ts
{
  type: 'tool_activity',
  messageId: `activity_tool_${toolCallId}`,
  activityType: 'TOOL_CALL',
  toolCallId,
  parentMessageId,
  status,
  content: {
    toolName,
    title,
    description,
    arguments,
    resultSummary
  }
}
```

项目结果块：

```ts
{
  type: 'project_list',
  messageId: `surface_project_list_${toolCallId}`,
  activityType: 'BUSINESS_RESULT',
  toolCallId,
  parentMessageId,
  content: {
    summary,
    projects
  }
}
```

### 8.4 Snapshot / Delta 更新规则

工具状态不应每次 append 新卡片，而应按 `toolCallId` patch 同一个 activity：

```text
tool_call.started
  -> ACTIVITY_SNAPSHOT(activity_tool_call_x, status=running)

tool_call.completed
  -> ACTIVITY_DELTA(activity_tool_call_x, replace /status completed, replace /resultSummary ...)
  -> append BUSINESS_RESULT surface_project_list_x
```

Plan 也是同理：

```text
plan.created
  -> ACTIVITY_SNAPSHOT(activity_plan_x)

todo.running / todo.completed
  -> ACTIVITY_DELTA(activity_plan_x, patch /todos/{id}/status)
```

### 8.5 文本与 Activity 的排序策略

AG-UI 里 tool call 可通过 `parentMessageId` 关联 assistant message。ANIFORCE 当前后端没有显式 parentMessageId，因此前端短期采用：

```text
currentAssistantMessageId = message.started.id || local assistant id
每个 tool activity.parentMessageId = currentAssistantMessageId
每个 business result.parentMessageId = currentAssistantMessageId
```

Home 渲染短期采用本轮内联区：

```text
历史 user/assistant messages
当前 streaming assistant message
当前 run activities / business surfaces
```

中期应升级为真正的 mixed message list：

```text
MessageItem[] = user text | assistant text | activity | business surface | approval
```

这样刷新历史会话时也能恢复工具卡和业务卡，而不是只保存在本轮前端内存。

### 8.6 A2UI / Bot UI 对业务组件的启发

CopilotKit A2UI 和 bot-ui 的启发是：业务结果应该是可序列化 UI surface，而不是写死在模型 Markdown 里。

ANIFORCE 第一阶段不引入完整 A2UI runtime，但采用同样思想：

```text
business result = surfaceId + component type + data model + actions
```

项目列表卡等价于一个固定 schema 的 surface：

```ts
{
  surfaceId: `project-list-${toolCallId}`,
  component: 'ProjectListSurface',
  data: { projects },
  actions: [
    { name: 'open_project', context: { projectId } },
    { name: 'create_campaign', context: { projectId } }
  ]
}
```

后续如果接入 A2UI，只需把 `ProjectListBlock` 替换成通用 surface renderer，数据模型不用推倒重来。

### 8.7 实现顺序修正

正确实现顺序：

1. 前端状态层先按 AG-UI 语义补齐 `messageId/toolCallId/parentMessageId/activityType`。
2. `Home.vue` 删除旧 `execution-trace`，接入真实 timeline renderer。
3. 工具 activity 用 `toolCallId` 原地更新，不重复追加。
4. `tool_call.completed` 派生 project-list business surface。
5. 视觉组件只消费 timeline block，不直接猜 SSE。
6. 后端后续补标准 AG-UI event adapter 或 `/ag-ui` endpoint。

## 9. 关键结论

这次问题不是单纯事件适配问题，而是交互模型必须统一，并且要与 AG-UI 的状态咬合一致：

```text
Agent 行动 = Activity Message
工具调用 = Tool Activity Snapshot + Delta
业务结果 = Serializable Business Surface
文本消息 = Text Message Stream
侧边栏 = 摘要与工作区，不是实时状态主展示
```

后续所有 Agent 能力都应按这个模型扩展。

# Agent Workspace 投影与上下文感知设计

## 1. 核心概念

### 1.1 问题定义

**能力 1：Workspace 是 Agent 执行的投影**

- Agent 调用工具后，结果应该渲染到 Workspace UI，而不是文本重复
- Agent 知道结果已在 UI 展示，只需要高亮重点和提供洞察

**能力 2：选中 / @mention 提供上下文**

- 用户可以选中实体（项目、素材、计划）作为对话上下文
- 用户可以 @mention 实体提供明确指向
- Agent 理解"这个"、"这些"指的是哪些实体

### 1.2 设计目标

```text
传统 Agent：
  用户："查询最近素材"
  Agent："以下是素材列表：\n1. 素材A...\n2. 素材B..."
  问题：文本冗长、不可交互

Workspace Agent：
  用户："查询最近素材"
  Agent 调用 list_materials 工具
  → Workspace 自动渲染素材卡片列表
  Agent："已展示 10 个素材，最近上传的是素材A（点击率 3.2%）"
  → 用户可以直接点击卡片查看详情
```

---

## 2. 架构设计

### 2.1 数据流

```text
┌─────────────────────────────────────────────────────────┐
│ Frontend Workspace                                      │
│  - Entity List (projects / campaigns / materials)      │
│  - Selection State (selectedEntities)                  │
│  - Draft State (draftEdits)                            │
└─────────────────────────────────────────────────────────┘
        ↓ collectContextSnapshot()
┌─────────────────────────────────────────────────────────┐
│ context_snapshot (前端快照)                             │
│  {                                                      │
│    route: "/projects?panel=materials",                 │
│    activePanel: "materials",                           │
│    selectedEntities: [                                 │
│      {type: "material", id: "M001", name: "素材A"},    │
│      {type: "material", id: "M002", name: "素材B"}     │
│    ],                                                   │
│    draftEdits: {...}                                   │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
        ↓ 随用户消息发送到 Backend
┌─────────────────────────────────────────────────────────┐
│ Backend session_state                                   │
│  - ui_snapshot (持久化 context_snapshot)               │
│  - linked_entities (关联实体详情)                      │
└─────────────────────────────────────────────────────────┘
        ↓ BusinessContextBuilder
┌─────────────────────────────────────────────────────────┐
│ business_context_summary (给 Agent 看的摘要)           │
│  """                                                    │
│  用户在素材管理面板                                     │
│  已选中 2 个素材：                                      │
│    - M001 素材A (image/jpeg, 上传于 2024-01-15)       │
│    - M002 素材B (video/mp4, 上传于 2024-01-16)        │
│  """                                                    │
└─────────────────────────────────────────────────────────┘
        ↓ Dynamic instructions
┌─────────────────────────────────────────────────────────┐
│ Agent 感知                                              │
│  - 当前在哪个页面                                       │
│  - 用户选中了什么                                       │
│  - 草稿状态是什么                                       │
└─────────────────────────────────────────────────────────┘
        ↓ 调用 MCP 工具
┌─────────────────────────────────────────────────────────┐
│ Tool Result Hook                                        │
│  tool_name: "list_materials"                           │
│  result: {materials: [...]}                            │
│  → 识别 projection_hint                                │
│  → 推送 workspace_projection 事件                      │
└─────────────────────────────────────────────────────────┘
        ↓ WebSocket
┌─────────────────────────────────────────────────────────┐
│ Frontend 接收 workspace_projection                      │
│  {                                                      │
│    type: "workspace_projection",                       │
│    projection_type: "entity_list",                     │
│    entity_type: "material",                            │
│    entities: [{id: "M001", ...}, ...]                  │
│  }                                                      │
│  → 渲染到 Workspace 列表                               │
│  → Agent 知道已渲染，不重复输出文本                    │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 能力 1：Workspace 投影

### 3.1 投影类型定义

```typescript
// frontend/packages/main-app/src/types/workspace.ts

export type WorkspaceProjection =
  | EntityListProjection
  | EntityDetailProjection
  | MetricsChartProjection
  | DraftUpdateProjection

export interface EntityListProjection {
  type: 'entity_list'
  entity_type: 'project' | 'campaign' | 'material'
  entities: Array<{
    id: string
    [key: string]: unknown
  }>
  metadata?: {
    total?: number
    filtered?: number
    sort_by?: string
  }
}

export interface EntityDetailProjection {
  type: 'entity_detail'
  entity_type: 'project' | 'campaign' | 'material'
  entity_id: string
  data: Record<string, unknown>
}

export interface MetricsChartProjection {
  type: 'metrics_chart'
  chart_type: 'line' | 'bar' | 'pie'
  data: Array<Record<string, unknown>>
  config?: {
    title?: string
    x_axis?: string
    y_axis?: string
  }
}

export interface DraftUpdateProjection {
  type: 'draft_update'
  entity_type: 'project' | 'campaign' | 'material'
  entity_id: string
  updates: Record<string, unknown>
}
```

### 3.2 MCP 工具返回 projection_hint

```python
# aniforce-agent/app/mcp_server.py

@mcp.tool()
async def list_materials(ctx: Context, limit: int = 20) -> dict:
    """列出广告素材"""
    token = _get_token(ctx)
    materials = await backend_client.list_materials(token=token, limit=limit)
  
    return {
        "status": "success",
        "materials": materials,
        # 🔥 关键：projection_hint 告诉系统这个结果应该投影到 Workspace
        "projection_hint": {
            "type": "entity_list",
            "entity_type": "material",
            "entities": materials,
            "metadata": {
                "total": len(materials)
            }
        }
    }
```

### 3.3 Backend 识别并推送投影事件

```python
# backend/app/api/v1/agent_routes.py

async def stream_agent_run_events(...):
    async for event in runtime.run_task(task, user_input):
        # 转发 SDK 原生事件
        yield event
      
        # 🔥 Hook：识别工具结果中的 projection_hint
        if event.get("type") == "tool_call_output_item":
            tool_output = event.get("output", {})
            projection_hint = tool_output.get("projection_hint")
          
            if projection_hint:
                # 推送 workspace 投影事件
                yield {
                    "type": "workspace_projection",
                    "projection_type": projection_hint["type"],
                    "data": projection_hint,
                    "source_tool": event.get("tool_name"),
                    "timestamp": datetime.utcnow().isoformat()
                }
```

### 3.4 Frontend 接收并渲染投影

```typescript
// frontend/packages/main-app/src/composables/useHomeAgentSession.ts

function handleWorkspaceProjection(projection: WorkspaceProjection) {
  switch (projection.projection_type) {
    case 'entity_list':
      // 渲染到 Workspace 列表
      store.updateWorkspaceList(
        projection.data.entity_type,
        projection.data.entities
      )
      break
    
    case 'entity_detail':
      // 打开实体详情面板
      store.openEntityDetail(
        projection.data.entity_type,
        projection.data.entity_id,
        projection.data.data
      )
      break
    
    case 'metrics_chart':
      // 渲染图表
      store.updateWorkspaceChart(projection.data)
      break
  }
}
```

### 3.5 Agent 知道已投影，精简输出

```python
# Agent dynamic instructions

def workspace_instructions(ctx: RunContextWrapper[WorkspaceRunContext]) -> str:
    return f"""
你是 ANIFORCE 助手。

# 输出规则
- 当你调用返回列表的工具（list_*），结果会自动显示在用户的 Workspace
- 你不需要重复列举所有项目，只需要：
  1. 确认已展示（"已为你展示了 N 个..."）
  2. 高亮关键发现（"最新的是..."、"点击率最高的是..."）
  3. 提供下一步建议

示例：
❌ 错误：重复列举
  "以下是素材列表：\n1. 素材A\n2. 素材B..."
  
✅ 正确：精简输出
  "已展示 10 个素材。最近上传的是素材A（点击率 3.2%），表现最好的是素材C（CTR 5.1%）。建议重点投放素材C。"
"""
```

---

## 4. 能力 2：选中与 @mention

### 4.1 Frontend 选中状态管理

```typescript
// frontend/packages/main-app/src/composables/useWorkspaceSelection.ts

export function useWorkspaceSelection() {
  const selectedEntities = ref<SelectedEntity[]>([])
  
  function selectEntity(entity: SelectedEntity) {
    const existing = selectedEntities.value.find(e => 
      e.type === entity.type && e.id === entity.id
    )
    if (!existing) {
      selectedEntities.value.push(entity)
    }
  }
  
  function deselectEntity(type: string, id: string) {
    selectedEntities.value = selectedEntities.value.filter(e =>
      !(e.type === type && e.id === id)
    )
  }
  
  function clearSelection() {
    selectedEntities.value = []
  }
  
  return {
    selectedEntities: readonly(selectedEntities),
    selectEntity,
    deselectEntity,
    clearSelection
  }
}
```

### 4.2 选中状态注入 context_snapshot

```typescript
// frontend/packages/main-app/src/composables/useHomeAgentSession.ts

function collectContextSnapshot(): AgentContextSnapshot {
  const { selectedEntities } = useWorkspaceSelection()
  
  return {
    route: route.fullPath,
    activePanel: getCurrentPanel(),
    selectedEntities: selectedEntities.value.map(e => ({
      type: e.type,
      id: e.id,
      name: e.name,
      // 可选：附加关键字段用于 Agent 快速理解
      _summary: e.type === 'material' 
        ? `${e.name} (${e.format}, CTR ${e.ctr}%)`
        : e.name
    })),
    draftEdits: getDraftEdits()
  }
}
```

### 4.3 Backend 构建选中实体摘要

```python
# backend/app/services/business_context_builder.py

class BusinessContextBuilder:
    async def build_selected_entities_summary(
        self,
        selected_entities: list[dict],
    ) -> str:
        """构建选中实体的摘要"""
        if not selected_entities:
            return ""
      
        lines = ["用户已选中以下实体："]
      
        for entity in selected_entities:
            entity_type = entity["type"]
            entity_id = entity["id"]
          
            # 从 DB 查询详情
            if entity_type == "material":
                material = await self.material_repo.get(entity_id)
                lines.append(
                    f"  - 素材 {material.name} "
                    f"(ID: {entity_id}, 格式: {material.format}, "
                    f"上传于: {material.created_at}, CTR: {material.ctr}%)"
                )
            elif entity_type == "campaign":
                campaign = await self.campaign_repo.get(entity_id)
                lines.append(
                    f"  - 广告计划 {campaign.name} "
                    f"(ID: {entity_id}, 预算: {campaign.budget}, "
                    f"状态: {campaign.status})"
                )
      
        return "\n".join(lines)
```

### 4.4 Agent 理解选中上下文

```python
# Agent dynamic instructions

def workspace_instructions(ctx: RunContextWrapper[WorkspaceRunContext]) -> str:
    selected_summary = ctx.context.selected_entities_summary or ""
  
    return f"""
你是 ANIFORCE 助手。

{selected_summary}

# 指代消解规则
当用户说"这个"、"这些"、"它们"时：
1. 优先指向已选中的实体
2. 其次指向最近操作的实体
3. 如果不确定，请用户明确指向

示例：
  用户选中了素材 M001、M002
  用户："这两个的点击率怎么样？"
  → 理解为：查询 M001、M002 的点击率
  → 调用 get_material_metrics(material_ids=["M001", "M002"])
"""
```

### 4.5 @mention 解析（可选扩展）

```typescript
// frontend/packages/main-app/src/utils/mentionParser.ts

export function parseMentions(text: string): {
  cleanText: string
  mentions: Array<{ type: string; id: string; name: string }>
} {
  const mentionRegex = /@(\w+)_(\w+)(?:\(([^)]+)\))?/g
  const mentions: Array<{ type: string; id: string; name: string }> = []
  
  const cleanText = text.replace(mentionRegex, (match, type, id, name) => {
    mentions.push({
      type,
      id,
      name: name || id
    })
    return name || id  // 替换成实体名称，LLM 更好理解
  })
  
  return { cleanText, mentions }
}

// 使用示例：
// 输入："@material_M001(素材A) 和 @material_M002(素材B) 的点击率"
// 输出：
//   cleanText: "素材A 和 素材B 的点击率"
//   mentions: [{type: "material", id: "M001", name: "素材A"}, ...]
```

---

## 5. 实现步骤

### Phase 1：Workspace 投影基础（优先级：高）

**目标：** Agent 调用工具后，结果自动渲染到 Workspace

**改动：**

1. MCP 工具返回增加 `projection_hint` 字段
2. Backend 识别 `projection_hint` 并推送 `workspace_projection` 事件
3. Frontend 接收并渲染到 Workspace 列表
4. Agent instructions 加入"不重复列举"规则

**工作量：** 2-3 天

**验收标准：**

- 用户："查询最近素材"
- Workspace 自动展示素材卡片列表
- Agent 回复精简："已展示 10 个素材，最新的是..."

---

### Phase 2：选中状态感知（优先级：高）

**目标：** Agent 理解用户选中了什么

**改动：**

1. Frontend 实现 `useWorkspaceSelection`
2. `collectContextSnapshot` 包含 `selectedEntities`
3. `BusinessContextBuilder` 构建选中实体摘要
4. Agent dynamic instructions 注入选中上下文

**工作量：** 2 天

**验收标准：**

- 用户选中素材 M001、M002
- 用户："这两个的点击率怎么样？"
- Agent 正确调用 `get_material_metrics(material_ids=["M001", "M002"])`

---

### Phase 3：@mention 解析（优先级：中）

**目标：** 用户可以 @实体 明确指向

**改动：**

1. Frontend 实现 mention 输入提示
2. 实现 `parseMentions` 解析 @mention
3. 解析后的 mentions 注入 `context_snapshot`

**工作量：** 1-2 天

**验收标准：**

- 用户输入："@M001 和 @M002 的点击率"
- 前端解析成 mentions + cleanText
- Agent 正确理解

---

### Phase 4：投影类型扩展（优先级：低）

**目标：** 支持更多投影类型（图表、详情面板）

**改动：**

1. 实现 `MetricsChartProjection`
2. 实现 `EntityDetailProjection`
3. Frontend 渲染图表和详情面板

**工作量：** 按需实现

---

## 6. 关键设计决策

### 6.1 projection_hint 放在工具返回 vs 单独事件？

**选qin**

**理由：**

- 工具最清楚结果应该怎么展示
- 不需要额外的协议层
- Backend 只做转发，逻辑简单

### 6.2 选中状态存在哪？

**选择：** Frontend 临时状态 + context_snapshot 传递

**理由：**

- 选中是临时 UI 状态，不需要持久化
- 每次发消息时通过 context_snapshot 传递给 Backend
- Backend 不存储选中状态，只用于当次 run

### 6.3 Agent 是否应该主动操作选中状态？

**选择：** 不应该

**理由：**

- 选中是用户主动操作，Agent 不应该代替用户选
- Agent 可以建议"请选中素材 M001 后再询问"
- 避免 Agent 和用户的控制权冲突

---

## 7. 未来扩展

### 7.1 Workspace Diff（变更高亮）

```typescript
// Agent 修改了实体后，Workspace 高亮变更
{
  type: "workspace_diff",
  entity_type: "campaign",
  entity_id: "C001",
  changes: {
    budget: { old: 1000, new: 5000 },
    status: { old: "draft", new: "active" }
  }
}
```

### 7.2 Workspace Collaboration（多用户协作）

```typescript
// 其他用户修改了同一个实体，实时同步
{
  type: "workspace_sync",
  entity_type: "project",
  entity_id: "P001",
  updated_by: "user_002",
  updates: {...}
}
```

### 7.3 Workspace Undo/Redo

```typescript
// Agent 操作可撤销
{
  type: "workspace_action",
  action_id: "act_001",
  reversible: true,
  undo_payload: {...}
}
```

---

## 8. 总结

**核心价值：**

- Agent 不再是"文本聊天机器人"，而是"Workspace 操作助手"
- 用户看到的是可交互的 UI，不是冗长的文本
- Agent 理解用户的 UI 操作上下文（选中、草稿、当前页面）

**实现原则：**

- Workspace 投影：工具返回 `projection_hint` → Backend 转发 → Frontend 渲染
- 选中感知：Frontend `selectedEntities` → `context_snapshot` → Agent dynamic instructions
- 保持简单：不引入复杂的双向绑定，单向数据流足够

**优先级：**

1. ✅ Workspace 投影基础（立即做）
2. ✅ 选中状态感知（立即做）
3. ⚠️ @mention 解析（按需做）
4. ⏸️ 投影扩展（未来做）

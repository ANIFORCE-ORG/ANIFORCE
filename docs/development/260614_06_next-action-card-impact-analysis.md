# Next Action Card 技术改造影响范围分析

日期：2026-06-14

## 问题
实现"AI 行为引导而非数据重复"功能，需要改造项目中哪些部分？

## 改造范围清单

### 1. System Prompt（必改）✅

**文件**：`backend/app/agent_platform/prompts.py`

**改动原因**：
- AI 当前的行为是"查询完数据后，用 Markdown 重复一遍"
- 需要告诉 AI："数据已投影到工作区，只需给出下一步建议"

**具体修改**：
```python
# 新增规则段落
## AG-UI 交互规则

当你调用工具并将结果投影到工作区时：

### 规则 1：避免重复数据
❌ 不要用 Markdown 重复列出已在工作区展示的数据
✅ 简单说明"找到 X 个项目，已展示在工作区"

### 规则 2：提供下一步行为建议
告诉用户可以做什么，使用以下格式：
- 具体行为（"为 Candy Blast 创建投放计划"）
- 不要模糊建议（"你可以进行操作"）
```

**影响**：
- AI 回复内容变化
- 需要测试确保 AI 遵守新规则

**工作量**：0.5 天

---

### 2. MCP Tools 返回格式（可选改，建议改）⚠️

**文件**：`backend/app/mcp/tools/project_tools.py`（及其他 MCP tools）

**改动原因**：
- 当前 MCP Tool 返回纯数据或 Markdown 文本
- 如果 Tool 能直接返回"建议的下一步行为"，AI 更容易理解和传递

**具体修改（list_projects 示例）**：
```python
# 当前返回格式
def list_projects(limit: int = 20) -> str:
    projects = query_projects(limit)
    return format_projects_as_markdown(projects)  # 返回 Markdown 文本

# 改造后返回格式（Option 1: 结构化）
def list_projects(limit: int = 20) -> dict:
    projects = query_projects(limit)
    return {
        "data": projects,
        "summary": f"找到 {len(projects)} 个项目",
        "next_actions": [
            {"label": "查看某个项目详情", "prompt_template": "查看项目 {project_id} 的详情"},
            {"label": "创建新的投放计划", "action": "open_workspace", "component": "CampaignDraft"},
            {"label": "分析项目投放效果", "prompt": "分析所有项目的投放效果"}
        ]
    }

# 改造后返回格式（Option 2: 纯文本 + System Prompt 约束）
def list_projects(limit: int = 20) -> str:
    projects = query_projects(limit)
    # 返回简短摘要，不列详细数据
    return f"找到 {len(projects)} 个项目。数据已在工作区展示。"
```

**影响**：
- 如果改成结构化返回，需要修改所有 MCP Tool
- 如果只改返回文本（简化版），改动较小
- 前端需要解析结构化数据（如果选 Option 1）

**工作量**：
- Option 1（结构化）：2-3 天（10 个 tools）
- Option 2（简化文本）：0.5 天

**建议**：先用 Option 2（只改返回文本），后续再升级到 Option 1

---

### 3. 后端 SSE 事件（需要新增）✅

**文件**：`backend/app/agent_platform/adapters/openai_adapter.py`

**改动原因**：
- 当前只有 tool_call.completed 事件返回工具结果
- 需要新增事件：workspace.projection 和 next_actions.created

**具体修改**：
```python
# 新增事件类型
class EventType(str, Enum):
    # ... 现有事件
    WORKSPACE_PROJECTION = "workspace.projection"
    NEXT_ACTIONS_CREATED = "next_actions.created"

# 在 tool_call.completed 后发送
async def handle_tool_completed(self, tool_call_id, result):
    # 1. 发送 tool_call.completed（现有）
    yield {
        "event": "tool_call.completed",
        "data": {"tool_call_id": tool_call_id, "result": result}
    }
    
    # 2. 判断是否需要投影到工作区
    if self._should_project_to_workspace(tool_name, result):
        yield {
            "event": "workspace.projection",
            "data": {
                "component": self._get_workspace_component(tool_name),
                "summary": f"{len(result['data'])} 个项目已展示在工作区",
                "data_count": len(result['data']),
                "tool_call_id": tool_call_id
            }
        }
    
    # 3. 如果 MCP Tool 返回了 next_actions，发送
    if "next_actions" in result:
        yield {
            "event": "next_actions.created",
            "data": {
                "actions": result["next_actions"],
                "parent_message_id": self.current_message_id
            }
        }
```

**影响**：
- 新增 2 个事件类型
- 需要映射规则：tool_name → workspace component
- 前端需要监听新事件

**工作量**：1 天

---

### 4. 前端 Timeline Block 类型（需要新增）✅

**文件**：`frontend/packages/main-app/src/types/agent.ts`

**改动原因**：
- 当前 Timeline 只有 tool_activity、project_list 等
- 需要新增 workspace_projection 和 next_action_card 类型

**具体修改**：
```typescript
// 新增类型定义
export type AgentTimelineBlock =
  | ToolActivityBlock
  | ProjectListBlock
  | PlanBlock
  | WorkspaceProjectionBlock    // 新增
  | NextActionCardBlock          // 新增
  | ErrorBlock

export interface WorkspaceProjectionBlock {
  type: 'workspace_projection'
  id: string
  messageId: string
  content: {
    component: string
    summary: string
    dataCount: number
    icon: string
  }
  createdAt: number
}

export interface NextActionCardBlock {
  type: 'next_action_card'
  id: string
  messageId: string
  content: {
    title?: string
    actions: Action[]
  }
  createdAt: number
}

export interface Action {
  id: string
  label: string
  description?: string
  icon?: string
  variant: 'primary' | 'secondary' | 'ghost'
  handler: {
    type: 'prompt' | 'tool' | 'workspace' | 'dialog'
    payload: any
  }
}
```

**影响**：
- TypeScript 类型扩展
- Timeline 渲染逻辑需要处理新类型

**工作量**：0.5 天

---

### 5. 前端事件监听（需要新增）✅

**文件**：`frontend/packages/main-app/src/composables/useHomeAgentSession.ts`

**改动原因**：
- 当前只监听 tool_call.*, message.* 等事件
- 需要监听新增的 workspace.projection 和 next_actions.created

**具体修改**：
```typescript
// 在 SSE 事件处理中新增
const handleSSEEvent = (event: SSEEvent) => {
  switch (event.event) {
    // ... 现有事件
    
    case 'workspace.projection':
      // 创建 WorkspaceProjectionBlock
      const projectionBlock: WorkspaceProjectionBlock = {
        type: 'workspace_projection',
        id: generateId(),
        messageId: `projection_${event.data.tool_call_id}`,
        content: {
          component: event.data.component,
          summary: event.data.summary,
          dataCount: event.data.data_count,
          icon: 'workspace'
        },
        createdAt: Date.now()
      }
      timelineBlocks.value.push(projectionBlock)
      break
      
    case 'next_actions.created':
      // 创建 NextActionCardBlock
      const actionBlock: NextActionCardBlock = {
        type: 'next_action_card',
        id: generateId(),
        messageId: `actions_${event.data.parent_message_id}`,
        content: {
          actions: event.data.actions
        },
        createdAt: Date.now()
      }
      timelineBlocks.value.push(actionBlock)
      break
  }
}
```

**影响**：
- SSE 事件处理分支增加
- Timeline 状态更新逻辑

**工作量**：0.5 天

---

### 6. 前端 UI 组件（需要新增）✅

**文件**：
- `frontend/packages/main-app/src/components/agent/timeline/WorkspaceProjectionCard.vue`
- `frontend/packages/main-app/src/components/agent/timeline/NextActionCard.vue`

**改动原因**：
- 需要渲染新的 Timeline Block 类型

**具体修改**：
参考设计文档中的 Vue 组件代码

**影响**：
- 新增 2 个 Vue 组件
- TimelineBlockRenderer 需要映射新类型
- CSS 样式

**工作量**：1 天

---

### 7. 前端 Action Handler（需要新增）✅

**文件**：`frontend/packages/main-app/src/composables/useActionHandler.ts`

**改动原因**：
- 需要处理用户点击 Action 按钮的逻辑
- 支持 4 种 handler 类型：prompt / tool / workspace / dialog

**具体修改**：
```typescript
export function useActionHandler() {
  const { sendMessage } = useChatSession()
  const { openWorkspace } = useWorkspace()
  const router = useRouter()
  
  function handleAction(action: Action) {
    const { handler } = action
    
    switch (handler.type) {
      case 'prompt':
        // 发送 prompt
        sendMessage(interpolate(handler.payload.template, handler.payload.prefill))
        break
        
      case 'workspace':
        // 打开工作区
        openWorkspace({
          component: handler.payload.component,
          props: handler.payload.props
        })
        break
        
      case 'tool':
        // 直接调用工具（需要后端支持）
        // TODO: 实现
        break
        
      case 'dialog':
        // 打开对话框
        // TODO: 实现
        break
    }
  }
  
  return { handleAction }
}
```

**影响**：
- 新增 composable
- 需要集成到 NextActionCard 组件

**工作量**：0.5 天

---

### 8. Skills（不需要改）❌

**原因**：
- Skills 是领域知识和工作流
- Next Action Card 是 UI 交互层
- 两者解耦，Skills 不需要感知

**但是**：如果某些 Skill 的返回也需要行为引导，可以在 Skill 的返回格式中增加建议

**工作量**：0（可选扩展）

---

### 9. AG-UI 协议（不需要改）❌

**原因**：
- workspace.projection 和 next_actions.created 是自定义事件
- 不是 AG-UI 标准协议的一部分
- 在你们项目的 SSE 层实现即可

**备注**：如果未来要对齐 AG-UI 标准，可能需要：
- 用 ACTIVITY_SNAPSHOT 表达 workspace projection
- 用 CUSTOM 事件类型

**工作量**：0（当前阶段）

---

### 10. API 接口（不需要改）❌

**原因**：
- SSE streaming 接口已存在（`/api/agent/chat`）
- 只是新增事件类型，接口签名不变

**工作量**：0

---

## 改造优先级和依赖关系

```
P0（核心路径）：
1. System Prompt 修改           → 0.5 天
2. MCP Tool 返回格式简化        → 0.5 天
3. 后端新增 2 个 SSE 事件       → 1 天
4. 前端类型定义扩展             → 0.5 天
5. 前端事件监听                 → 0.5 天
6. 前端 UI 组件                 → 1 天
7. 前端 Action Handler          → 0.5 天

总计：约 5 天（MVP 版本）

P1（增强）：
- MCP Tool 返回结构化 next_actions  → 2 天
- 更多 Action Handler 类型支持      → 1 天

P2（优化）：
- AI 动态生成 suggestions（类似 CopilotKit） → 3 天
```

## 风险点

1. **System Prompt 效果不确定**：需要多次调试才能让 AI 稳定遵守新规则
2. **前后端协议对齐**：SSE 事件字段需要严格对齐
3. **用户体验**：Action 按钮的文案需要足够清晰
4. **兼容性**：旧的消息历史可能没有新事件，需要降级处理

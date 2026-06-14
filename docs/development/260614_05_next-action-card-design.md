# Next Action Card 与 AI 引导交互设计

日期：2026-06-14

## 1. 问题背景

当前 ANIFORCE Agent 存在的问题：

```text
用户: "查看项目列表"

❌ 当前行为：
AI: "您目前有 11 个项目：
1. 260614 (ID: fb20..., 预算 ¥50,000)
2. Candy Blast (ID: 296a..., 预算 ¥50,000)
..."

问题：
- 数据已经投影到右侧工作区，AI 文本重复了一遍
- 用户不知道下一步该做什么
- 没有可点击的行为引导
- 文本信息冗余，体验差
```

## 2. 设计目标

**核心原则**：当数据已投影到工作区时，AI 应该提供**行为引导**而非**数据重复**。

```text
✅ 目标行为：
用户: "查看项目列表"

[工具调用卡片] "项目列表查询完成"
[投影通知] "11 个项目已展示在工作区"
[下一步行为卡片]
  → 查看某个项目详情
  → 创建新的投放计划
  → 分析项目投放效果
```

## 3. 新增 Timeline Block 类型

### 3.1 WorkspaceProjection（工作区投影通知）

```typescript
interface WorkspaceProjectionBlock {
  type: 'workspace_projection'
  id: string
  messageId: string
  parentMessageId: string
  createdAt: number
  content: {
    component: 'ProjectListWorkspace' | 'ProjectDetailWorkspace' | 'CampaignDraftWorkspace'
    summary: string      // "11 个项目已展示在工作区"
    dataCount?: number   // 11
    icon: string         // 'list' | 'folder' | 'campaign'
  }
}
```

### 3.2 NextActionCard（下一步行为卡片）

```typescript
interface NextActionCardBlock {
  type: 'next_action_card'
  id: string
  messageId: string
  parentMessageId: string
  createdAt: number
  content: {
    title?: string       // "你可以："
    actions: Action[]
  }
}

interface Action {
  id: string
  label: string         // "查看某个项目详情"
  description?: string  // "深入了解项目的投放数据和预算使用情况"
  icon?: string
  variant: 'primary' | 'secondary' | 'ghost'
  handler: ActionHandler
}

interface ActionHandler {
  type: 'prompt' | 'tool' | 'workspace' | 'dialog'
  payload: {
    // type=prompt: 发送提示词
    template?: string   // "查看项目 {projectId} 的详情"
    prefill?: Record<string, any>
    
    // type=tool: 直接调用工具
    toolName?: string
    arguments?: Record<string, any>
    
    // type=workspace: 打开工作区
    component?: string
    props?: Record<string, any>
    
    // type=dialog: 打开对话框
    dialogType?: string
    dialogProps?: Record<string, any>
  }
}
```

### 3.3 ContextualSuggestion（上下文建议）

基于工作区当前数据，动态生成具体建议：

```typescript
interface ContextualSuggestionBlock {
  type: 'contextual_suggestion'
  id: string
  messageId: string
  parentMessageId: string
  createdAt: number
  content: {
    context: {
      workspaceType: string
      dataKeys: string[]  // ['project_001', 'project_002']
    }
    suggestions: Suggestion[]
  }
}

interface Suggestion {
  id: string
  text: string          // "为「Candy Blast」创建投放计划"
  prompt: string        // 点击后发送的完整 prompt
  confidence: number    // 0-1，排序依据
  metadata?: Record<string, any>
}
```

## 4. 视觉设计

### 4.1 WorkspaceProjection 组件

```vue
<div class="workspace-projection-card">
  <div class="projection-icon">
    <span class="material-symbols-outlined">{{ content.icon }}</span>
  </div>
  <div class="projection-content">
    <div class="projection-summary">{{ content.summary }}</div>
    <div class="projection-hint">已在工作区展示</div>
  </div>
</div>

<style scoped>
.workspace-projection-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  margin: 8px 0;
}

.projection-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(59, 130, 246, 0.1);
  border-radius: 10px;
  color: #3b82f6;
}

.projection-summary {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
}

.projection-hint {
  font-size: 12px;
  color: #64748b;
}
</style>
```

### 4.2 NextActionCard 组件

```vue
<div class="next-action-card">
  <div v-if="content.title" class="action-title">{{ content.title }}</div>
  <div class="action-list">
    <button
      v-for="action in content.actions"
      :key="action.id"
      :class="['action-button', `action-${action.variant}`]"
      @click="handleAction(action)"
    >
      <span v-if="action.icon" class="action-icon material-symbols-outlined">
        {{ action.icon }}
      </span>
      <div class="action-text">
        <div class="action-label">{{ action.label }}</div>
        <div v-if="action.description" class="action-description">
          {{ action.description }}
        </div>
      </div>
      <span class="action-arrow material-symbols-outlined">arrow_forward</span>
    </button>
  </div>
</div>

<style scoped>
.next-action-card {
  padding: 16px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin: 12px 0;
}

.action-title {
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
  margin-bottom: 12px;
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-button {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-button:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  transform: translateX(2px);
}

.action-button.action-primary {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border-color: #3b82f6;
  color: white;
}

.action-button.action-primary:hover {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  transform: translateX(2px);
}

.action-icon {
  font-size: 20px;
  color: inherit;
}

.action-text {
  flex: 1;
  text-align: left;
}

.action-label {
  font-size: 14px;
  font-weight: 500;
}

.action-description {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 2px;
}

.action-arrow {
  font-size: 18px;
  opacity: 0.6;
}
</style>
```

## 5. AI Prompt 改造

### 5.1 新增规则到 System Prompt

在 `backend/app/agent_platform/prompts.py` 中增加：

```python
## AG-UI 交互规则

当你调用工具并将结果投影到工作区时，你的回复应该遵循以下规则：

### 规则 1：避免重复数据

❌ 错误示例：
```
找到 11 个项目：
1. 260614 (ID: fb20..., 预算 ¥50,000)
2. Candy Blast...
（工作区已经显示了这些数据）
```

✅ 正确示例：
```
找到 11 个项目，已展示在工作区。
```

### 规则 2：提供下一步行为引导

当数据已投影到工作区后，你应该告诉用户可以做什么，而不是重复数据。

使用以下格式：

```
找到 {数量} 个 {对象}，已展示在工作区。

你可以：
- {具体行为 1}
- {具体行为 2}
- {具体行为 3}
```

### 规则 3：行为要具体可执行

❌ 错误：模糊建议
```
你可以：
- 查看详情
- 进行操作
```

✅ 正确：具体行为
```
你可以：
- 查看「Candy Blast」项目的详细数据
- 为「260614」项目创建投放计划
- 分析所有项目的预算使用情况
```

### 规则 4：结合上下文数据

基于工作区实际数据，给出针对性建议：

```
找到 11 个项目，已展示在工作区。

我注意到：
- 「Candy Blast」项目预算充足但投放计划较少
- 「260614」项目已接近预算上限

建议：
- 为 Candy Blast 增加投放计划
- 查看 260614 的预算使用详情
```

## 示例对话

### 场景 1：查看项目列表

**用户**：查看我的项目列表

**Timeline 输出**：
```
[ToolActivityBlock] 
status: completed
title: "项目列表查询完成"
summary: "找到 11 个项目"

[WorkspaceProjectionBlock]
component: ProjectListWorkspace
summary: "11 个项目已展示在工作区"
dataCount: 11

[NextActionCardBlock]
actions:
  - label: "查看某个项目详情"
    icon: "info"
    variant: "primary"
    handler: { type: "prompt", template: "查看项目 {projectId} 的详情" }
    
  - label: "创建新的投放计划"
    icon: "add_circle"
    variant: "secondary"
    handler: { type: "workspace", component: "CampaignDraftWorkspace" }
    
  - label: "分析项目投放效果"
    icon: "analytics"
    variant: "ghost"
    handler: { type: "prompt", template: "分析所有项目的投放效果" }
```

**AI 文本输出**（可选，简短）：
```
找到 11 个项目，已在工作区展示。
```

### 场景 2：创建项目后

**用户**：创建一个项目，名称是 RPG 出海，预算 100000

**Timeline 输出**：
```
[ToolActivityBlock]
status: completed
title: "项目创建完成"

[WorkspaceProjectionBlock]
component: ProjectDetailWorkspace
summary: "项目「RPG 出海」已创建"

[NextActionCardBlock]
actions:
  - label: "为这个项目创建投放计划"
    description: "设置目标受众和预算分配"
    icon: "campaign"
    variant: "primary"
    handler: { type: "workspace", component: "CampaignDraftWorkspace", props: { projectId: "xxx" } }
    
  - label: "上传投放素材"
    icon: "upload"
    variant: "secondary"
    handler: { type: "dialog", dialogType: "MaterialUpload" }
```

**AI 文本输出**：
```
✅ 项目「RPG 出海」创建成功（预算 ¥100,000）
```

## 6. 后端实现

### 6.1 MCP Tool 返回格式改造

MCP Tool 除了返回数据，还应该返回**建议的下一步行为**：

```python
# list_projects MCP Tool 示例
def list_projects(limit: int = 20) -> dict:
    projects = query_projects(limit=limit)
    
    return {
        "type": "project.list",
        "data": {
            "projects": projects,
            "total": len(projects)
        },
        "next_actions": [
            {
                "id": "view_detail",
                "label": "查看某个项目详情",
                "handler": {
                    "type": "prompt",
                    "template": "查看项目 {projectId} 的详情"
                }
            },
            {
                "id": "create_campaign",
                "label": "创建新的投放计划",
                "handler": {
                    "type": "workspace",
                    "component": "CampaignDraftWorkspace"
                }
            },
            {
                "id": "analyze",
                "label": "分析项目投放效果",
                "handler": {
                    "type": "prompt",
                    "template": "分析所有项目的投放效果"
                }
            }
        ]
    }
```

### 6.2 SSE 事件扩展

新增两种事件类型：

```python
# 工作区投影事件
{
    "event_type": "workspace.projection",
    "payload": {
        "component": "ProjectListWorkspace",
        "summary": "11 个项目已展示在工作区",
        "data_count": 11,
        "icon": "list",
        "tool_call_id": "call_xxx"
    }
}

# 下一步行为事件
{
    "event_type": "next_actions.created",
    "payload": {
        "title": "你可以：",
        "actions": [
            {
                "id": "view_detail",
                "label": "查看某个项目详情",
                "icon": "info",
                "variant": "primary",
                "handler": {
                    "type": "prompt",
                    "template": "查看项目 {projectId} 的详情"
                }
            }
        ],
        "parent_message_id": "msg_xxx"
    }
}
```

## 7. 前端实现

### 7.1 扩展 Timeline Block 类型

在 `frontend/packages/main-app/src/types/agent.ts` 中：

```typescript
export type AgentTimelineBlock =
  | TextBlock
  | ToolActivityBlock
  | PlanBlock
  | ProjectListBlock
  | WorkspaceProjectionBlock    // 新增
  | NextActionCardBlock          // 新增
  | ContextualSuggestionBlock    // 新增
  | ErrorBlock
```

### 7.2 创建新组件

```text
frontend/packages/main-app/src/components/agent/timeline/
  ├── WorkspaceProjectionCard.vue
  ├── NextActionCard.vue
  └── ContextualSuggestionChips.vue
```

### 7.3 TimelineBlockRenderer 更新

```vue
<!-- TimelineBlockRenderer.vue -->
<template>
  <component
    :is="blockComponent"
    :block="block"
    @action="handleAction"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ToolActivityBlock from './ToolActivityBlock.vue'
import ProjectListBlock from './ProjectListBlock.vue'
import WorkspaceProjectionCard from './WorkspaceProjectionCard.vue'
import NextActionCard from './NextActionCard.vue'

const props = defineProps<{
  block: AgentTimelineBlock
}>()

const emit = defineEmits<{
  action: [payload: any]
}>()

const blockComponent = computed(() => {
  switch (props.block.type) {
    case 'tool_activity': return ToolActivityBlock
    case 'project_list': return ProjectListBlock
    case 'workspace_projection': return WorkspaceProjectionCard
    case 'next_action_card': return NextActionCard
    default: return null
  }
})

function handleAction(payload: any) {
  emit('action', payload)
}
</script>
```

### 7.4 Action Handler 实现

```typescript
// useActionHandler.ts
export function useActionHandler() {
  const router = useRouter()
  const { sendMessage } = useChatSession()
  const { openWorkspace } = useWorkspace()
  
  function handleAction(action: Action) {
    const { handler } = action
    
    switch (handler.type) {
      case 'prompt':
        // 发送提示词
        const prompt = interpolateTemplate(handler.payload.template, handler.payload.prefill)
        sendMessage(prompt)
        break
        
      case 'tool':
        // 直接调用工具（需要后端支持）
        callTool(handler.payload.toolName, handler.payload.arguments)
        break
        
      case 'workspace':
        // 打开工作区
        openWorkspace({
          component: handler.payload.component,
          props: handler.payload.props
        })
        break
        
      case 'dialog':
        // 打开对话框
        openDialog(handler.payload.dialogType, handler.payload.dialogProps)
        break
    }
  }
  
  return { handleAction }
}
```

## 8. 实施优先级

### P0（立即实施）

1. ✅ 创建设计文档
2. 扩展 Timeline Block 类型定义
3. 创建 WorkspaceProjectionCard 组件
4. 创建 NextActionCard 组件
5. 修改 System Prompt，增加 AG-UI 交互规则

### P1（本周完成）

1. MCP Tool 返回格式增加 next_actions
2. 后端发送 workspace.projection 事件
3. 后端发送 next_actions.created 事件
4. 前端 Action Handler 完整实现
5. 测试完整交互流程

### P2（后续优化）

1. ContextualSuggestion 动态生成
2. Action 执行后的反馈动画
3. 多轮对话中的上下文感知
4. Action 的权限控制和条件判断

## 9. 验收标准

### 场景：查看项目列表

**输入**：用户发送 "查看项目列表"

**期望输出**：
1. ✅ 出现工具调用卡片 "项目列表查询完成"
2. ✅ 出现工作区投影卡片 "11 个项目已展示在工作区"
3. ✅ 出现下一步行为卡片，包含 3 个可点击行为
4. ✅ AI 文本回复简短（不超过 2 句话）
5. ✅ 右侧工作区显示项目列表
6. ✅ 点击行为卡片中的按钮能正确触发对应动作

**禁止出现**：
1. ❌ AI 用文本重复列出 11 个项目的详细信息
2. ❌ 用户不知道下一步该做什么
3. ❌ 需要手动输入 prompt 才能继续操作

## 10. 参考资料

- AG-UI Protocol: `docs/development/260614_01_agentic-timeline-interaction-design.md`
- CopilotKit Suggestions: `resources/CopilotKit/packages/react-core/src/types/chat-suggestion-configuration.ts`
- 现有 Timeline: `frontend/packages/main-app/src/components/agent/timeline/`


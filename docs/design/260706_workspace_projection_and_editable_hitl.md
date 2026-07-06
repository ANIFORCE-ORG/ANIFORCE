# Workspace 投影与可编辑 HITL 审批方案

日期：2026-07-06
状态：设计 + 首版实现

---

## 1. 背景

ANIFORCE 首页是 Agent + Workspace 双栏结构。当前 Workspace 存在两个问题：

1. **重复实现业务页面**：`ProjectListWorkspace.vue` 自己画项目卡片，没有复用 `ProjectCollectionView`。
2. **审批不可编辑**：`create_project` 触发 HITL 后，前端只能 approve/reject，用户无法在 Workspace 里改 Agent 给出的参数，必须回到聊天框用自然语言纠正。

目标：让 Workspace 成为 Agent 和用户共同操作 SaaS 的真实工作台，做到「Agent 说到哪、工具做到哪、用户看到哪、能直接改哪」。

---

## 2. 核心原则

### 2.1 投影 ≠ 审批

所有工具调用都应产生 Workspace 投影，但只有高风险工具才进入 HITL 审批。

| 工具 | 投影 | 审批 |
|------|------|------|
| `list_projects` | 项目列表 | 否 |
| `get_project_detail` | 项目详情 | 否 |
| `list_materials` | 素材列表 | 否 |
| `create_project` | 创建表单（可编辑） | 是 |
| `delete_project` | 删除确认 | 是 |
| `create_campaign` | 创建表单（可编辑） | 是 |
| `update_campaign_status` | 状态变更确认 | 是 |

### 2.2 复用页面组件，不新造业务卡片

Workspace 不重新实现项目卡片、素材卡片、广告计划卡片。只做投影容器：

- `project.list` → `ProjectCollectionView`
- `material.list` → `MaterialCollectionView`
- `campaign.list` → `CampaignCollectionView`

### 2.3 复用页面表单字段，不新造 Agent 专用 schema

项目创建表单字段来自 `CreateProjectModal.vue` 现有的 `ProjectFormData`：

```ts
interface ProjectFormModel {
  name: string
  product: string
  countries: string      // 对应 API 的 target_market
  status: string
  start: string          // 对应 API 的 start_date
  end: string            // 对应 API 的 end_date
  total_budget: number
  description: string
}
```

Workspace 表单和页面表单用同一份字段定义和同一份 `toCreateProjectPayload()` 适配函数。

### 2.4 确认即审批

用户在 Workspace 表单里编辑完，点击「确认创建」就是 HITL approval decision，不需要再发一句自然语言确认。approve 时携带用户最终编辑的 `edited_arguments` 和 `argument_diff`。

---

## 3. 状态模型

### 3.1 WorkspaceProjection

```ts
interface WorkspaceProjection {
  id: string
  sessionId: string
  runId?: string
  surface:
    | 'project.list'
    | 'project.detail'
    | 'project.create'
    | 'project.delete'
    | 'campaign.list'
    | 'campaign.create'
    | 'campaign.status'
    | 'material.list'
  sourceToolName?: string
  sourceToolCallId?: string
  mode:
    | 'loading'
    | 'readonly'
    | 'editable'
    | 'review'
    | 'executing'
    | 'completed'
    | 'stale'
    | 'failed'
  payload: Record<string, unknown>
  approval?: {
    runId: string
    checkpointId: string
    decisionStatus: 'pending' | 'approved' | 'rejected'
  }
  updatedAt: number
}
```

查询类工具：`mode = 'readonly'`，无 `approval`。
高风险工具：`mode = 'review'`，带 `approval`。

### 3.2 WorkspaceApprovalDraft

```ts
interface WorkspaceApprovalDraft {
  id: string               // = checkpointId
  runId: string
  checkpointId: string
  toolName: string
  surface: string
  originalArguments: Record<string, unknown>
  editedArguments: Record<string, unknown>
  dirtyFields: string[]
  status: 'pending' | 'approved' | 'rejected' | 'executing' | 'completed'
  updatedAt: number
}
```

### 3.3 WorkspaceInteractionEvent

用户在 Workspace 的操作记录，用于下一轮 context：

```ts
interface WorkspaceInteractionEvent {
  id: string
  sessionId: string
  runId?: string
  type:
    | 'entity.selected'
    | 'draft.field_changed'
    | 'approval.confirmed'
    | 'approval.rejected'
  surface: string
  field?: string
  before?: unknown
  after?: unknown
  createdAt: number
}
```

---

## 4. 工具投影注册表

工具到 Workspace 的映射用一张 registry，不写 if else：

```ts
const toolProjectionRegistry = {
  list_projects: {
    surface: 'project.list',
    mode: 'readonly',
    component: ProjectCollectionView,
    resultToPayload: parseProjectsResult,
  },
  create_project: {
    surface: 'project.create',
    mode: 'review',
    component: WorkspaceProjectCreate,
    argsToForm: fromCreateProjectArgs,
    formToArgs: toCreateProjectPayload,
    requiresApproval: true,
  },
  // 后续扩展...
}
```

---

## 5. 完整流程（以 create_project 为例）

```text
1. 用户：帮我创建一个日本 RPG 买量项目
2. Agent 生成 create_project tool call
3. MCP require_approval 中断
4. agent-service 保存 RunState checkpoint
5. backend SSE 发 runtime.requires_action
6. 前端生成 WorkspaceApprovalDraft（originalArguments = Agent 参数）
7. Workspace 渲染 CreateProjectForm，初始值为 originalArguments
8. 用户改 budget 5000→8000，市场 JP→JP,KR
9. workspaceStore 记录 draft + interaction + diff
10. 用户点击「确认创建」
11. 前端调 resolveApproval：
    {
      decision: "approve",
      edited_arguments: { name, product, target_market, ... },  // 用户最终值
      argument_diff: [{ field: "total_budget", before: 5000, after: 8000 }, ...]
    }
12. backend 透传到 agent-service
13. agent-service 把 approved_arguments 存入 checkpoint metadata
14. agent-service 加载 RunState，重建 WorkspaceRunContext（含 approved_arguments_by_call_id）
15. state.approve(interruption)
16. Runner.run_streamed(agent, state, context=workspace_context)
17. MCP create_project 执行时：
    - 通过 tool_meta_resolver 拿到 run_id
    - 用 run_id 查 checkpoint store 的 approved_arguments
    - 用 approved_arguments 覆盖原始 arguments
    - 调 backend REST 创建项目
18. backend 写 system db，返回结果
19. side_effect entity_changed/project
20. Workspace 刷新 project.list
21. Agent 输出：已按你调整后的预算和市场创建项目
```

---

## 6. RunContext 结合

严格遵循 `notebooks/06-context/study_note.md` 的边界：

```text
context_snapshot / session_state.ui_snapshot = 持久状态源
BusinessContextBuilder = 业务现场摘要
WorkspaceRunContext = 本次 run 本地上下文
Dynamic instructions = LLM 可见 workspace 上下文
RunContextWrapper / ToolContext = 工具访问上下文
Session = SDK 原生对话历史
RunState = HITL 暂停/恢复状态
```

### 6.1 collectContextSnapshot 真实化

```ts
function collectContextSnapshot(): AgentContextSnapshot {
  return {
    route: route.fullPath,
    activePanel,
    activeProjectId,
    activeCampaignId,
    selectedEntities: workspaceStore.getSelectedEntities(sessionId),
    draftEdits: workspaceStore.getDraftSummaries(sessionId),
    pendingApprovals: workspaceStore.getPendingApprovalSummaries(sessionId),
    recentInteractions: workspaceStore.getRecentInteractionSummaries(sessionId, 10),
  }
}
```

### 6.2 WorkspaceRunContext 增强

```python
@dataclass
class WorkspaceRunContext:
    user_id: str
    session_id: str
    run_id: str
    auth_token: str | None
    business_context_summary: str
    ui_snapshot: dict
    session_state: dict
    task_type: str
    # 新增：用户在 Workspace 编辑后的审批参数
    approved_arguments_by_call_id: dict[str, dict] = field(default_factory=dict)
```

### 6.3 两种可见性

**给 LLM 看**（dynamic instructions）：

```text
# Workspace 审核结果
用户刚刚确认了 create_project 操作。
Agent 原始参数：name=日本RPG测试, total_budget=5000
用户最终参数：name=日本RPG Q3扩量, total_budget=8000, target_market=JP,KR
用户修改：预算 5000→8000，市场 JP→JP,KR
后续回复必须以用户最终参数为准。
```

**给工具用**（本地 context）：

```python
# MCP 工具执行前
approved = ctx.context.approved_arguments_by_call_id.get(call_id)
if approved:
    arguments = approved  # 覆盖原始 arguments
```

---

## 7. 参数覆盖实现

SDK `RunState.approve(item)` 只批准原始 interruption，不改 tool arguments。因此参数覆盖放在 MCP 工具层：

```text
SDK RunState approve 原始 interruption
  -> tool 真正执行前
  -> MCP 工具通过 meta 拿 run_id
  -> 用 run_id 查 checkpoint store 的 approved_arguments
  -> 用 approved_arguments 覆盖原始 arguments
  -> 调 backend REST
```

关键：MCP 工具函数能访问 checkpoint store（同进程模块），通过 `tool_meta_resolver` 注入的 `run_id` 关联。

---

## 8. 数据落点

### 8.1 agent.db runtime_checkpoints（已有表，扩展 metadata）

```json
{
  "interruptions": [...],
  "run_state": {...},
  "approved_arguments": { "call_xxx": {...} },
  "argument_diff": [...],
  "approved_by": "user_id",
  "approved_at": "..."
}
```

### 8.2 前端 workspaceStore（内存 + localStorage 缓存）

- `projectionsBySession`
- `approvalDraftsByCheckpoint`
- `selectedEntitiesBySession`
- `interactionsBySession`

---

## 9. 首版实现范围

第一阶段只做 project 链路，验证两个关键点：

1. **查询类工具无需审批，也能投影到 Workspace**：`list_projects` → `ProjectCollectionView`
2. **创建类工具复用页面表单，用户编辑后走 HITL，Agent 感知最终参数**：`create_project` → `CreateProjectForm` + 可编辑 approval

### 9.1 前端

- 新增 `workspaceStore`（projections + approvalDrafts + interactions + selectedEntities）
- 新增 `toolProjectionRegistry`
- 拆 `CreateProjectModal.vue` → `CreateProjectForm.vue` + modal 壳
- 新增 `WorkspaceProjectCreate.vue`（用 `CreateProjectForm` + 确认/拒绝按钮）
- 废弃 `ProjectListWorkspace.vue` 自绘卡片，改用 `ProjectCollectionView`
- `collectContextSnapshot()` 接入 workspaceStore 真实数据
- `resolveApproval()` 携带 `edited_arguments` + `argument_diff`

### 9.2 API

- `resolveAgentRunApproval()` 增加 `editedArguments` + `argumentDiff` 参数

### 9.3 backend

- `resolve_run_approval` 透传 `edited_arguments` + `argument_diff` 到 agent-service

### 9.4 agent-service

- `resume_checkpoint` 接收 `edited_arguments` + `argument_diff`
- 存入 checkpoint metadata
- resume 时注入 `WorkspaceRunContext.approved_arguments_by_call_id`
- MCP `create_project` 执行时读取 approved_arguments 覆盖

### 9.5 dynamic instructions

- resume 后的 instructions 注入「用户修改了什么」，让 Agent 后续回复对齐用户最终参数

---

## 10. 后续阶段

- Phase B：`project.detail` 投影 + selection 接入 context
- Phase C：`campaign.create` / `campaign.status` / `delete_project` / `delete_campaign` 可编辑审批
- Phase D：`material.list` / `campaign.list` 复用对应 CollectionView
- Phase E：side_effect 驱动 Workspace stale/refresh

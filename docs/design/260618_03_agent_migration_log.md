# 前端 Agent 对话组件迁移日志

> 迁移时间: 2026-06-18
> 源分支: `zhangtianzhu_260611`
> 目标分支: `feat/claude-agent-migration`

## 迁移文件清单

### 组件 (19 个 Vue 文件)

#### 核心组件 (9个)
- [x] `components/agent/ChatWindow.vue` - 对话窗口主容器
- [x] `components/agent/MessageView.vue` - 消息渲染器（32KB，最复杂）
- [x] `components/agent/ActivityMessageView.vue` - 工具调用活动卡片
- [x] `components/agent/ChatInput.vue` - 输入框组件
- [x] `components/agent/AgentShell.vue` - Agent 外壳容器
- [x] `components/agent/HITLDialog.vue` - 人机交互确认对话框
- [x] `components/agent/PlanView.vue` - 计划视图
- [x] `components/agent/TaskStatusPanel.vue` - 任务状态面板
- [x] `components/agent/ToolCallView.vue` - 工具调用视图

#### Timeline 组件 (4个)
- [x] `components/agent/timeline/TimelineBlockRenderer.vue` - Timeline 路由器
- [x] `components/agent/timeline/ToolActivityBlock.vue` - 工具活动块
- [x] `components/agent/timeline/ProjectListBlock.vue` - 项目列表块
- [x] `components/agent/timeline/PlanTimelineBlock.vue` - 计划块

#### Workspace 组件 (6个)
- [x] `components/agent/workspace/CampaignDraftWorkspace.vue` - 广告计划草稿
- [x] `components/agent/workspace/CreativeWorkspace.vue` - 创意素材工作区
- [x] `components/agent/workspace/EmbeddedTaskTimeline.vue` - 嵌入式任务时间线
- [x] `components/agent/workspace/LiveWorkspaceShell.vue` - 实时工作区外壳
- [x] `components/agent/workspace/ProjectListWorkspace.vue` - 项目列表工作区
- [x] `components/agent/workspace/ProjectWorkspaceDetail.vue` - 项目详情工作区

#### Layout 组件 (1个)
- [x] `components/layout/ChatPanel.vue` - 聊天面板

### Composables (2个)
- [x] `composables/useHomeAgentSession.ts` - 旧版 Agent 会话管理（32KB）
- [x] `composables/useAgUiAgent.ts` - 新版 AG-UI 客户端（4KB）

### API 层 (2个)
- [x] `api/agent.ts` - Agent API 接口定义（4.1KB）
- [x] `api/agui.ts` - AG-UI SSE 客户端（2.6KB）

### Store (1个)
- [x] `store/agent.ts` - Agent 状态管理（5.1KB）

### Types (1个)
- [x] `types/agui.ts` - AG-UI 类型定义（5.5KB）

## 迁移总计

- **Vue 组件**: 19 个
- **TypeScript 文件**: 6 个
- **总计**: 25 个文件
- **代码量**: 约 85KB

## 迁移方法

使用 `git show` 从源分支读取文件内容，无需切换分支：

```bash
git show zhangtianzhu_260611:path/to/file.vue > path/to/file.vue
```

## 注意事项

### ⚠️ 后端协议不兼容

**当前分支后端**: Claude Agent SDK + AG-UI 协议适配层  
**旧分支后端**: OpenAI SDK + 自定义事件流

迁移的前端代码**暂不可直接运行**，因为：

1. **端点路径变化**:
   - 旧: `/api/v1/agent/chat/sessions/{id}/stream`
   - 新: `/api/v1/copilotkit` (AG-UI 标准)

2. **事件格式不同**:
   - 旧: 自定义事件（runtime.started / message.updated / tool_call.* / CUSTOM）
   - 新: AG-UI 标准事件（RunStarted / TextMessageContent / ActionExecution* / StateSnapshot）

3. **数据结构差异**:
   - 旧: AgentMessage 含 toolCallId / activityType
   - 新: 需对齐 AG-UI Message 格式

### 下一步工作

#### 方案 A: 适配前端到新协议（推荐）
1. 修改 `api/agui.ts` 端点为 `/api/v1/copilotkit`
2. 修改 `useHomeAgentSession.ts` 事件处理逻辑：
   - `runtime.started` → `RunStarted`
   - `message.updated` → `TextMessageContent`
   - `tool_call.*` → `ActionExecution*` + `ActivitySnapshot`
3. 测试前端组件与新后端联调

#### 方案 B: 保留旧协议兼容层（临时方案）
1. 在 aniforce-agent 添加旧协议适配端点
2. 将 Claude SDK 消息流转为旧格式
3. 前端暂时无需改动

#### 方案 C: 完全重构为 @ag-ui/client（长期方案）
1. 移除 `useHomeAgentSession.ts`
2. 只使用 `useAgUiAgent.ts`（基于 HttpAgent）
3. 简化状态管理，依赖 AG-UI 客户端

## 依赖检查

前端使用的外部库需确认当前分支是否已安装：

```json
{
  "markdown-it": "^13.x",
  "@ag-ui/client": "^x.x.x",
  "@ag-ui/core": "^x.x.x"
}
```

检查方法：
```bash
cd frontend/packages/main-app
cat package.json | grep -E "markdown-it|@ag-ui"
```

## 验证步骤（暂不执行）

```bash
# 1. 安装依赖（如需）
cd frontend/packages/main-app
pnpm install

# 2. 类型检查
pnpm type-check

# 3. 构建检查
pnpm build

# 4. 本地开发服务器
pnpm dev
```

## 参考文档

- [前端 Agent UI 组件分析](./frontend-agent-ui-analysis.md)
- [ANIFORCE 关键技术结论](../AGENTS.md)
- [AG-UI 协议与架构设计](../AGENTS.md#ag-ui-协议与架构设计)

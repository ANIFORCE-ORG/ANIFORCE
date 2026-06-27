# ANIFORCE 前端现状全面分析报告

## 📊 项目结构概览

```
frontend/packages/main-app/
├── src/
│   ├── components/
│   │   ├── agent/              # Agent 相关组件（5个文件，1217行）
│   │   │   ├── AgentShell.vue         # Agent 外壳（198行）
│   │   │   ├── ChatInput.vue          # 聊天输入框（207行）
│   │   │   ├── ChatWindow.vue         # 聊天窗口（135行）
│   │   │   ├── MessageView.vue        # 消息展示（327行）
│   │   │   └── TaskStatusPanel.vue    # 任务状态面板（350行）
│   │   ├── layout/
│   │   │   └── ChatPanel.vue          # 右侧对话面板（主入口）
│   │   ├── campaigns/          # 广告计划组件
│   │   ├── projects/           # 项目组件
│   │   └── ...
│   ├── services/
│   │   └── agentService.ts    # Agent API 服务（核心）
│   ├── config/
│   │   └── agent.ts           # Agent 配置
│   ├── composables/
│   │   ├── useAgentSession.ts
│   │   └── useHomeAgentSession.ts
│   └── api/
│       └── agent.ts
```

---

## 🔍 核心组件分析

### 1. ChatPanel.vue（主入口组件）

**当前功能**：
- ✅ 基础对话界面（折叠/展开）
- ✅ 消息列表展示
- ✅ 流式/非流式对话切换
- ✅ Session 管理
- ✅ 快捷提示词
- ✅ 消息历史加载

**当前架构**：
```typescript
interface Message {
  role: 'user' | 'assistant' | 'system'
  author: string
  time: string
  content: string
  isStreaming?: boolean
}
```

**当前流程**：
1. 用户输入消息
2. 调用 `agentService.chatStream()` 或 `agentService.chat()`
3. 接收 SSE 事件流
4. 解析事件：`message_delta` / `message.updated` / `message_completed`
5. 更新 UI

**问题/限制**：
- ❌ 只处理文本消息（`message_delta`）
- ❌ 不支持 Plan/Todo 事件
- ❌ 不支持 Tool 调用可视化
- ❌ 不支持 HITL 确认
- ❌ 没有 Shared State 概念
- ❌ 消息格式简单（只有 content 字符串）

---

### 2. agentService.ts（API 层）

**当前功能**：
- ✅ Session CRUD
- ✅ SSE 流式对话
- ✅ 事件解析（`parseSseEvent`）
- ✅ 错误处理

**当前事件处理**：
```typescript
// 只处理 3 种事件
- message_delta / message.updated  → 流式内容
- message_completed / message.completed → 完成
- runtime.error / error → 错误
```

**问题/限制**：
- ❌ 不支持 AG-UI 协议事件（TEXT_MESSAGE_*, TOOL_CALL_*, CUSTOM）
- ❌ 事件处理逻辑硬编码
- ❌ 没有事件类型枚举
- ❌ 返回格式单一（只有 text）

---

### 3. agent 目录下的其他组件

**AgentShell.vue（198行）**：
- 目的：Agent 工作区外壳
- 状态：未使用（ChatPanel 是主入口）

**ChatInput.vue（207行）**：
- 目的：独立的输入组件
- 状态：未使用（ChatPanel 内嵌了输入框）

**ChatWindow.vue（135行）**：
- 目的：独立的聊天窗口
- 状态：未使用（ChatPanel 包含了聊天功能）

**MessageView.vue（327行）**：
- 目的：消息渲染组件
- 状态：未使用（ChatPanel 直接渲染消息）

**TaskStatusPanel.vue（350行）**：
- 目的：任务状态展示
- 状态：未使用

**结论**：这些组件是早期设计，但实际使用的是 **ChatPanel.vue**

---

## 🎯 当前架构特点

### 优点 ✅

1. **简洁明了**：
   - 单一入口（ChatPanel.vue）
   - 代码量适中（~200 行）
   - 易于理解和维护

2. **基础功能完善**：
   - 流式对话体验好
   - Session 管理完整
   - 错误处理到位

3. **用户体验**：
   - 折叠/展开功能
   - 快捷提示词
   - 流式输出动画

4. **代码质量**：
   - TypeScript 类型完整
   - Vue 3 Composition API
   - 响应式设计

### 限制 ❌

1. **事件处理简单**：
   - 只处理 3 种事件类型
   - 没有 AG-UI 协议支持
   - 无法展示 Plan/Todo/Tool Call

2. **UI 表达有限**：
   - 只能显示纯文本
   - 没有 Markdown 渲染
   - 没有富媒体支持
   - 没有可交互元素（按钮、表单）

3. **交互单向**：
   - 只能发送文本
   - 没有 HITL 确认机制
   - 没有用户操作回传

4. **状态管理缺失**：
   - 没有 Shared State
   - 没有上下文感知
   - 没有 Plan/Todo 状态追踪

5. **可扩展性受限**：
   - 组件耦合度高
   - 事件处理硬编码
   - 难以添加新功能

---

## 🔄 与 AG-UI 协议的差距

### 当前支持的事件

| 事件类型 | 当前处理 | AG-UI 对应 |
|---------|---------|-----------|
| message_delta | ✅ 流式内容 | TEXT_MESSAGE_CONTENT |
| message.updated | ✅ 流式内容 | TEXT_MESSAGE_CONTENT |
| message_completed | ✅ 完成 | TEXT_MESSAGE_END |
| runtime.error | ✅ 错误 | - |

### 缺失的 AG-UI 事件

| AG-UI 事件 | 用途 | 当前状态 |
|-----------|------|---------|
| TEXT_MESSAGE_START | 消息开始 | ❌ 未处理 |
| TOOL_CALL_START | 工具调用开始 | ❌ 未处理 |
| TOOL_CALL_ARGS | 工具参数 | ❌ 未处理 |
| TOOL_CALL_END | 工具调用结束 | ❌ 未处理 |
| STATE_SNAPSHOT | 共享状态 | ❌ 未处理 |
| CUSTOM (plan.created) | 计划创建 | ❌ 未处理 |
| CUSTOM (todo.started) | Todo 开始 | ❌ 未处理 |
| CUSTOM (hitl.*) | HITL 确认 | ❌ 未处理 |

---

## 📋 改造策略建议

### 策略 A：渐进式改造（推荐）✅

**原则**：保留现有 ChatPanel.vue，逐步增强

**步骤**：

1. **Phase 1：扩展事件处理（1-2 小时）**
   - 在 `agentService.ts` 中添加 AG-UI 事件类型
   - 扩展 `streamChat` 方法，支持更多事件
   - ChatPanel 增加事件分发逻辑

2. **Phase 2：Plan/Todo 可视化（2-3 小时）**
   - 消息类型扩展（添加 plan / tool_call 类型）
   - 添加 Plan 展示组件（折叠列表）
   - 添加 Todo 进度条
   - 添加 Tool Call 徽章

3. **Phase 3：HITL 确认（1 小时）**
   - 添加确认对话框组件
   - 处理 HITL 事件
   - 实现确认/取消回调

4. **Phase 4：Shared State（可选，1 小时）**
   - 添加 Composable：`useSharedState`
   - 同步前后端状态
   - 上下文感知提示

**优点**：
- ✅ 不破坏现有功能
- ✅ 逐步验证效果
- ✅ 风险可控
- ✅ 可以边开发边使用

**缺点**：
- ⚠️ 代码可能变复杂
- ⚠️ 需要兼容旧逻辑

---

### 策略 B：全新组件（不推荐）❌

**原则**：创建新的 AGUIChatWindow.vue

**优点**：
- ✅ 架构清晰
- ✅ 充分利用 AG-UI 协议

**缺点**：
- ❌ 需要重写大量代码
- ❌ 两套组件并存，维护成本高
- ❌ 用户体验切换不平滑
- ❌ 时间成本高（5-7 小时）

---

## 🎯 推荐方案：渐进式改造

### Phase 1：扩展事件处理

**目标**：让 agentService 支持 AG-UI 协议

**修改文件**：
1. `src/types/agent.ts`（新建）
   - 定义 AG-UI 事件类型
   - 定义消息类型

2. `src/services/agentService.ts`
   - 扩展 `AgentStreamEvent` 类型
   - 添加事件处理逻辑

**代码量**：~100 行

---

### Phase 2：Plan/Todo 可视化

**目标**：ChatPanel 能展示 Plan 和 Todo

**修改文件**：
1. `src/components/layout/ChatPanel.vue`
   - 扩展 Message 接口
   - 添加 Plan 渲染逻辑
   - 添加 Todo 列表渲染

**新增组件**：
1. `src/components/agent/PlanView.vue`（可选）
   - 计划展示组件
   - 折叠/展开
   - 进度指示

**代码量**：~200 行

---

### Phase 3：HITL 确认

**目标**：支持用户确认操作

**新增组件**：
1. `src/components/agent/HITLDialog.vue`
   - 确认对话框
   - 风险等级展示
   - 确认/取消按钮

**修改文件**：
1. `src/components/layout/ChatPanel.vue`
   - 处理 HITL 事件
   - 显示对话框
   - 回传确认结果

**代码量**：~150 行

---

## 📊 工作量评估

| 阶段 | 工作量 | 优先级 | 依赖 |
|------|--------|--------|------|
| Phase 1: 事件处理 | 1-2h | 🔴 高 | 无 |
| Phase 2: Plan/Todo | 2-3h | 🔴 高 | Phase 1 |
| Phase 3: HITL | 1h | 🟡 中 | Phase 1 |
| Phase 4: Shared State | 1h | 🟢 低 | Phase 1 |

**总计**：5-7 小时（完整实现）

---

## 💡 关键决策点

### 1. 是否重用现有组件？

**推荐**：✅ 重用并增强 ChatPanel.vue

**理由**：
- 当前 ChatPanel 架构清晰
- 用户已习惯当前界面
- 代码量适中，易于扩展
- 风险可控

### 2. 消息格式如何扩展？

**当前**：
```typescript
interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
}
```

**推荐**：
```typescript
interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  type?: 'text' | 'plan' | 'tool_call' | 'hitl'
  metadata?: {
    plan?: ExecutionPlan
    tool?: ToolCall
    hitl?: HITLRequest
  }
}
```

### 3. 是否使用 Markdown 渲染？

**推荐**：✅ 是

**理由**：
- Agent 输出可能包含格式化内容
- Plan/Todo 需要结构化展示
- 用户体验更好

**库选择**：
- `marked`（轻量，5KB）
- `markdown-it`（功能强大，20KB）

---

## 🚀 实施建议

### 第一步：创建类型定义

```bash
# 创建新文件
frontend/packages/main-app/src/types/agui.ts
```

### 第二步：扩展 agentService

```bash
# 修改文件
frontend/packages/main-app/src/services/agentService.ts
```

### 第三步：增强 ChatPanel

```bash
# 修改文件
frontend/packages/main-app/src/components/layout/ChatPanel.vue
```

### 第四步：测试验证

```bash
# 使用真实 Agent 测试
- 简单查询 → ReAct 模式
- 复杂分析 → Plan-Execute 模式
- 删除操作 → HITL 确认
```

---

## 📝 总结

### 当前状态
- ✅ 基础对话功能完善
- ✅ 代码质量高
- ❌ 缺少 AG-UI 协议支持
- ❌ 缺少高级交互

### 改造方向
- ✅ 渐进式增强（不破坏现有功能）
- ✅ 优先支持 Plan/Todo 可视化
- ✅ 后续添加 HITL 和 Shared State

### 预期效果
- 🎯 完全支持 AG-UI 协议
- 🎯 Plan-Execute 流程可视化
- 🎯 Tool 调用透明化
- 🎯 HITL 交互流畅

### 时间成本
- Phase 1-2（核心功能）：3-5 小时
- Phase 3-4（完整功能）：5-7 小时

---

**推荐从 Phase 1 开始，每个 Phase 完成后验证效果，再决定是否继续！**

# 对话流与 Workspace 交互设计 - 简化方案

**日期**: 2026-06-14  
**状态**: ✅ 设计完成，待实施  
**优先级**: P0（核心体验改造）

---

## 背景与问题

### 当前架构
- **前端**: 三栏布局（左导航 + 中对话流 + 右 Workspace）
- **协议**: AG-UI 事件流（SSE）
- **消息类型**: user / assistant / activity（已内联到消息流）

### 当前痛点
1. **信息重复**：工具结果在对话流和 Workspace 都展示，感觉冗余
2. **视线跳转**：用户需要在对话区和 Workspace 之间反复切换
3. **状态不一致**：Activity 卡片和 Workspace Timeline 表达同一件事但样式不同
4. **归属不清**：不清楚哪些结果应该在对话流，哪些应该在 Workspace
5. **视觉不统一**：ActivityMessageView 使用鲜艳渐变背景，与主站扁平风格不符

---

## 设计目标

1. **对话流 + Workspace 自动同步**：工具结果同时出现，自然分工
2. **视觉统一**：状态卡符合 ANIFORCE 扁平设计系统（主色 `#137fec`，圆角 1rem）
3. **交互清晰**：对话流轻量只读，Workspace 完整可交互
4. **无需复杂路由**：简单规则，易维护

---

## 核心设计原则

### 信息分配规则（极简版）

**对话流**：
- Activity 进度卡片（工具调用状态）
- AI 文本摘要
- 工具结果预览（前 3 条 + "查看完整"链接）

**Workspace**：
- 完整业务对象列表/详情/编辑器
- 自动同步最新工具结果
- 支持深度交互（点击、编辑、提交）

**示例流程**：
```
用户："现在有哪些项目？"
  ↓
对话流：
  [ActivityCard] ● 查询项目列表完成 (2.3s)
  [AssistantMessage] "您目前有 11 个项目，已同步到 Workspace →
    • 260614 - ¥50,000
    • Candy Blast - ¥50,000
    • RPG Adventure - ¥80,000
    [完整列表请在 Workspace 中查看 →]"
  ↓
Workspace：
  [Header] 项目管理 (11 个项目)
  [Body] [ProjectCardDetailed x 11 - 可滚动、可点击]
```

---

## 视觉层设计

### 1. ActivityMessageView 重构

**设计规范对齐**：
- 背景：`#f8fafc`（浅灰，与 ProjectCardDetailed 统一）
- 边框：`#e2e8f0`（细边框）
- 圆角：`1rem`（16px，统一）
- hover：边框变色 `rgba(19, 127, 236, 0.3)`（主色半透明）

**核心改动**：
- ❌ 移除鲜艳渐变背景（`bg-blue-50/emerald-50/red-50`）
- ❌ 移除左侧彩色指示条
- ❌ 移除 pulse-subtle 卡片动画、3 点跳动
- ✅ 状态用小圆点（8px）表达
- ✅ 只有圆点有柔和脉动动画
- ✅ 扁平卡片，静态 hover

**布局结构**：
```
[8px 圆点] [工具标题] [工具名称(mono)] [耗时]
```

### 2. AssistantMessage 元信息分层

**当前问题**：usage 统计和消息正文视觉边界不清

**改造方案**：
```
[消息正文]
────────────── (浅色分隔线)
model-badge | usage-text (半透明) | copy-button
```

**样式特征**：
- 分隔线：`border-top: 1px solid #f1f5f9`
- usage 文字：`font-size: 11px; color: #94a3b8`（半透明灰）
- 右对齐：`justify-content: space-between`

### 3. 工具结果预览组件（新增）

**组件名**：`ToolResultSummary.vue`

**用途**：在对话流中显示工具结果的轻量预览

**布局**：
```
📋 项目列表 (11)
────────────────────
• 260614           ¥50,000
• Candy Blast      ¥50,000
• RPG Adventure    ¥80,000
────────────────────
[完整列表请在 Workspace 中查看 →]
```

**样式**：
- 背景：`#fafbfc`
- 边框：`#e9ecef`
- 圆角：`1rem`
- 每行预览：白色背景 `8px` 圆角

---

## 交互流程

### 场景 1：轻量查询

```
1. 用户输入："现在有哪些项目？"
2. [对话流] ActivityCard：● 正在查询项目列表
3. [对话流] ActivityCard：● 查询完成 (2.3s)
4. [对话流] AssistantMessage：
   - 文本："您目前有 11 个项目，已同步到 Workspace →"
   - ToolResultSummary：前 3 条预览 + 查看完整链接
5. [Workspace] 自动显示 ProjectCardDetailed x 11
```

### 场景 2：创建项目草稿

```
1. 用户输入："帮我创建一个新的投放项目"
2. [对话流] AI 询问信息
3. 用户补充信息
4. [对话流] ActivityCard：● 正在创建项目草稿
5. [对话流] AssistantMessage："项目草稿已创建，请在 Workspace 中完善详情 →"
6. [Workspace] 自动切换到项目编辑器（表单）
```

---

## 技术实施

### 1. ActivityMessageView.vue 改造

**文件位置**：
`frontend/packages/main-app/src/components/agent/ActivityMessageView.vue`

**关键改动**：
```vue
<template>
  <div class="activity-card">
    <div class="activity-content">
      <!-- 状态圆点（8px） -->
      <div class="status-dot" :class="statusClass"></div>
      
      <!-- 工具信息 -->
      <div class="flex-1 min-w-0">
        <span class="activity-title">{{ content.title }}</span>
        <span class="activity-tool">{{ content.toolName }}</span>
      </div>
      
      <!-- 耗时 -->
      <span class="activity-duration">{{ duration }}</span>
    </div>
  </div>
</template>

<style scoped>
.activity-card {
  padding: 12px 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 1rem;
  transition: border-color 0.16s ease;
  margin: 8px 0;
}

.activity-card:hover {
  border-color: rgba(19, 127, 236, 0.3);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.running {
  background: #137fec;
  animation: pulse-dot 2s ease-in-out infinite;
}

.status-dot.completed {
  background: #10b981;
}

.status-dot.error {
  background: #ef4444;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
```

### 2. MessageView.vue 元信息分层

**文件位置**：
`frontend/packages/main-app/src/components/agent/MessageView.vue`

**改动位置**：`.assistant-footer` 样式块

**关键改动**：
```css
.assistant-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

.usage-text {
  font-size: 11px;
  color: #94a3b8;
}
```

### 3. ToolResultSummary.vue（新增）

**文件位置**（新建）：
`frontend/packages/main-app/src/components/agent/ToolResultSummary.vue`

**功能**：
- 接收工具结果数据
- 显示前 3 条预览
- 提供"查看完整"链接（滚动到 Workspace）

### 4. Workspace 自动同步

**文件位置**：
`frontend/packages/main-app/src/components/agent/workspace/LiveWorkspaceShell.vue`

**当前逻辑**：已有 `toolResults` 监听和自动渲染

**无需改动**：Workspace 已经在监听 `workspaceToolResults`，工具完成后自动显示

---

## 实施计划

### Phase 1：视觉改造（2-3 小时）
- [ ] 重构 ActivityMessageView.vue（移除渐变背景、彩色指示条、重动画）
- [ ] 改造 MessageView.vue 的 assistant-footer（添加分隔线、调整 usage 样式）
- [ ] 验证视觉一致性（对比 ProjectCardDetailed）

### Phase 2：工具结果预览（2-3 小时）
- [ ] 创建 ToolResultSummary.vue 组件
- [ ] 在 MessageView.vue 中集成（assistant 消息后自动渲染）
- [ ] 实现"查看完整"链接（scrollIntoView Workspace）

### Phase 3：测试与优化（1-2 小时）
- [ ] 完整流程测试（查询项目、创建项目、查询广告计划）
- [ ] Dark mode 适配
- [ ] 响应式适配（移动端）

**总计**：5-8 小时

---

## 验收标准

### 视觉层
- ✅ ActivityCard 背景为浅灰 `#f8fafc`，边框 `#e2e8f0`
- ✅ 状态用 8px 小圆点，只有圆点有脉动动画
- ✅ hover 只变边框色，不变背景
- ✅ assistant-footer 有浅色分隔线，usage 文字半透明右对齐

### 交互层
- ✅ 工具调用完成后，对话流显示 Activity 完成状态
- ✅ AI 回复中包含工具结果预览（前 3 条）
- ✅ Workspace 自动显示完整工具结果
- ✅ 点击"查看完整"链接，页面滚动到 Workspace

### 兼容性
- ✅ Dark mode 正常显示
- ✅ 移动端布局不错乱（Workspace 隐藏时）

---

## 未来扩展

### 短期（1-2 周内）
- Activity 类型扩展（STATE_CHANGE / CONFIRMATION / PROGRESS）
- 工具结果结构化卡片（ProjectListCard / DataTableCard）

### 中期（1 个月内）
- Workspace 多 Tab 支持（Projects / Campaigns / Materials）
- 对话流消息编辑/重新生成

### 长期（2-3 个月）
- 消息分支（多分支对话）
- 导出对话（Markdown / PDF）

---

**设计者**: Kiro (Claude Code)  
**协作者**: 张天柱  
**参考资料**: CopilotKit showcase, ANIFORCE 设计系统

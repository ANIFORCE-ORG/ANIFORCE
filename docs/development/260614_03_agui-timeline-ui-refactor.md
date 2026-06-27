# AG-UI 时间线交互 UI 全面重构

**日期**: 2026-06-14  
**状态**: ✅ 完成核心改造，待优化视觉层次

---

## 今日完成

### 1. AG-UI 协议验证（已完成 ✅）
- ✅ 后端 `/api/v1/copilotkit` 端点正常工作
- ✅ SSE 事件流输出符合 AG-UI 规范
- ✅ 前端接收到完整事件序列
- ✅ ActivitySnapshot / ToolCallResult / StateSnapshot 全部到达

### 2. 消息流架构重构（已完成 ✅）
**核心改造：Activity 内联到消息流**

#### 旧架构问题
```
user message
assistant message
[TimelineBlock 堆在下面]  ← 视觉上割裂
[TimelineBlock]
[TimelineBlock]
```

#### 新架构
```
user message
activity message (tool running)    ← 内联显示
activity message (tool completed)
assistant message
```

#### 实现细节
- `store.upsertActivityMessage()` - Activity 直接插入 messages 数组
- `visibleMessages` 过滤包含 `role: 'activity'`
- 移除 `TimelineBlockRenderer` 依赖
- 移除 `orphanTimelineBlocks` / `streamingTimelineBlocks` 复杂逻辑

---

### 3. 新增 ActivityMessageView 组件（已完成 ✅）

**设计目标：呼吸感 + 高级感 + 状态清晰**

#### 视觉特性
- **左侧彩色指示条**：蓝色(running) / 绿色(completed) / 红色(error)
- **状态图标**：pending / check_circle / error
- **动画效果**：
  - running: pulse 动画 + 3点跳动
  - completed/error: 静态展示
- **hover 效果**：阴影加深 + 微提升

#### 状态映射
```typescript
running    → 蓝色 + 旋转图标 + 跳动点
completed  → 绿色 + ✓ 图标
error      → 红色 + ✗ 图标
```

---

### 4. MessageView 全面优化（已完成 ✅）

#### 用户消息
- 渐变背景：`linear-gradient(135deg, #eff6ff, #e0f2fe)`
- 圆角：16px → 18px
- 多层阴影：轻阴影 + hover 加深
- hover 效果：`translateY(-1px)`

#### 助手消息
- 移除左侧 border（旧设计遗留）
- 增加间距：22px → 32px
- fadeInUp 进入动画（0.4s cubic-bezier）
- 字号优化：14px → 15px，行高 1.7 → 1.75

#### 代码块 / 表格
- 圆角：6px → 10px
- 多层阴影：增强层次感
- 表格：overflow hidden + 圆角

---

### 5. 输入输出统计修复（已完成 ✅）

**问题：** usage 数据丢失

**原因：** AG-UI adapter 的 `TextMessageEnd` 没传递 usage

**修复：**
```python
# backend/app/agent_platform/adapters/agui_adapter.py
if event_type == "message.completed":
    usage = payload.get("usage")  # 提取 usage
    return [TextMessageEndEvent(message_id=mid, usage=usage)]

# backend/app/agent_platform/adapters/agui_events.py
class TextMessageEndEvent:
    def __init__(self, message_id: str, usage: dict | None = None):
        self.usage = usage  # 新增 usage 字段
```

**前端处理：**
```typescript
if (event.event === 'TextMessageEnd') {
  const { usage } = event.data
  if (usage) {
    assistant.usage = usage  // 保存到消息对象
  }
}
```

**显示效果：**
```
5,043 in  465 out  2,560 cache  $0.0234
```

---

## 视觉对比

### 改造前
- 消息堆叠紧凑（16-22px 间距）
- TimelineBlock 与消息割裂
- 无动画过渡
- 单层阴影
- 工具状态文字化

### 改造后
- 呼吸感间距（28-32px）
- Activity 内联在消息流
- fadeInUp + pulse 动画
- 多层渐变阴影
- 工具状态卡片化（彩色指示条）

---

## 当前问题

### ⚠️ 视觉层次混乱
**用户反馈：** "输入输出统计和当前 AI 回复的消息视觉上完全无法区分"

**现状：**
```
┌─ assistant message ──────────┐
│ 您目前有 11 个项目：          │
│ | 项目 | 预算 | 状态 |         │
│ ...                           │
│                               │
│ 5,043 in  465 out  $0.0234   │  ← 统计信息混在内容里
└───────────────────────────────┘
```

**问题分析：**
- `assistant-footer` 和消息内容视觉边界不清晰
- 统计信息字号/颜色与正文相近
- 缺少分隔线或背景区分

---

## 下一步开发计划

### 🎯 高优先级

#### 1. 优化消息元信息显示层次
**目标：** 明确区分消息内容 vs 元信息（usage / model / 时间）

**方案选项：**

**A. 元信息右下角半透明（最快）**
```
┌─ assistant message ──────────────┐
│ 您目前有 11 个项目：              │
│ ...                               │
│                                   │
│            [Copy] 12k in 850 out │  ← 右对齐，半透明
└───────────────────────────────────┘
```
- 实现简单，只改 CSS
- 视觉层次清晰

**B. 独立元信息卡片（最清晰）**
```
┌─ assistant message ──────────────┐
│ 您目前有 11 个项目：              │
│ ...                               │
└───────────────────────────────────┘
┌─ meta ──────────────────────────┐  ← 独立浅色背景
│ 📊 gpt-5.4  12k in  850 out  $0.02 │
└───────────────────────────────────┘
```
- 最清晰，但增加视觉重量

**C. 折叠到 model 行（最简洁）**
```
gpt-5.4  ↓ 850  12.5 t/s  [详情 ▾]  ← 点击展开
┌─ assistant message ──────────────┐
│ 您目前有 11 个项目：              │
└───────────────────────────────────┘
```
- 最节省空间
- 需要交互逻辑

**推荐：方案 A（快速修复）→ 后续优化为方案 B**

---

#### 2. Activity 类型扩展
**当前：** 只支持 `TOOL_CALL`

**扩展目标：**
- `STATE_CHANGE` - 状态变化通知
- `CONFIRMATION` - 用户确认对话框
- `PROGRESS` - 进度条更新
- `SYSTEM_EVENT` - 系统通知

**实现路径：**
```typescript
// ActivityMessageView.vue 支持多种 activityType
<StateChangeCard v-if="activityType === 'STATE_CHANGE'" />
<ConfirmationDialog v-if="activityType === 'CONFIRMATION'" />
<ProgressBar v-if="activityType === 'PROGRESS'" />
```

---

#### 3. 工具结果卡片优化
**当前：** ToolCallResult 只显示纯文本

**目标：** 结构化结果卡片
```
┌─ 项目列表（11 个）─────────────┐
│ ┌────────────────────────────┐ │
│ │ 260614        ¥50,000      │ │
│ │ Candy Blast   ¥50,000      │ │
│ │ ...                        │ │
│ └────────────────────────────┘ │
│ [在 Workspace 中查看详情 →]    │
└────────────────────────────────┘
```

**实现：**
- 后端 `ToolPresentation.extract_result()` 返回结构化数据
- 前端根据 tool 类型渲染不同卡片（ProjectListCard / DataTableCard）

---

### 🔧 中优先级

#### 4. 消息流滚动优化
- 新消息出现时平滑滚动到底部
- Activity 卡片出现时不要跳动
- 支持"滚动到顶部加载历史"

#### 5. Dark Mode 优化
- Activity 卡片深色模式配色
- 渐变背景适配暗色
- 阴影在暗色下的层次调整

#### 6. 性能优化
- 长对话时虚拟滚动（messages > 100）
- Activity 动画节流（requestAnimationFrame）

---

### 📋 低优先级（未来）

#### 7. 消息编辑 / 重新生成
- 点击用户消息可编辑
- 点击助手消息可重新生成

#### 8. 消息分支
- 支持多分支对话（类似 ChatGPT）

#### 9. 导出对话
- 导出为 Markdown / PDF

---

## 技术债务

### 1. TimelineBlockRenderer 残留
- Home.vue 已移除引用
- 但组件文件还在，未来可删除

### 2. timelineBySession 冗余
- Store 中 `timelineBySession` 现在只用于 executionTools 状态
- 可简化为 `executionToolsBySession`

### 3. 类型定义混乱
- `AgentMessage.content` 类型是 `string | AgentContentBlock[] | ActivityContent`
- 应该拆分为不同接口（UserMessage / AssistantMessage / ActivityMessage）

---

## 总结

### ✅ 今日成果
- AG-UI 协议全面接入
- 消息流架构重构完成
- Activity 内联显示实现
- UI 呼吸感 + 高级感提升
- 输入输出统计修复

### ⚠️ 待解决
- 消息元信息视觉层次混乱
- Activity 类型单一
- 工具结果卡片简陋

### 🎯 下一步
1. **快速修复**：优化 assistant-footer 视觉层次（方案 A）
2. **功能扩展**：Activity 类型扩展（STATE_CHANGE / CONFIRMATION）
3. **体验优化**：工具结果结构化卡片

---

**开发者**: Kiro (Claude Code)  
**协作者**: 张天柱  
**代码提交**: e384ac6, 56382a0

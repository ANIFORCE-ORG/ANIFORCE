# ANIFORCE Agent 对话 UI 组件分析

> 基于 `zhangtianzhu_260611` 分支的前端实现

## 核心组件结构

### 1. ChatWindow.vue - 对话窗口主容器

**职责**：
- 消息列表渲染（用户消息 + assistant 消息）
- 空状态展示（Hero title + ChatInput）
- Timeline blocks 渲染（工具调用、计划等）
- 自动滚动到底部

**关键特性**：
- 响应式设计，最大宽度 820px
- 流式状态指示器（"Waiting for model..." / "Running tools..."）
- 支持重试提示和错误展示

**样式亮点**：
- 干净的渐变背景
- 平滑的滚动动画
- 状态脉动动画（pulse）

---

### 2. MessageView.vue - 消息渲染器

**职责**：
- 渲染用户消息（气泡样式）
- 渲染 assistant 消息（Markdown + 代码块）
- 渲染 activity 消息（工具调用卡片）
- 支持图片附件、thinking block、tool call block

**关键特性**：

#### 用户消息样式
```
- 渐变蓝色气泡（#eff6ff → #e0f2fe）
- 圆角 18px，右对齐
- 悬停阴影加深 + 轻微上移
- 支持图片预览（最大 240px）
```

#### Assistant 消息样式
```
- 透明背景，左对齐
- Markdown 渲染（标题、列表、表格、代码）
- 代码块带语言标签 + copy 按钮
- 流式状态显示（token/s 速度）
- 底部元数据栏（模型名、token 用量、成本）
```

#### 工具调用折叠块
```
- 可展开/折叠
- 显示工具名、参数预览、状态（running/done/error）
- 参数和结果用 pre 块展示
- 错误状态红色高亮
```

**样式亮点**：
- 用户消息气泡有渐变 + 阴影 + 圆角，视觉精致
- Assistant 消息 fadeInUp 进场动画
- 代码块语法高亮区域独立，带 copy 按钮
- 悬停时显示 copy 按钮（opacity 过渡）

---

### 3. ActivityMessageView.vue - 工具调用活动卡片

**职责**：
- 渲染单个工具调用的实时状态
- 显示状态点（running 脉动 / completed 绿色 / error 红色）
- 显示工具名称和标题

**样式特点**：
```css
.activity-card {
  - 浅灰背景 (#f8fafc)
  - 边框 1px solid #e2e8f0
  - 圆角 1rem
  - 悬停时边框变蓝色
}

.status-dot {
  - 8px 圆点
  - running: 蓝色 + 脉动动画
  - completed: 绿色静态
  - error: 红色静态
}
```

**动画**：
- `pulse-dot`: 柔和的透明度变化（1 → 0.5 → 1）

---

### 4. ChatInput.vue - 输入框组件

**职责**：
- 多行文本输入（自动高度调整）
- 图片附件上传 + 预览
- 模型选择下拉菜单
- 发送 / 停止按钮切换

**关键特性**：

#### 输入框样式
```
- 最大宽度 820px
- 圆角 18px
- 白色背景 + 柔和阴影
- 流式状态时边框变黄色
```

#### 按钮设计
```
Send 按钮:
  - 蓝色背景 (#137fec)
  - 白色文字 + 箭头图标
  - 禁用时变灰

Stop 按钮:
  - 浅红色背景
  - 红色边框 + 红色文字
  - 方形停止图标
```

#### Toolbar
```
- 图片附件按钮（图标按钮）
- 模型选择按钮（chip 样式）
- 下拉菜单（固定定位，阴影）
```

**样式亮点**：
- 输入框有立体阴影（box-shadow 两层）
- Chip 按钮圆角 999px（完全圆润）
- 图片预览带删除按钮（右上角 × 按钮）

---

### 5. Timeline 组件系列

#### TimelineBlockRenderer.vue
- 路由器组件，根据 block.type 分发到具体渲染器

#### ToolActivityBlock.vue
**样式特点**：
```css
.tool-indicator {
  - 毛玻璃效果（backdrop-filter: blur(8px)）
  - 浅色背景 + 半透明
  - 圆角 12px
  - 悬停时阴影加深
  - slide-in 进场动画（从右向左）
}

.status-dot {
  - 20px 圆点
  - running: 蓝色背景 + 脉动光环
  - completed: 绿色 + check icon（check-pop 动画）
  - error: 红色 + 感叹号 icon
}
```

**动画**：
```
- slide-in: 从右侧滑入（透明度 0→1，位移 12px→0）
- pulse: 光环脉动（scale 1→1.4，opacity 1→0.6）
- check-pop: 对勾图标弹出（scale 0.6→1.2→1）
```

---

## 设计语言总结

### 色彩系统
```
主色调（Accent）: #137fec（蓝色）
成功色（Success）: #059669（绿色）
错误色（Error）: #dc2626（红色）
警告色（Warning）: #eab308（黄色）

背景层次:
- bg: 主背景
- surface: 卡片背景
- surface-container: 次级容器
- bg-panel: 面板背景

文本层次:
- text: 主文本 (#0f172a)
- text-muted: 次要文本 (#64748b)
- text-dim: 弱化文本 (#94a3b8)
```

### 圆角规范
```
小圆角: 4px（inline code、badge）
中圆角: 6-8px（按钮、代码头部）
大圆角: 10-12px（卡片、代码块）
超大圆角: 18px（气泡消息、输入框）
完全圆: 999px（chip、状态点）
```

### 阴影规范
```
轻微阴影（卡片）:
  0 1px 3px rgba(0,0,0,0.04)

中等阴影（输入框）:
  0 1px 2px rgba(60,64,67,0.10),
  0 6px 18px -14px rgba(60,64,67,0.45)

深阴影（悬停）:
  0 4px 12px rgba(15,23,42,0.04)

弹出层阴影（menu）:
  var(--shadow-popover)
```

### 动画时长
```
快速过渡: 0.15-0.18s（按钮悬停、chip 状态）
标准过渡: 0.2-0.28s（卡片、阴影）
流畅动画: 0.32-0.4s（进场动画、弹出）
长动画: 0.8-2s（脉动、呼吸）
```

### 间距系统
```
紧密: 4-6px（图标与文字）
标准: 8-12px（元素间隔）
宽松: 16-20px（区块间隔）
超宽: 24-32px（消息间隔）
```

---

## Dark Mode 支持

所有组件都支持暗色模式，通过 `:global(.dark)` 选择器切换：

```css
Dark 模式调整:
- 背景变深：#0f172a, #1e293b
- 边框更明显：#334155
- 文本对比度降低：#f8fafc, #e2e8f0
- 渐变颜色调整：蓝色 opacity 降低
- 阴影增强：rgba(0,0,0,0.2-0.3)
```

---

## 响应式设计

- 最大内容宽度：820px（居中对齐）
- 左右 padding：16px（移动端）/ 52-68px（桌面端，右侧留空间给 scrollbar）
- 输入框自动高度：最大 200px（超出滚动）

---

## 可复用性建议

### 1. 提取 Design Token
建议将颜色、圆角、阴影等提取为 CSS 变量：
```css
:root {
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 18px;
  --radius-full: 999px;
  
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.04);
  --shadow-md: 0 1px 2px rgba(60,64,67,0.10), 0 6px 18px -14px rgba(60,64,67,0.45);
}
```

### 2. 组件解耦建议
- `MessageView.vue` 太复杂，建议拆分：
  - `UserMessage.vue`
  - `AssistantMessage.vue`
  - `ThinkingBlock.vue`
  - `ToolCallBlock.vue`

### 3. 动画库提取
可以将常用动画提取为全局 CSS：
```css
@keyframes fadeInUp { ... }
@keyframes pulse { ... }
@keyframes check-pop { ... }
```

---

## 迁移到当前分支的建议

### Step 1: 复制核心组件
```bash
frontend/packages/main-app/src/components/agent/
  ├── ChatWindow.vue
  ├── MessageView.vue
  ├── ActivityMessageView.vue
  ├── ChatInput.vue
  └── timeline/
      ├── TimelineBlockRenderer.vue
      ├── ToolActivityBlock.vue
      ├── ProjectListBlock.vue
      └── PlanTimelineBlock.vue
```

### Step 2: 适配数据结构
- `useHomeAgentSession` → 保留或改为 `useAgUiAgent`
- `AgentMessage` 类型需对齐 AG-UI 协议
- `AgentTimelineBlock` 类型需对齐后端事件

### Step 3: 样式变量统一
- 检查当前分支的 CSS 变量定义
- 合并或覆盖颜色、圆角、阴影定义

### Step 4: 测试清单
- [ ] 用户消息渲染正常
- [ ] Assistant 消息 Markdown 正常
- [ ] 代码块语法高亮 + copy 功能
- [ ] 图片附件上传 + 预览
- [ ] 工具调用卡片状态显示
- [ ] Timeline blocks 渲染
- [ ] Dark mode 切换
- [ ] 响应式布局（移动端）

---

## 技术栈

- Vue 3 Composition API
- TypeScript
- Markdown-it（Markdown 渲染）
- CSS 变量 + scoped styles
- Material Symbols（图标）

---

## 文件位置参考

**前端组件路径**：
```
frontend/packages/main-app/src/
  ├── components/agent/
  │   ├── ChatWindow.vue
  │   ├── MessageView.vue
  │   ├── ActivityMessageView.vue
  │   ├── ChatInput.vue
  │   └── timeline/
  │       ├── TimelineBlockRenderer.vue
  │       ├── ToolActivityBlock.vue
  │       ├── ProjectListBlock.vue
  │       └── PlanTimelineBlock.vue
  ├── composables/
  │   ├── useHomeAgentSession.ts
  │   └── useAgUiAgent.ts
  ├── api/
  │   ├── agent.ts
  │   └── agui.ts
  └── store/
      └── agent.ts
```

**后端对应端点**：
```
backend/app/api/v1/
  ├── agent/routes.py          # 旧接口 /agent/chat/sessions
  └── copilotkit.py            # 新接口 /copilotkit
```

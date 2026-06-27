# ANIFORCE AG-UI 能力实现指南

**基于 OpenAI Agents SDK + AG-UI 协议的完整能力图谱**

---

## Block 0: 核心理解与能力矩阵

### 0.1 AG-UI 协议的本质

AG-UI 不是一个框架，而是一个**通信协议**，定义了：

1. **事件格式**：Agent 和 UI 如何交换信息
2. **状态同步**：前后端如何共享状态
3. **工具调用**：Agent 如何触发 UI 更新
4. **人机协作**：Agent 如何请求用户确认

**类比**：
- HTTP 定义了客户端-服务器通信
- WebSocket 定义了双向实时通信
- **AG-UI 定义了 Agent-UI 协作通信**

---

### 0.2 ANIFORCE 当前能力 vs AG-UI 能力

#### 当前已有能力（✅）

```
┌─────────────────────────────────────────────────────┐
│  ANIFORCE 现有能力                                   │
├─────────────────────────────────────────────────────┤
│  ✅ 用户认证/权限（JWT + get_current_user）         │
│  ✅ MCP Tools（10 个业务工具）                       │
│  ✅ Task 管理（AgentTask 模型 + SQLite）            │
│  ✅ Session 持久化（会话历史）                       │
│  ✅ 事件流（SSE 流式推送）                           │
│  ✅ 多租户隔离（user_id 隔离数据）                   │
│  ✅ 错误处理（AppError + 统一异常）                  │
│  ✅ OpenAI Agents SDK（Agent 框架）                 │
└─────────────────────────────────────────────────────┘
```

#### AG-UI 带来的新能力（🆕）

```
┌─────────────────────────────────────────────────────┐
│  AG-UI 协议新增能力                                  │
├─────────────────────────────────────────────────────┤
│  🆕 Shared State（前后端状态双向同步）              │
│     → 左侧选中项目，AI 自动知道当前上下文           │
│     → AI 切换项目，左侧列表自动高亮                 │
│                                                       │
│  🆕 Generative UI（Agent 动态生成 UI）              │
│     → AI 分析数据后，直接生成图表插入页面           │
│     → AI 创建任务后，自动渲染任务卡片               │
│                                                       │
│  🆕 Human-in-the-Loop（关键操作暂停确认）           │
│     → AI 删除项目前，弹框确认                       │
│     → AI 批量修改前，展示预览                       │
│                                                       │
│  🆕 Frontend Actions（前端能力暴露给 Agent）        │
│     → Agent 可以调用前端的 "切换标签页"             │
│     → Agent 可以调用前端的 "打开详情页"             │
│                                                       │
│  🆕 实时协作（Agent 执行过程中 UI 实时更新）        │
│     → Agent 创建项目，列表立即显示新项目            │
│     → Agent 更新预算，Dashboard 数据实时刷新        │
└─────────────────────────────────────────────────────┘
```

---

### 0.3 能力映射到你的业务场景

#### 场景 1: SaaS 产品加 AI 助手

**你的产品**：广告投放 SaaS（项目管理 + 广告计划 + 素材管理 + 数据分析）

**AG-UI 实现能力**：

| 能力 | 传统方式 | AG-UI 方式 | 价值 |
|------|---------|-----------|------|
| **自动填表** | 用户手动填写创建项目表单 | AI: "帮我创建 RPG 游戏项目，预算 10 万" → 表单自动填充并创建 | ⭐⭐⭐⭐⭐ |
| **自动生成报告** | 用户点击"生成报告"，下载 Excel | AI: "分析项目 A 的广告效果" → 页面实时渲染图表 + 生成 Word 报告 | ⭐⭐⭐⭐⭐ |
| **根据页面数据给建议** | AI 无法知道用户在看哪个项目 | AI 通过 Shared State 知道当前选中项目，给出针对性建议 | ⭐⭐⭐⭐ |
| **自动创建任务** | AI 只能说"建议你创建任务" | AI 直接调用 MCP 工具创建，并更新前端任务列表 | ⭐⭐⭐⭐⭐ |
| **自动执行配置变更** | AI 说"建议修改预算为 X"，用户手动改 | AI 请求确认 → 用户批准 → AI 直接修改 → 前端实时更新 | ⭐⭐⭐⭐⭐ |

---

#### 场景 2: 内部管理后台

**你的场景**：广告投放运营后台

**AG-UI 实现能力**：

| 能力 | 实现方式 | 代码示例 |
|------|---------|---------|
| **查异常** | AI 调用 MCP 工具查询数据，发现异常自动高亮 | `list_campaigns(status="abnormal")` |
| **解释指标波动** | AI 读取 Shared State 当前选中的广告计划，分析波动原因 | `state.current_campaign.metrics` |
| **生成 SQL** | AI 根据用户需求生成 SQL，前端显示预览，用户确认后执行 | HITL 确认 → 执行查询 |
| **创建工单** | AI 发现问题，自动创建工单（MCP 工具），工单列表实时更新 | `create_ticket()` + 前端刷新 |
| **生成复盘文档** | AI 分析项目数据，生成 Markdown 报告，前端实时渲染 | Generative UI |
| **调用内部工具** | AI 调用后台工具（重启服务、清缓存），通过 HITL 确认 | MCP Tools + HITL |

---

#### 场景 3: Agent 工作台

**你的产品形态**：左边聊天，右边工作区

```
┌──────────────────────────────────────────────────────┐
│  ANIFORCE Agent 工作台                                │
├────────────────┬─────────────────────────────────────┤
│  Chat Panel    │  Workspace                          │
│                │                                      │
│  User: 帮我    │  ┌─────────────────────────────┐   │
│  分析项目 A    │  │  项目 A 详情                │   │
│                │  │  - 名称: XXX                │   │
│  AI: 好的，    │  │  - 预算: ¥100,000 ✏️       │   │
│  正在分析...   │  │  - 状态: 进行中             │   │
│                │  └─────────────────────────────┘   │
│  [工具调用]    │                                      │
│  ✓ 查询项目    │  ┌─────────────────────────────┐   │
│  ✓ 查询广告    │  │  📊 广告效果分析            │   │
│  ✓ 生成报告    │  │  [实时渲染的图表]           │   │
│                │  └─────────────────────────────┘   │
│  AI: 分析完成  │                                      │
│  [查看报告]    │  ┌─────────────────────────────┐   │
│                │  │  💡 优化建议                │   │
│                │  │  1. 增加预算 20%            │   │
│                │  │  2. 调整投放时段            │   │
│                │  └─────────────────────────────┘   │
└────────────────┴─────────────────────────────────────┘
```

**AG-UI 实现能力**：

1. **左边聊天，右边工作台**
   - Chat Panel 在左侧（使用 CopilotSidebar）
   - Workspace 在右侧（你的业务组件）
   - AG-UI 协议连接两者

2. **Agent 执行过程中实时更新 UI**
   - Agent 查询项目 → 右侧显示项目详情
   - Agent 生成图表 → 右侧插入图表组件
   - Agent 修改数据 → 右侧数据实时刷新

3. **用户可以中途介入**
   - Agent 准备删除项目 → 弹框确认（HITL）
   - Agent 建议修改预算 → 用户点击"应用"（Frontend Action）
   - 用户手动修改数据 → Shared State 同步给 Agent

4. **Agent 生成结构化产物**
   - 生成报告 → Markdown/PDF
   - 生成图表 → ECharts/Chart.js
   - 生成表格 → Table 组件
   - 生成卡片 → Card 组件

5. **页面状态和 Agent 状态双向同步**
   - 用户在 Workspace 选中项目 A → Agent 知道上下文
   - Agent 切换到项目 B → Workspace 自动切换
   - 用户修改预算 → Agent 状态更新
   - Agent 创建任务 → Workspace 任务列表更新

---

#### 场景 4: AI Native 产品

**如果 ANIFORCE 变成 AI-first 产品**：

```
传统 SaaS 产品：
用户 → 点击按钮 → 填表单 → 提交 → 页面刷新

AI Native 产品：
用户 → 对话 → AI 理解意图 → AI 执行操作 → 页面实时更新
```

**举例**：

**传统方式创建广告计划**：
1. 用户点击"新建广告计划"
2. 填写表单（20+ 字段）
3. 选择投放平台
4. 上传素材
5. 设置预算和时间
6. 提交

**AI Native 方式**：
```
用户: "帮我为项目 A 创建一个 Facebook 广告计划，
      预算 1 万，投放时间下周一到周五，
      目标人群 18-35 岁女性游戏玩家"

AI: [理解意图]
    [调用 create_campaign MCP 工具]
    [生成预览卡片]
    
    ┌─────────────────────────────────────┐
    │  📋 广告计划预览                     │
    │  名称: 项目 A - Facebook 投放        │
    │  平台: Facebook                      │
    │  预算: ¥10,000                       │
    │  时间: 2025-06-16 至 2025-06-20     │
    │  目标: 18-35 岁女性游戏玩家          │
    │                                      │
    │  [确认创建]  [修改]                 │
    └─────────────────────────────────────┘

用户: 点击 [确认创建]

AI: ✅ 已创建广告计划
    [左侧广告计划列表实时更新]
```


---

### 0.4 关键能力对比：传统 vs AG-UI

#### 能力 1: Shared State（状态同步）

**传统方式**：
```
用户在页面 A 选中项目 X
↓
用户切换到 Chat
↓
AI: "你想问什么？"
用户: "分析这个项目"
AI: "请问是哪个项目？" ❌ AI 不知道上下文
```

**AG-UI 方式**：
```
用户在页面 A 选中项目 X
↓ (Shared State 同步)
AI 自动知道: state.current_project = "项目 X"
↓
用户切换到 Chat
用户: "分析这个项目"
AI: "好的，正在分析项目 X..." ✅ AI 有上下文
```

**实现**：
```typescript
// Frontend - 用户选中项目时
useCopilotReadable({
  description: "当前选中的项目",
  value: currentProject
})

// Backend - Agent 自动获取
current_project = shared_state.get("current_project")
```

---

#### 能力 2: Generative UI（动态生成 UI）

**传统方式**：
```
用户: "分析项目 A 的数据"
↓
AI: "根据分析，曝光量增长了 30%，点击率下降了 5%..."
↓
用户: 😕 纯文字，没有可视化
```

**AG-UI 方式**：
```
用户: "分析项目 A 的数据"
↓
AI: [生成图表数据]
↓
前端自动渲染:
┌────────────────────────────┐
│  📊 项目 A 数据分析         │
│  [折线图 - 曝光量趋势]      │
│  [柱状图 - 点击率对比]      │
│  💡 曝光量 ↑30%, 点击率 ↓5% │
└────────────────────────────┘
```

**实现**：
```python
# Backend - Agent 返回结构化数据
emit_custom_event("GENERATE_CHART", {
    "type": "line",
    "data": analytics_data,
    "config": {"title": "曝光量趋势"}
})
```

```typescript
// Frontend - 自动渲染
useCopilotAction({
  name: "show_chart",
  handler: async ({ data, config }) => {
    return <LineChart data={data} config={config} />
  }
})
```

---

#### 能力 3: Human-in-the-Loop（人机协作）

**传统方式**：
```
用户: "删除项目 A"
↓
AI: ❌ 无法执行（没有权限/不安全）
或
AI: ✅ 已删除（太危险！）
```

**AG-UI 方式**：
```
用户: "删除项目 A"
↓
AI: [检测到危险操作]
↓
前端弹框:
┌────────────────────────────┐
│  ⚠️ 需要您的确认           │
│                             │
│  操作: 删除项目             │
│  项目: 项目 A               │
│  包含: 5 个广告计划         │
│  预算: ¥50,000             │
│                             │
│  ⚠️ 此操作不可逆！          │
│                             │
│  [取消]  [确认删除]        │
└────────────────────────────┘
↓
用户点击 [确认删除]
↓
AI: ✅ 已删除项目 A
```

**实现**：
```python
# Backend - Agent 请求确认
approved = await hitl_manager.request_confirmation(
    operation="delete_project",
    details={"project_name": "项目 A"},
    risk_level="high"
)

if approved:
    await mcp_tool("delete_project", {"id": project_id})
```

---

#### 能力 4: Frontend Actions（前端能力暴露）

**传统方式**：
```
AI: "我建议你切换到广告计划列表页查看详情"
用户: 手动点击导航 😓
```

**AG-UI 方式**：
```
AI: [自动执行]
前端自动切换到广告计划列表页 ✅
```

**实现**：
```typescript
// Frontend - 暴露能力给 Agent
useCopilotAction({
  name: "navigate_to_campaigns",
  description: "跳转到广告计划列表页",
  handler: async () => {
    router.push('/campaigns')
    return "已跳转"
  }
})
```

```python
# Backend - Agent 调用
await frontend_action("navigate_to_campaigns")
```

---

#### 能力 5: 实时协作（双向更新）

**传统方式**：
```
用户: "创建项目 B"
↓
AI: "已创建项目 B"
↓
用户: 手动刷新页面才能看到 😓
```

**AG-UI 方式**：
```
用户: "创建项目 B"
↓
AI: [调用 create_project]
↓
左侧项目列表实时出现 "项目 B" ✅
AI: "已创建项目 B"
```

**实现**：
```python
# Backend - Agent 创建项目
project = await mcp_tool("create_project", {...})

# 推送状态更新事件
emit_state_update({
    "projects": [...existing_projects, project]
})
```

```typescript
// Frontend - 自动更新
const { state } = useCopilotContext()

watch(() => state.projects, (newProjects) => {
  projectList.value = newProjects
})
```

---

### 0.5 你的核心问题：是否值得改造？

#### 投入产出分析

| 项目 | 传统 SSE 方式 | AG-UI 方式 | 差异 |
|------|-------------|-----------|------|
| **开发成本** | 已完成 | +350 行代码（适配器） | ⚠️ 需要额外开发 |
| **维护成本** | 低 | 低（协议标准化） | ✅ 持平 |
| **用户体验** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ 显著提升 |
| **功能丰富度** | 基础对话 | Shared State + HITL + GenUI | ✅ 质的飞跃 |
| **产品差异化** | 普通 AI 助手 | AI-first 产品 | ✅ 核心竞争力 |
| **跨平台能力** | 仅 Web | Web + Mobile + Slack | ✅ 扩展性强 |
| **生态兼容** | 自定义协议 | 行业标准（Google/MS 采用） | ✅ 未来可期 |

#### 结论：**强烈建议改造**

**理由**：

1. **用户体验质的飞跃**
   - 从"聊天机器人"变成"AI 协作伙伴"
   - 用户不需要手动操作，AI 直接执行并更新 UI

2. **产品差异化**
   - 市场上大多数 SaaS 只是"加个聊天框"
   - AG-UI 让你的产品成为真正的 AI-first 产品

3. **开发成本可控**
   - 核心适配器只需 ~350 行代码
   - 现有能力 100% 保留
   - 可以渐进式迁移

4. **符合行业趋势**
   - AG-UI 协议已被主流厂商采用
   - 未来会有更多生态工具支持

---

### 0.6 改造路线图

#### 阶段 1: MVP（1-2 周）

**目标**：实现基础 AG-UI 能力

- ✅ Backend AG-UI 适配器
- ✅ Shared State（当前项目/广告计划）
- ✅ HITL（删除操作确认）
- ✅ Frontend Vue 组件（方案 A）

**验证指标**：
- 用户可以通过对话创建/查询项目
- 页面选中项目后，AI 自动知道上下文
- 删除操作需要用户确认

---

#### 阶段 2: 完整体验（2-3 周）

**目标**：完整 Agent 工作台

- ✅ Generative UI（图表生成）
- ✅ Frontend Actions（页面跳转）
- ✅ 实时协作（列表实时更新）
- ✅ 4 个核心 Skills

**验证指标**：
- AI 分析数据后，页面直接渲染图表
- AI 可以切换页面标签
- AI 创建对象后，列表立即刷新
- AI 可以执行复杂工作流

---

#### 阶段 3: 生产优化（1-2 周）

**目标**：生产级稳定性

- ✅ 错误处理和降级
- ✅ 性能优化（事件流压缩）
- ✅ 监控和追踪
- ✅ 用户反馈收集

**验证指标**：
- 99.9% 可用性
- 平均响应时间 < 2s
- 错误率 < 0.1%

---

#### 阶段 4: 高级功能（可选）

**目标**：AI-first 产品形态

- ✅ 升级到 CopilotKit React（方案 B）
- ✅ 多 Agent 协作
- ✅ Slack/Teams 集成
- ✅ 语音交互

---

## 下一步：Block 1 - 核心技术实现

Block 1 将详细讲解：
- 如何实现 Shared State
- 如何实现 Generative UI
- 如何实现 HITL
- 如何实现 Frontend Actions
- 完整代码示例

需要我继续写 Block 1 吗？


---

## Block 1: 核心能力实现详解

### 1.1 Shared State（状态同步）完整实现

#### 1.1.1 什么是 Shared State？

**定义**：前端和 Agent 共享的、双向同步的状态对象

**核心价值**：
- Agent 知道用户在看什么（上下文感知）
- Agent 修改状态，前端立即更新（实时协作）
- 用户修改状态，Agent 立即知道（双向绑定）

**ANIFORCE 的 Shared State 设计**：

```typescript
interface ANIFORCESharedState {
  // 当前上下文
  current_project: Project | null        // 用户当前选中的项目
  current_campaign: Campaign | null      // 用户当前选中的广告计划
  current_material: Material | null      // 用户当前选中的素材
  
  // 视图状态
  active_tab: string                     // 当前激活的标签页
  filters: Record<string, any>           // 当前筛选条件
  sort: { field: string, order: string } // 当前排序
  
  // 用户偏好
  user_preferences: {
    default_platform: string             // 默认投放平台
    budget_range: [number, number]       // 常用预算范围
    target_audience: string[]            // 常用目标人群
  }
  
  // 待处理事项
  pending_operations: Array<{
    id: string
    type: string
    status: 'pending' | 'confirmed' | 'rejected'
    data: any
  }>
}
```

---

#### 1.1.2 Backend 实现

```python
# backend/app/agent_platform/adapters/agui_state.py

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

class ANIFORCESharedState:
    """ANIFORCE 共享状态管理器"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state: Dict[str, Any] = {
            # 当前上下文
            "current_project": None,
            "current_campaign": None,
            "current_material": None,
            
            # 视图状态
            "active_tab": "projects",
            "filters": {},
            "sort": {"field": "created_at", "order": "desc"},
            
            # 用户偏好
            "user_preferences": {
                "default_platform": "facebook",
                "budget_range": [1000, 10000],
                "target_audience": []
            },
            
            # 待处理事项
            "pending_operations": [],
        }
        
        self._history: List[Dict[str, Any]] = []
        self._update_timestamp = datetime.now()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取状态"""
        return self.state.get(key, default)
    
    def set(self, key: str, value: Any, source: str = "agent") -> bool:
        """
        设置状态
        
        Args:
            key: 状态键
            value: 状态值
            source: 来源（"agent" 或 "frontend"）
        
        Returns:
            bool: 是否发生变化
        """
        old_value = self.state.get(key)
        
        if old_value == value:
            return False  # 没有变化
        
        # 记录历史
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            "key": key,
            "old_value": old_value,
            "new_value": value,
            "source": source,
        })
        
        # 更新状态
        self.state[key] = value
        self._update_timestamp = datetime.now()
        
        logger.info(f"[SharedState] {source} updated: {key} = {value}")
        return True
    
    def update(self, updates: Dict[str, Any], source: str = "agent") -> List[str]:
        """
        批量更新状态
        
        Returns:
            List[str]: 发生变化的键列表
        """
        changed_keys = []
        
        for key, value in updates.items():
            if self.set(key, value, source):
                changed_keys.append(key)
        
        return changed_keys
    
    def to_snapshot(self) -> Dict[str, Any]:
        """转换为 AG-UI STATE_SNAPSHOT 事件"""
        return {
            "type": "STATE_SNAPSHOT",
            "snapshot": self.state.copy(),
            "timestamp": self._update_timestamp.isoformat(),
        }
    
    def get_context_summary(self) -> str:
        """获取当前上下文的自然语言描述（供 Agent 使用）"""
        parts = []
        
        current_project = self.state.get("current_project")
        if current_project:
            parts.append(f"当前项目: {current_project.get('name', 'Unknown')}")
        
        current_campaign = self.state.get("current_campaign")
        if current_campaign:
            parts.append(f"当前广告计划: {current_campaign.get('name', 'Unknown')}")
        
        active_tab = self.state.get("active_tab")
        if active_tab:
            parts.append(f"当前页面: {active_tab}")
        
        if not parts:
            return "用户未选中任何对象"
        
        return "、".join(parts)


# 全局状态管理器（按 user_id 隔离）
_state_managers: Dict[str, ANIFORCESharedState] = {}


def get_shared_state(user_id: str) -> ANIFORCESharedState:
    """获取或创建用户的共享状态"""
    if user_id not in _state_managers:
        _state_managers[user_id] = ANIFORCESharedState(user_id)
    return _state_managers[user_id]
```

---

#### 1.1.3 Frontend 实现（Vue 组件）

```typescript
// frontend/packages/main-app/src/composables/useSharedState.ts

import { ref, watch, onMounted } from 'vue'
import { aguiService } from '@/services/aguiService'

export interface SharedState {
  current_project: any | null
  current_campaign: any | null
  current_material: any | null
  active_tab: string
  filters: Record<string, any>
  sort: { field: string; order: string }
  user_preferences: {
    default_platform: string
    budget_range: [number, number]
    target_audience: string[]
  }
  pending_operations: Array<any>
}

export function useSharedState() {
  const state = ref<SharedState>({
    current_project: null,
    current_campaign: null,
    current_material: null,
    active_tab: 'projects',
    filters: {},
    sort: { field: 'created_at', order: 'desc' },
    user_preferences: {
      default_platform: 'facebook',
      budget_range: [1000, 10000],
      target_audience: [],
    },
    pending_operations: [],
  })
  
  // 监听状态变化，同步到 Backend
  const updateBackend = async (key: string, value: any) => {
    try {
      // 这里可以调用一个专门的 API 更新 Backend 状态
      // 或者在下次 AG-UI 请求时带上状态更新
      console.log('[SharedState] Frontend updated:', key, value)
    } catch (error) {
      console.error('[SharedState] Update failed:', error)
    }
  }
  
  // 设置状态（从 Frontend）
  const setState = (key: keyof SharedState, value: any) => {
    (state.value as any)[key] = value
    updateBackend(key, value)
  }
  
  // 批量更新状态（从 Backend）
  const updateFromBackend = (snapshot: Partial<SharedState>) => {
    Object.assign(state.value, snapshot)
  }
  
  return {
    state,
    setState,
    updateFromBackend,
  }
}
```

---

#### 1.1.4 使用示例

**场景 1：用户选中项目，AI 自动知道**

```vue
<!-- ProjectList.vue -->
<script setup lang="ts">
import { useSharedState } from '@/composables/useSharedState'

const { state, setState } = useSharedState()

const selectProject = (project: any) => {
  // 更新 Shared State
  setState('current_project', project)
  
  // UI 高亮
  selectedProjectId.value = project.id
}
</script>

<template>
  <div v-for="project in projects" :key="project.id">
    <div 
      @click="selectProject(project)"
      :class="{ active: project.id === selectedProjectId }"
    >
      {{ project.name }}
    </div>
  </div>
</template>
```

```python
# Backend - Agent 自动获取上下文
shared_state = get_shared_state(user_id)

# 在 System Prompt 中注入上下文
context_summary = shared_state.get_context_summary()
# → "当前项目: 项目 A、当前页面: projects"

system_prompt = f"""
你是 ANIFORCE AI 助手。

当前用户上下文：
{context_summary}

用户正在查看项目列表页，当前选中的是 "项目 A"。
你可以直接针对该项目进行操作，无需再询问用户是哪个项目。
"""
```

---

**场景 2：AI 切换项目，前端自动更新**

```python
# Backend - Agent 切换项目
async def switch_project(project_id: str):
    # 查询项目详情
    project = await mcp_tool("get_project_detail", {"id": project_id})
    
    # 更新 Shared State
    shared_state = get_shared_state(user_id)
    shared_state.set("current_project", project, source="agent")
    
    # 推送状态快照事件
    snapshot_event = shared_state.to_snapshot()
    yield snapshot_event
    
    return f"已切换到项目: {project['name']}"
```

```typescript
// Frontend - 自动响应状态变化
watch(() => state.value.current_project, (newProject) => {
  if (newProject) {
    // 高亮左侧列表
    highlightProject(newProject.id)
    
    // 刷新右侧详情
    loadProjectDetail(newProject.id)
  }
})
```


---

### 1.2 Generative UI（动态生成 UI）完整实现

#### 1.2.1 什么是 Generative UI？

**定义**：Agent 根据执行结果，动态生成并插入前端 UI 组件

**三种模式**：

| 模式 | 描述 | 适用场景 | 控制度 |
|------|------|---------|--------|
| **Controlled** | 预定义组件，Agent 选择+填数据 | 生产环境核心流程 | ⭐⭐⭐⭐⭐ |
| **Declarative (A2UI)** | Agent 输出 JSON，前端映射组件 | 长尾功能 | ⭐⭐⭐ |
| **Open-ended** | Agent 生成 HTML/Markdown | 探索性场景 | ⭐ |

**ANIFORCE 推荐方案**：**Controlled 模式**（生产环境）

---

#### 1.2.2 Backend 实现

```python
# backend/app/agent_platform/adapters/agui_genui.py

from typing import Dict, Any, List, Optional
from enum import Enum

class UIComponentType(Enum):
    """预定义的 UI 组件类型"""
    
    # 数据展示
    TABLE = "table"                    # 表格
    CHART = "chart"                    # 图表
    CARD = "card"                      # 卡片
    LIST = "list"                      # 列表
    METRIC = "metric"                  # 指标
    
    # 表单
    FORM = "form"                      # 表单
    INPUT = "input"                    # 输入框
    SELECT = "select"                  # 下拉框
    DATEPICKER = "datepicker"          # 日期选择
    
    # 交互
    BUTTON = "button"                  # 按钮
    DIALOG = "dialog"                  # 对话框
    NOTIFICATION = "notification"      # 通知
    
    # 布局
    PANEL = "panel"                    # 面板
    TABS = "tabs"                      # 标签页
    COLLAPSE = "collapse"              # 折叠面板


class GenerativeUIManager:
    """Generative UI 管理器"""
    
    @staticmethod
    def generate_chart(
        chart_type: str,
        data: List[Dict[str, Any]],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成图表组件
        
        Args:
            chart_type: 图表类型（line/bar/pie/scatter）
            data: 图表数据
            config: 图表配置（标题、轴标签等）
        
        Returns:
            AG-UI 事件
        """
        return {
            "type": "CUSTOM",
            "name": "GENERATE_UI",
            "value": {
                "component": UIComponentType.CHART.value,
                "props": {
                    "type": chart_type,
                    "data": data,
                    "config": config,
                }
            }
        }
    
    @staticmethod
    def generate_table(
        columns: List[Dict[str, str]],
        data: List[Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成表格组件
        
        Args:
            columns: 列定义 [{"key": "name", "label": "名称", "width": 100}]
            data: 表格数据
            config: 表格配置（分页、排序等）
        """
        return {
            "type": "CUSTOM",
            "name": "GENERATE_UI",
            "value": {
                "component": UIComponentType.TABLE.value,
                "props": {
                    "columns": columns,
                    "data": data,
                    "config": config or {},
                }
            }
        }
    
    @staticmethod
    def generate_card(
        title: str,
        content: str,
        extra: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成卡片组件"""
        return {
            "type": "CUSTOM",
            "name": "GENERATE_UI",
            "value": {
                "component": UIComponentType.CARD.value,
                "props": {
                    "title": title,
                    "content": content,
                    "extra": extra or {},
                }
            }
        }
    
    @staticmethod
    def generate_metrics(
        metrics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成指标卡片
        
        Args:
            metrics: [
                {"label": "曝光量", "value": 10000, "trend": "+20%"},
                {"label": "点击率", "value": "5.2%", "trend": "-0.3%"}
            ]
        """
        return {
            "type": "CUSTOM",
            "name": "GENERATE_UI",
            "value": {
                "component": UIComponentType.METRIC.value,
                "props": {
                    "metrics": metrics
                }
            }
        }
    
    @staticmethod
    def generate_form_preview(
        fields: List[Dict[str, Any]],
        values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成表单预览
        
        用于 HITL 场景：Agent 准备创建对象，先展示表单预览
        """
        return {
            "type": "CUSTOM",
            "name": "GENERATE_UI",
            "value": {
                "component": UIComponentType.FORM.value,
                "props": {
                    "fields": fields,
                    "values": values,
                    "readonly": True,
                }
            }
        }
```

---

#### 1.2.3 Frontend 实现

```vue
<!-- frontend/packages/main-app/src/components/agent/GenerativeUIRenderer.vue -->

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElTable, ElCard, ElProgress } from 'element-plus'
import * as echarts from 'echarts'

interface UIComponent {
  component: string
  props: Record<string, any>
}

const props = defineProps<{
  component: UIComponent
}>()

// 根据组件类型渲染不同的组件
const componentMap = {
  chart: 'ChartComponent',
  table: 'TableComponent',
  card: 'CardComponent',
  metric: 'MetricComponent',
  form: 'FormComponent',
}

const currentComponent = computed(() => {
  return componentMap[props.component.component] || 'div'
})
</script>

<template>
  <div class="genui-renderer">
    <!-- 图表组件 -->
    <ChartComponent 
      v-if="component.component === 'chart'"
      v-bind="component.props"
    />
    
    <!-- 表格组件 -->
    <TableComponent 
      v-else-if="component.component === 'table'"
      v-bind="component.props"
    />
    
    <!-- 卡片组件 -->
    <CardComponent 
      v-else-if="component.component === 'card'"
      v-bind="component.props"
    />
    
    <!-- 指标组件 -->
    <MetricComponent 
      v-else-if="component.component === 'metric'"
      v-bind="component.props"
    />
    
    <!-- 表单组件 -->
    <FormComponent 
      v-else-if="component.component === 'form'"
      v-bind="component.props"
    />
    
    <!-- 未知组件 -->
    <div v-else class="unknown-component">
      Unknown component: {{ component.component }}
    </div>
  </div>
</template>
```

```vue
<!-- ChartComponent.vue -->
<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{
  type: string
  data: any[]
  config: Record<string, any>
}>()

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

const renderChart = () => {
  if (!chartRef.value) return
  
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  
  // 根据类型生成 ECharts 配置
  const option = generateChartOption(props.type, props.data, props.config)
  chartInstance.setOption(option)
}

const generateChartOption = (type: string, data: any[], config: any) => {
  // 这里根据 type 和 data 生成对应的 ECharts 配置
  // 示例：折线图
  if (type === 'line') {
    return {
      title: { text: config.title || '' },
      xAxis: { 
        type: 'category', 
        data: data.map(item => item[config.xField || 'x']) 
      },
      yAxis: { type: 'value' },
      series: [{
        type: 'line',
        data: data.map(item => item[config.yField || 'y'])
      }]
    }
  }
  
  // 其他图表类型...
  return {}
}

onMounted(() => {
  renderChart()
})

watch(() => [props.data, props.config], () => {
  renderChart()
}, { deep: true })
</script>

<template>
  <div ref="chartRef" style="width: 100%; height: 400px;"></div>
</template>
```

---

#### 1.2.4 使用示例

**场景 1：AI 分析数据后生成图表**

```python
# Backend - Agent 分析广告计划数据
async def analyze_campaign(campaign_id: str):
    # 1. 调用 MCP 工具获取数据
    analytics = await mcp_tool("get_campaign_analytics", {
        "campaign_id": campaign_id
    })
    
    # 2. 处理数据
    daily_data = analytics["daily_stats"]
    
    # 3. 生成图表
    genui_manager = GenerativeUIManager()
    
    # 曝光量趋势图
    chart_event = genui_manager.generate_chart(
        chart_type="line",
        data=daily_data,
        config={
            "title": "曝光量趋势",
            "xField": "date",
            "yField": "impressions",
        }
    )
    yield chart_event
    
    # 点击率趋势图
    chart_event2 = genui_manager.generate_chart(
        chart_type="line",
        data=daily_data,
        config={
            "title": "点击率趋势",
            "xField": "date",
            "yField": "ctr",
        }
    )
    yield chart_event2
    
    # 生成指标卡片
    metrics_event = genui_manager.generate_metrics([
        {
            "label": "总曝光量",
            "value": f"{analytics['total_impressions']:,}",
            "trend": f"+{analytics['impressions_growth']}%"
        },
        {
            "label": "平均点击率",
            "value": f"{analytics['avg_ctr']}%",
            "trend": f"{analytics['ctr_change']:+.1f}%"
        },
        {
            "label": "总花费",
            "value": f"¥{analytics['total_cost']:,.2f}",
            "trend": f"+{analytics['cost_growth']}%"
        }
    ])
    yield metrics_event
    
    # 返回文字总结
    return f"""
    ✅ 分析完成
    
    📊 数据概览：
    - 总曝光量：{analytics['total_impressions']:,}（增长 {analytics['impressions_growth']}%）
    - 平均点击率：{analytics['avg_ctr']}%（变化 {analytics['ctr_change']:+.1f}%）
    - 总花费：¥{analytics['total_cost']:,.2f}（增长 {analytics['cost_growth']}%）
    
    💡 建议：
    {analytics['suggestions']}
    """
```

```typescript
// Frontend - 处理 GENERATE_UI 事件
const handleAGUIEvent = async (event: AGUIStreamEvent) => {
  if (event.type === 'CUSTOM' && event.name === 'GENERATE_UI') {
    // 添加到 UI 组件列表
    generatedComponents.value.push(event.value)
  }
}
```

```vue
<!-- 在聊天窗口渲染生成的 UI -->
<template>
  <div class="chat-messages">
    <div v-for="(msg, idx) in messages" :key="idx">
      <!-- 文本消息 -->
      <div v-if="msg.type === 'text'" class="message">
        {{ msg.content }}
      </div>
      
      <!-- 生成的 UI 组件 -->
      <div v-else-if="msg.type === 'ui'" class="generated-ui">
        <GenerativeUIRenderer :component="msg.component" />
      </div>
    </div>
  </div>
</template>
```

**最终效果**：

```
用户: "分析广告计划 A 的数据"

AI: 正在分析...

[图表自动渲染]
┌────────────────────────────────────┐
│  📊 曝光量趋势                      │
│  [折线图实时渲染]                  │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│  📊 点击率趋势                      │
│  [折线图实时渲染]                  │
└────────────────────────────────────┘

[指标卡片自动渲染]
┌──────────┬──────────┬──────────┐
│ 总曝光量  │ 平均点击率│ 总花费    │
│ 1,234,567│  5.2%    │ ¥12,345  │
│ ↑ +20%   │ ↓ -0.3%  │ ↑ +15%   │
└──────────┴──────────┴──────────┘

AI: ✅ 分析完成
    
    📊 数据概览：...
    
    💡 建议：...
```


---

### 1.3 Human-in-the-Loop（人机协作）完整实现

#### 1.3.1 什么是 HITL？

**定义**：Agent 在执行关键操作前，暂停并请求用户确认

**核心价值**：
- 安全保障：防止误操作
- 用户控制：用户始终掌握主导权
- 透明可控：用户清楚 AI 要做什么

**ANIFORCE 的 HITL 场景**：

| 操作类型 | 风险等级 | 是否需要 HITL | 确认内容 |
|---------|---------|-------------|---------|
| 查询项目/广告 | 低 | ❌ | 无需确认 |
| 创建项目/广告 | 中 | ✅ | 展示表单预览 |
| 更新预算 | 中 | ✅ | 展示修改对比 |
| 删除项目 | 高 | ✅ | 展示影响范围 |
| 批量操作 | 高 | ✅ | 展示受影响对象列表 |
| 暂停/启动广告 | 中 | ✅ | 展示影响 |

---

#### 1.3.2 Backend 实现

```python
# backend/app/agent_platform/adapters/agui_hitl.py

import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from loguru import logger
from enum import Enum

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class HITLManager:
    """Human-in-the-Loop 管理器"""
    
    def __init__(self):
        self.pending_confirmations: Dict[str, asyncio.Future] = {}
        self.timeout_seconds = 300  # 5 分钟超时
    
    async def request_confirmation(
        self,
        operation_id: str,
        operation: str,
        details: Dict[str, Any],
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        preview_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        请求用户确认
        
        Args:
            operation_id: 操作唯一 ID
            operation: 操作名称（如 "delete_project"）
            details: 操作详情
            risk_level: 风险等级
            preview_data: 预览数据（可选，用于生成 UI 预览）
        
        Returns:
            bool: 用户是否批准
        """
        # 创建 Future 等待用户响应
        future = asyncio.get_event_loop().create_future()
        self.pending_confirmations[operation_id] = future
        
        logger.info(f"[HITL] Requesting confirmation: {operation_id} | {operation} | {risk_level.value}")
        
        # 等待用户响应（带超时）
        try:
            approved = await asyncio.wait_for(future, timeout=self.timeout_seconds)
            logger.info(f"[HITL] User response: {operation_id} | approved={approved}")
            return approved
        
        except asyncio.TimeoutError:
            logger.warning(f"[HITL] Confirmation timeout: {operation_id}")
            return False  # 超时默认拒绝
        
        finally:
            self.pending_confirmations.pop(operation_id, None)
    
    def respond_confirmation(self, operation_id: str, approved: bool, comment: Optional[str] = None):
        """
        响应用户确认（由前端 API 调用）
        
        Args:
            operation_id: 操作 ID
            approved: 是否批准
            comment: 用户备注（可选）
        """
        future = self.pending_confirmations.get(operation_id)
        if future and not future.done():
            future.set_result(approved)
            logger.info(f"[HITL] Confirmation responded: {operation_id} | approved={approved} | comment={comment}")
        else:
            logger.warning(f"[HITL] No pending confirmation found: {operation_id}")
    
    def generate_confirmation_event(
        self,
        operation_id: str,
        operation: str,
        details: Dict[str, Any],
        risk_level: RiskLevel,
        preview_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """生成 AG-UI 确认请求事件"""
        
        # 根据风险等级选择 emoji
        risk_emoji = {
            RiskLevel.LOW: "ℹ️",
            RiskLevel.MEDIUM: "⚠️",
            RiskLevel.HIGH: "🚨",
        }
        
        # 生成确认消息
        message_parts = [
            f"{risk_emoji[risk_level]} **需要您的确认**",
            "",
            f"**操作**: {operation}",
        ]
        
        # 添加详情
        if details:
            message_parts.append("**详情**:")
            for key, value in details.items():
                message_parts.append(f"- {key}: {value}")
        
        # 添加风险提示
        message_parts.append("")
        message_parts.append(f"**风险等级**: {risk_level.value}")
        
        if risk_level == RiskLevel.HIGH:
            message_parts.append("")
            message_parts.append("⚠️ **此操作不可逆，请谨慎确认！**")
        
        message = "\n".join(message_parts)
        
        return {
            "type": "CUSTOM",
            "name": "HITL_CONFIRMATION_REQUEST",
            "value": {
                "operation_id": operation_id,
                "operation": operation,
                "details": details,
                "risk_level": risk_level.value,
                "message": message,
                "preview_data": preview_data,
                "timestamp": datetime.now().isoformat(),
            }
        }


# 全局实例
_hitl_manager = HITLManager()


def get_hitl_manager() -> HITLManager:
    """获取全局 HITL 管理器"""
    return _hitl_manager
```

---

#### 1.3.3 Backend API 端点

```python
# backend/app/api/v1/agent/agui_routes.py

from ....agent_platform.adapters.agui_hitl import get_hitl_manager

@router.post("/hitl/{operation_id}/respond")
async def hitl_respond(
    operation_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    响应 Human-in-the-Loop 确认请求
    
    Body:
    {
        "approved": true,
        "comment": "用户备注（可选）"
    }
    """
    body = await request.json()
    approved = body.get("approved", False)
    comment = body.get("comment")
    
    hitl_manager = get_hitl_manager()
    hitl_manager.respond_confirmation(operation_id, approved, comment)
    
    return {
        "status": "ok",
        "operation_id": operation_id,
        "approved": approved,
    }
```

---

#### 1.3.4 Frontend 实现

```typescript
// frontend/packages/main-app/src/composables/useHITL.ts

import { ElMessageBox } from 'element-plus'
import { aguiService } from '@/services/aguiService'

export interface HITLRequest {
  operation_id: string
  operation: string
  details: Record<string, any>
  risk_level: 'low' | 'medium' | 'high'
  message: string
  preview_data?: any
}

export function useHITL() {
  /**
   * 显示 HITL 确认对话框
   */
  const showConfirmation = async (request: HITLRequest): Promise<boolean> => {
    try {
      // 根据风险等级选择对话框类型
      const messageType = {
        low: 'info',
        medium: 'warning',
        high: 'error',
      }[request.risk_level] as any
      
      // 显示确认框
      await ElMessageBox.confirm(
        request.message,
        '需要您的确认',
        {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          type: messageType,
          dangerouslyUseHTMLString: false,
        }
      )
      
      // 用户批准
      await aguiService.respondHITL(request.operation_id, true)
      return true
      
    } catch (error) {
      // 用户取消
      await aguiService.respondHITL(request.operation_id, false)
      return false
    }
  }
  
  /**
   * 显示带预览的确认对话框
   */
  const showConfirmationWithPreview = async (request: HITLRequest): Promise<boolean> => {
    // TODO: 实现自定义对话框，展示 preview_data
    return showConfirmation(request)
  }
  
  return {
    showConfirmation,
    showConfirmationWithPreview,
  }
}
```

```typescript
// AGUIChatWindow.vue 中处理 HITL 事件
import { useHITL } from '@/composables/useHITL'

const { showConfirmation } = useHITL()

const handleAGUIEvent = async (event: AGUIStreamEvent) => {
  if (event.type === 'CUSTOM' && event.name === 'HITL_CONFIRMATION_REQUEST') {
    // 显示确认对话框
    const approved = await showConfirmation(event.value)
    
    if (approved) {
      console.log('[HITL] User approved')
    } else {
      console.log('[HITL] User rejected')
    }
  }
}
```

---

#### 1.3.5 使用示例

**场景 1：删除项目（高风险操作）**

```python
# Backend - Agent 执行删除项目
async def delete_project_with_confirmation(project_id: str, user_id: str):
    from uuid import uuid4
    from ....agent_platform.adapters.agui_hitl import get_hitl_manager, RiskLevel
    
    # 1. 查询项目详情
    project = await mcp_tool("get_project_detail", {"id": project_id})
    
    # 2. 统计影响范围
    campaigns_count = len(project.get("campaigns", []))
    total_budget = project.get("budget", 0)
    
    # 3. 生成确认请求
    hitl_manager = get_hitl_manager()
    operation_id = f"delete_project_{uuid4().hex[:8]}"
    
    confirmation_event = hitl_manager.generate_confirmation_event(
        operation_id=operation_id,
        operation="删除项目",
        details={
            "项目名称": project["name"],
            "项目 ID": project_id,
            "包含广告计划": f"{campaigns_count} 个",
            "总预算": f"¥{total_budget:,.2f}",
        },
        risk_level=RiskLevel.HIGH,
    )
    
    # 4. 推送确认事件到前端
    yield confirmation_event
    
    # 5. 等待用户确认
    approved = await hitl_manager.request_confirmation(
        operation_id=operation_id,
        operation="删除项目",
        details=confirmation_event["value"]["details"],
        risk_level=RiskLevel.HIGH,
    )
    
    # 6. 根据用户响应执行
    if approved:
        # 用户批准，执行删除
        await mcp_tool("delete_project", {"id": project_id})
        return f"✅ 已删除项目 '{project['name']}'"
    else:
        # 用户拒绝
        return f"❌ 已取消删除操作"
```

**前端效果**：

```
用户: "删除项目 A"

AI: 正在查询项目信息...

[弹出确认对话框]
┌────────────────────────────────────┐
│  🚨 需要您的确认                    │
│                                    │
│  操作: 删除项目                     │
│  详情:                              │
│  - 项目名称: 项目 A                 │
│  - 项目 ID: proj_123               │
│  - 包含广告计划: 5 个               │
│  - 总预算: ¥50,000.00              │
│                                    │
│  风险等级: high                     │
│                                    │
│  ⚠️ 此操作不可逆，请谨慎确认！      │
│                                    │
│  [取消]         [确认删除]         │
└────────────────────────────────────┘

用户点击 [确认删除]

AI: ✅ 已删除项目 '项目 A'
    [左侧项目列表实时更新]
```

---

**场景 2：批量更新预算（带预览）**

```python
# Backend - Agent 批量更新广告计划预算
async def batch_update_budget(campaign_ids: List[str], new_budget: float):
    from ....agent_platform.adapters.agui_hitl import get_hitl_manager, RiskLevel
    from ....agent_platform.adapters.agui_genui import GenerativeUIManager
    
    # 1. 查询所有广告计划
    campaigns = []
    for cid in campaign_ids:
        campaign = await mcp_tool("get_campaign_detail", {"id": cid})
        campaigns.append(campaign)
    
    # 2. 生成预览表格
    preview_data = [
        {
            "name": c["name"],
            "old_budget": c["budget"],
            "new_budget": new_budget,
            "change": new_budget - c["budget"],
        }
        for c in campaigns
    ]
    
    genui_manager = GenerativeUIManager()
    preview_table_event = genui_manager.generate_table(
        columns=[
            {"key": "name", "label": "广告计划名称"},
            {"key": "old_budget", "label": "原预算"},
            {"key": "new_budget", "label": "新预算"},
            {"key": "change", "label": "变化"},
        ],
        data=preview_data,
        config={"title": "批量修改预览"}
    )
    yield preview_table_event
    
    # 3. 请求确认
    hitl_manager = get_hitl_manager()
    operation_id = f"batch_update_{uuid4().hex[:8]}"
    
    confirmation_event = hitl_manager.generate_confirmation_event(
        operation_id=operation_id,
        operation="批量更新预算",
        details={
            "受影响广告计划": f"{len(campaigns)} 个",
            "新预算": f"¥{new_budget:,.2f}",
        },
        risk_level=RiskLevel.MEDIUM,
        preview_data=preview_data,
    )
    yield confirmation_event
    
    # 4. 等待确认
    approved = await hitl_manager.request_confirmation(
        operation_id=operation_id,
        operation="批量更新预算",
        details=confirmation_event["value"]["details"],
        risk_level=RiskLevel.MEDIUM,
    )
    
    # 5. 执行
    if approved:
        for cid in campaign_ids:
            await mcp_tool("update_campaign", {
                "id": cid,
                "budget": new_budget
            })
        return f"✅ 已更新 {len(campaign_ids)} 个广告计划的预算"
    else:
        return "❌ 已取消批量更新操作"
```


---

### 1.4 Frontend Actions（前端能力暴露）完整实现

#### 1.4.1 什么是 Frontend Actions？

**定义**：将前端的能力（导航、打开弹窗、刷新数据等）暴露给 Agent 调用

**核心价值**：
- Agent 可以主动控制前端行为
- 实现真正的"Agent 驱动 UI"
- 用户体验更流畅（无需手动操作）

**ANIFORCE 的 Frontend Actions**：

| Action 名称 | 描述 | 参数 | 效果 |
|-----------|------|------|------|
| `navigate_to_project` | 跳转到项目详情页 | `project_id` | 页面跳转 |
| `navigate_to_campaigns` | 跳转到广告计划列表 | 无 | 页面跳转 |
| `open_create_dialog` | 打开创建对话框 | `type`, `prefill` | 弹窗 |
| `refresh_list` | 刷新列表数据 | `list_type` | 数据刷新 |
| `highlight_item` | 高亮列表项 | `item_id` | 视觉高亮 |
| `switch_tab` | 切换标签页 | `tab_name` | 标签切换 |

---

#### 1.4.2 Backend 实现

```python
# backend/app/agent_platform/adapters/agui_frontend_actions.py

from typing import Dict, Any, Optional

class FrontendActionsManager:
    """Frontend Actions 管理器"""
    
    @staticmethod
    def navigate(path: str, query: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        导航到指定页面
        
        Args:
            path: 页面路径（如 "/projects/123"）
            query: URL 查询参数（可选）
        """
        return {
            "type": "CUSTOM",
            "name": "FRONTEND_ACTION",
            "value": {
                "action": "navigate",
                "params": {
                    "path": path,
                    "query": query or {},
                }
            }
        }
    
    @staticmethod
    def open_dialog(dialog_type: str, prefill: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        打开对话框
        
        Args:
            dialog_type: 对话框类型（"create_project", "create_campaign" 等）
            prefill: 预填充数据
        """
        return {
            "type": "CUSTOM",
            "name": "FRONTEND_ACTION",
            "value": {
                "action": "open_dialog",
                "params": {
                    "type": dialog_type,
                    "prefill": prefill or {},
                }
            }
        }
    
    @staticmethod
    def refresh_list(list_type: str) -> Dict[str, Any]:
        """刷新列表"""
        return {
            "type": "CUSTOM",
            "name": "FRONTEND_ACTION",
            "value": {
                "action": "refresh_list",
                "params": {
                    "type": list_type,
                }
            }
        }
    
    @staticmethod
    def highlight_item(item_id: str, duration: int = 3000) -> Dict[str, Any]:
        """高亮指定项"""
        return {
            "type": "CUSTOM",
            "name": "FRONTEND_ACTION",
            "value": {
                "action": "highlight_item",
                "params": {
                    "id": item_id,
                    "duration": duration,
                }
            }
        }
    
    @staticmethod
    def switch_tab(tab_name: str) -> Dict[str, Any]:
        """切换标签页"""
        return {
            "type": "CUSTOM",
            "name": "FRONTEND_ACTION",
            "value": {
                "action": "switch_tab",
                "params": {
                    "tab": tab_name,
                }
            }
        }
    
    @staticmethod
    def show_notification(message: str, type: str = "success") -> Dict[str, Any]:
        """显示通知"""
        return {
            "type": "CUSTOM",
            "name": "FRONTEND_ACTION",
            "value": {
                "action": "show_notification",
                "params": {
                    "message": message,
                    "type": type,  # success/warning/error/info
                }
            }
        }
```

---

#### 1.4.3 Frontend 实现

```typescript
// frontend/packages/main-app/src/composables/useFrontendActions.ts

import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'

export interface FrontendActionEvent {
  action: string
  params: Record<string, any>
}

export function useFrontendActions() {
  const router = useRouter()
  
  /**
   * 执行 Frontend Action
   */
  const executeFrontendAction = async (event: FrontendActionEvent) => {
    const { action, params } = event
    
    console.log('[Frontend Action]', action, params)
    
    switch (action) {
      case 'navigate':
        await handleNavigate(params)
        break
      
      case 'open_dialog':
        await handleOpenDialog(params)
        break
      
      case 'refresh_list':
        await handleRefreshList(params)
        break
      
      case 'highlight_item':
        await handleHighlightItem(params)
        break
      
      case 'switch_tab':
        await handleSwitchTab(params)
        break
      
      case 'show_notification':
        handleShowNotification(params)
        break
      
      default:
        console.warn('[Frontend Action] Unknown action:', action)
    }
  }
  
  // 导航
  const handleNavigate = async (params: any) => {
    const { path, query } = params
    await router.push({ path, query })
  }
  
  // 打开对话框
  const handleOpenDialog = async (params: any) => {
    const { type, prefill } = params
    
    // 触发全局事件或调用全局状态管理
    window.dispatchEvent(new CustomEvent('open-dialog', {
      detail: { type, prefill }
    }))
  }
  
  // 刷新列表
  const handleRefreshList = async (params: any) => {
    const { type } = params
    
    window.dispatchEvent(new CustomEvent('refresh-list', {
      detail: { type }
    }))
  }
  
  // 高亮项
  const handleHighlightItem = async (params: any) => {
    const { id, duration } = params
    
    const element = document.querySelector(`[data-item-id="${id}"]`)
    if (element) {
      element.classList.add('highlighted')
      
      setTimeout(() => {
        element.classList.remove('highlighted')
      }, duration || 3000)
    }
  }
  
  // 切换标签
  const handleSwitchTab = async (params: any) => {
    const { tab } = params
    
    window.dispatchEvent(new CustomEvent('switch-tab', {
      detail: { tab }
    }))
  }
  
  // 显示通知
  const handleShowNotification = (params: any) => {
    const { message, type } = params
    
    ElNotification({
      message,
      type: type || 'success',
    })
  }
  
  return {
    executeFrontendAction,
  }
}
```

```typescript
// AGUIChatWindow.vue 中处理 Frontend Action 事件
import { useFrontendActions } from '@/composables/useFrontendActions'

const { executeFrontendAction } = useFrontendActions()

const handleAGUIEvent = async (event: AGUIStreamEvent) => {
  if (event.type === 'CUSTOM' && event.name === 'FRONTEND_ACTION') {
    await executeFrontendAction(event.value)
  }
}
```

---

#### 1.4.4 使用示例

**场景 1：AI 创建项目后自动跳转**

```python
# Backend - Agent 创建项目
async def create_project_and_navigate(project_data: Dict[str, Any]):
    from ....agent_platform.adapters.agui_frontend_actions import FrontendActionsManager
    
    # 1. 创建项目
    project = await mcp_tool("create_project", project_data)
    
    # 2. 刷新项目列表
    actions_manager = FrontendActionsManager()
    refresh_event = actions_manager.refresh_list("projects")
    yield refresh_event
    
    # 3. 导航到项目详情页
    navigate_event = actions_manager.navigate(
        path=f"/projects/{project['id']}",
        query={"highlight": "true"}
    )
    yield navigate_event
    
    # 4. 显示成功通知
    notification_event = actions_manager.show_notification(
        message=f"✅ 已创建项目 '{project['name']}' 并跳转到详情页",
        type="success"
    )
    yield notification_event
    
    return f"✅ 项目 '{project['name']}' 创建成功"
```

**前端效果**：

```
用户: "帮我创建一个 RPG 游戏项目，预算 10 万"

AI: 正在创建项目...

[项目列表自动刷新]
[页面自动跳转到 /projects/proj_123]
[右上角显示成功通知]

AI: ✅ 项目 'RPG 游戏项目' 创建成功
```

---

**场景 2：AI 引导用户填表**

```python
# Backend - Agent 引导用户创建广告计划
async def guide_create_campaign():
    from ....agent_platform.adapters.agui_frontend_actions import FrontendActionsManager
    
    actions_manager = FrontendActionsManager()
    
    # 1. 打开创建对话框，并预填充部分字段
    open_dialog_event = actions_manager.open_dialog(
        dialog_type="create_campaign",
        prefill={
            "platform": "facebook",
            "budget": 5000,
            "target_audience": "18-35岁女性游戏玩家",
        }
    )
    yield open_dialog_event
    
    return """
    ✅ 已打开广告计划创建对话框，并预填充了以下字段：
    - 平台: Facebook
    - 预算: ¥5,000
    - 目标人群: 18-35岁女性游戏玩家
    
    请您补充其他必填字段并提交。
    """
```

---

### 1.5 实时协作（双向更新）完整实现

#### 1.5.1 什么是实时协作？

**定义**：Agent 操作数据后，前端立即更新；用户操作 UI 后，Agent 立即感知

**实现机制**：
- Backend → Frontend: 通过 AG-UI 事件推送
- Frontend → Backend: 通过 Shared State 同步

---

#### 1.5.2 实现示例

**场景：AI 创建项目，列表实时更新**

```python
# Backend - Agent 创建项目
async def create_project_with_realtime_update(project_data: Dict[str, Any], user_id: str):
    from ....agent_platform.adapters.agui_state import get_shared_state
    from ....agent_platform.adapters.agui_frontend_actions import FrontendActionsManager
    
    # 1. 创建项目
    project = await mcp_tool("create_project", project_data)
    
    # 2. 更新 Shared State
    shared_state = get_shared_state(user_id)
    
    # 获取现有项目列表
    projects = shared_state.get("projects", [])
    
    # 添加新项目
    projects.append(project)
    
    # 更新状态
    shared_state.set("projects", projects, source="agent")
    shared_state.set("current_project", project, source="agent")
    
    # 3. 推送状态快照
    state_snapshot_event = shared_state.to_snapshot()
    yield state_snapshot_event
    
    # 4. 高亮新项目
    actions_manager = FrontendActionsManager()
    highlight_event = actions_manager.highlight_item(project["id"])
    yield highlight_event
    
    return f"✅ 已创建项目 '{project['name']}'"
```

```vue
<!-- Frontend - 自动响应状态更新 -->
<script setup lang="ts">
import { watch } from 'vue'
import { useSharedState } from '@/composables/useSharedState'

const { state } = useSharedState()

// 监听项目列表变化
watch(() => state.value.projects, (newProjects, oldProjects) => {
  if (newProjects.length > oldProjects.length) {
    // 有新项目添加
    const newProject = newProjects[newProjects.length - 1]
    console.log('[Real-time Update] New project added:', newProject.name)
    
    // 刷新列表 UI
    projectList.value = newProjects
  }
}, { deep: true })

// 监听当前项目变化
watch(() => state.value.current_project, (newProject) => {
  if (newProject) {
    // 高亮选中项
    selectedProjectId.value = newProject.id
    
    // 加载详情
    loadProjectDetail(newProject.id)
  }
})
</script>
```

---

## Block 1 总结

### 核心能力实现清单

| 能力 | Backend 代码 | Frontend 代码 | 集成难度 |
|------|------------|-------------|---------|
| **Shared State** | `agui_state.py` (~200 行) | `useSharedState.ts` (~80 行) | ⭐⭐ |
| **Generative UI** | `agui_genui.py` (~150 行) | `GenerativeUIRenderer.vue` (~200 行) | ⭐⭐⭐ |
| **HITL** | `agui_hitl.py` (~150 行) | `useHITL.ts` (~50 行) | ⭐⭐ |
| **Frontend Actions** | `agui_frontend_actions.py` (~100 行) | `useFrontendActions.ts` (~100 行) | ⭐⭐ |
| **实时协作** | 基于以上能力组合 | 基于以上能力组合 | ⭐ |

**总计代码量**：
- Backend: ~600 行
- Frontend: ~430 行
- **合计: ~1030 行**

---

## 下一步：Block 2 - 完整集成方案

Block 2 将详细讲解：
- 如何将所有能力集成到现有项目
- 完整的 API 路由设计
- 完整的前端集成方案
- 测试和验证方法

需要我继续写 Block 2 吗？


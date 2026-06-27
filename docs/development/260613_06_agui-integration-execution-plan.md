# ANIFORCE AG-UI 集成执行计划

**版本**: v1.0  
**创建日期**: 2025-06-13  
**预计完成时间**: 4-6 周  
**当前状态**: 📋 规划中

---

## 📋 项目概述

### 目标
将 ANIFORCE 从"传统 AI 助手"升级为"AI-first 协作产品"，实现：
- Shared State（前后端状态同步）
- Generative UI（动态生成界面）
- Human-in-the-Loop（关键操作确认）
- Frontend Actions（AI 控制前端）

### 技术选型
- **Backend**: OpenAI Agents SDK（保持不变）+ 自实现 AG-UI 协议适配器
- **Frontend**: Vue 3（保持不变）+ AG-UI 事件处理
- **协议**: AG-UI Protocol（行业标准）

### 核心原则
- ✅ 100% 向后兼容（现有 API 不变）
- ✅ 渐进式集成（可以分阶段上线）
- ✅ Agent 编排不变（Plan-ReAct + Skills + MCP）
- ✅ 每个 Block 独立可测试

---

## 🗓️ 总体时间规划

| 阶段 | 工作量 | 时间 | 依赖 |
|------|-------|------|------|
| **Block 1**: Shared State（状态同步） | 2-3 天 | Week 1 | 无 |
| **Block 2**: HITL（人机确认） | 2-3 天 | Week 1-2 | 无 |
| **Block 3**: Generative UI（动态 UI） | 3-4 天 | Week 2 | Block 1 |
| **Block 4**: Frontend Actions（前端控制） | 2-3 天 | Week 2-3 | Block 1 |
| **Block 5**: AG-UI 路由集成 | 1-2 天 | Week 3 | Block 1-4 |
| **Block 6**: Skills 创建 | 2-3 天 | Week 3-4 | Block 5 |
| **Block 7**: E2E 测试与优化 | 3-5 天 | Week 4-5 | Block 1-6 |
| **Block 8**: 生产部署 | 2-3 天 | Week 5-6 | Block 7 |

**总计**: 17-26 天 → **4-6 周**

---

## 📊 进度追踪

### 整体进度
- [ ] Block 1: Shared State - 0%
- [ ] Block 2: HITL - 0%
- [ ] Block 3: Generative UI - 0%
- [ ] Block 4: Frontend Actions - 0%
- [ ] Block 5: AG-UI 路由集成 - 0%
- [ ] Block 6: Skills 创建 - 0%
- [ ] Block 7: E2E 测试 - 0%
- [ ] Block 8: 生产部署 - 0%

### 里程碑
- [ ] MVP 完成（Block 1-2）
- [ ] 核心能力完成（Block 1-4）
- [ ] 完整集成完成（Block 1-6）
- [ ] 生产就绪（Block 1-8）

---


## Block 1: Shared State（状态同步）

### 📅 时间规划
- **预计工作量**: 2-3 天
- **开始日期**: TBD
- **完成日期**: TBD
- **状态**: 📋 待开始

### 🎯 目标
实现前后端状态双向同步，让 Agent 知道用户当前上下文（选中的项目/广告计划）。

### 📋 任务清单

#### 1.1 Backend 实现（1 天）

**文件**: `backend/app/agent_platform/adapters/agui_state.py`

- [ ] 创建 `ANIFORCESharedState` 类
  - [ ] 定义状态结构（current_project, current_campaign, 等）
  - [ ] 实现 `get()`, `set()`, `update()` 方法
  - [ ] 实现 `to_snapshot()` 方法（生成 AG-UI 事件）
  - [ ] 实现 `get_context_summary()` 方法（供 Agent 使用）
  - [ ] 实现状态历史记录（可选，用于调试）

- [ ] 创建全局状态管理器
  - [ ] 按 user_id 隔离状态
  - [ ] 实现 `get_shared_state(user_id)` 工厂方法

**代码量**: ~200 行

#### 1.2 Backend API（0.5 天）

**文件**: `backend/app/api/v1/agent/agui_routes.py`

- [ ] 创建 `/api/v1/agent/agui/state/update` 端点
  - [ ] 接收前端状态更新
  - [ ] 更新 Shared State
  - [ ] 返回确认

**代码量**: ~30 行

#### 1.3 Frontend 实现（1 天）

**文件**: `frontend/packages/main-app/src/composables/useSharedState.ts`

- [ ] 创建 `useSharedState` composable
  - [ ] 定义 `SharedState` 接口
  - [ ] 实现 `state` ref
  - [ ] 实现 `setState()` 方法（更新并同步到 Backend）
  - [ ] 实现 `updateFromBackend()` 方法（接收 Backend 更新）

**代码量**: ~80 行

**文件**: 修改现有组件（`ProjectList.vue`, `CampaignList.vue`）

- [ ] 集成 `useSharedState`
- [ ] 用户选中项目时，调用 `setState('current_project', project)`
- [ ] 监听 `state.current_project` 变化，更新 UI 高亮

**代码量**: ~40 行

#### 1.4 集成到 Runtime（0.5 天）

**文件**: `backend/app/agent_platform/runtime.py`

- [ ] 在 `run_task()` 中初始化 Shared State
- [ ] 在 Task 上下文中传递 Shared State
- [ ] 在事件流中推送状态快照（STATE_SNAPSHOT 事件）

**代码量**: ~20 行

**文件**: 增强 System Prompt

- [ ] 在 `backend/app/agent_platform/prompts.py` 中注入上下文摘要
- [ ] 让 Agent 知道当前用户在看什么

**代码量**: ~30 行

### ✅ 验收标准

#### 功能验收
- [ ] **前端 → Agent**: 用户在页面选中项目 A，Agent 对话中提到"当前项目"时自动指 A
- [ ] **Agent → 前端**: Agent 切换项目 B，前端列表自动高亮 B
- [ ] **双向同步**: 前端修改状态，Agent 立即感知；Agent 修改状态，前端立即更新

#### 测试用例
```bash
# 测试 1: 前端 → Agent
1. 前端选中项目 A
2. 发送消息："分析这个项目"
3. 验证：Agent 回复中提到 "项目 A"

# 测试 2: Agent → 前端
1. 发送消息："切换到项目 B"
2. 验证：前端列表自动高亮项目 B
3. 验证：右侧详情页显示项目 B

# 测试 3: 状态持久化
1. 选中项目 A
2. 刷新页面
3. 验证：项目 A 仍然是选中状态
```

### 📦 交付物
- [ ] `agui_state.py` (Backend)
- [ ] `useSharedState.ts` (Frontend)
- [ ] 修改后的 `ProjectList.vue`, `CampaignList.vue`
- [ ] 测试报告（3 个测试用例通过截图）

### 🐛 已知问题
（开发过程中记录）

### 📝 开发日志
（每天更新）

---


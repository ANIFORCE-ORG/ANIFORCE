# ANIFORCE 项目现状与开发路线图

**更新日期**: 2025-06-13  
**版本**: v1.0

---

## 📊 当前项目状态（真实情况）

### ✅ 已完成的核心能力

#### 1. Backend 基础架构
- ✅ **FastAPI 应用框架**
  - 完整的 API 路由系统
  - JWT 认证和权限控制（`Depends(get_current_user)`）
  - 统一异常处理
  - 请求上下文管理（`context.py`, `middleware.py`）

#### 2. Agent 平台（基础版）
- ✅ **OpenAI Agents SDK 集成**
  - `OpenAISDKAdapter` - SDK 封装（~360 行）
  - `AgentRuntime` - 任务执行引擎（~240 行）
  - 支持 MCP 服务器连接（通过 `mcp_servers` 参数）
  - 支持 Session 持久化（SQLite）

- ✅ **Task 管理系统**
  - `AgentTask` 模型（状态机清晰）
  - `AgentTaskEvent` 事件流模型
  - `AgentTaskRepository` - 数据访问层
  - SQLite 存储（`tasks.db`, `sessions.db`）

- ✅ **事件流系统**
  - SSE 流式推送
  - 事件类型：runtime.*, message.*, tool_call.*
  - 序列号支持（支持断点续传）

#### 3. MCP Tools（10 个业务工具）
- ✅ **Project Tools** (5 个)
  - list_projects, create_project, get_project_detail, update_project, delete_project
  
- ✅ **Campaign Tools** (5 个)
  - list_campaigns, create_campaign, get_campaign_detail, update_campaign, delete_campaign

- ✅ **MCP 协议端点**
  - `/api/v1/mcp` - MCP StreamableHTTP 端点
  - 自动解析 JWT token，user_id 隔离

#### 4. 多租户隔离
- ✅ 用户认证（JWT）
- ✅ 数据隔离（所有查询自动加 user_id 过滤）
- ✅ MCP 工具自动获取 user context

#### 5. Frontend（Vue 3）
- ✅ 基础聊天界面（`ChatPanel.vue`）
- ✅ SSE 事件接收和渲染
- ✅ 项目/广告计划列表页

---

### ❌ 尚未实现的能力

#### 1. Agent 编排（核心缺失）
- ❌ **没有 Plan-Execute 框架**
- ❌ **没有 ReAct Loop**
- ❌ **没有 Skills 系统**（虽然有 `backend/app/agent_platform/skills/` 目录，但是空的）
- ❌ **没有多 Agent 协作**
- ❌ **没有 Sub-Agents**

**当前状态**：
- Agent 只是简单的"一次性调用"
- 没有复杂的任务分解
- 没有多步骤执行
- 没有自我反思和验证

#### 2. AG-UI 协议（完全没有）
- ❌ **没有 Shared State**
- ❌ **没有 Generative UI**
- ❌ **没有 Human-in-the-Loop**
- ❌ **没有 Frontend Actions**

**当前状态**：
- 只是传统的"聊天机器人"
- Agent 不知道用户在页面上选中了什么
- Agent 无法动态生成 UI 组件
- Agent 无法请求用户确认
- Agent 无法控制前端行为

#### 3. Skills 系统（目录存在但为空）
- ❌ 没有任何 SKILL.md 文件
- ❌ 没有 Skills 加载机制
- ❌ 没有 Skills 索引和调用

---

## 🎯 关键发现

### 发现 1: Agent 编排是基础，AG-UI 是增强

```
优先级：
1️⃣ Agent 编排（Plan-Execute + Skills）
   ↓ 没有这个，Agent 只能做简单对话
   
2️⃣ AG-UI 协议（前后端协同）
   ↓ 没有这个，无法实现 AI-first 产品体验
```

**结论**：**必须先做 Agent 编排，再做 AG-UI！**

### 发现 2: 当前架构支持渐进式升级

✅ **好消息**：
- OpenAI Agents SDK 已经集成
- MCP Tools 已经实现
- Event Stream 已经实现
- 可以在此基础上增量开发

❌ **坏消息**：
- 需要增加的代码量不小（预计 2000-3000 行）
- 需要重构 System Prompt
- 需要设计 Skills 规范

---

## 🗓️ 重新规划的开发路线图

### 阶段 1: Agent 编排基础（2-3 周）

#### Phase 1.1: Skills 系统（1 周）
**目标**: 让 Agent 能够加载和调用 Skills

- [ ] 定义 SKILL.md 规范
- [ ] 实现 Skills 加载器
- [ ] 创建 3-5 个核心 Skills
- [ ] 集成到 OpenAI Agent

**交付物**:
- `backend/runtime/skills/` 下有 3-5 个 SKILL.md
- Skills 自动加载到 Agent

#### Phase 1.2: Plan-Execute 框架（1 周）
**目标**: Agent 能够分解任务并逐步执行

- [ ] 设计 TodoList 数据结构
- [ ] 实现 Planning 节点（生成 Todo）
- [ ] 实现 Execute 节点（执行 Todo）
- [ ] 实现 Verify 节点（验证结果）

**交付物**:
- Agent 能够分解复杂任务
- 执行过程中显示 Todo 列表

#### Phase 1.3: 增强 System Prompt（3-5 天）
**目标**: Agent 知道何时用 Skills、何时分解任务

- [ ] 编写完整的 System Prompt
- [ ] 注入 Skills 索引
- [ ] 注入 MCP Tools 列表
- [ ] 测试和调优

---

### 阶段 2: AG-UI 协议集成（2-3 周）

#### Phase 2.1: Shared State（3-4 天）
**目标**: 前后端状态同步

- [ ] Backend: `agui_state.py`
- [ ] Frontend: `useSharedState.ts`
- [ ] 集成到现有组件

#### Phase 2.2: Human-in-the-Loop（2-3 天）
**目标**: 危险操作需要确认

- [ ] Backend: `agui_hitl.py`
- [ ] Frontend: `useHITL.ts`
- [ ] 创建确认对话框组件

#### Phase 2.3: Generative UI（3-4 天）
**目标**: Agent 动态生成图表

- [ ] Backend: `agui_genui.py`
- [ ] Frontend: `GenerativeUIRenderer.vue`
- [ ] 实现图表/表格组件

#### Phase 2.4: Frontend Actions（2-3 天）
**目标**: Agent 控制前端

- [ ] Backend: `agui_frontend_actions.py`
- [ ] Frontend: `useFrontendActions.ts`

#### Phase 2.5: AG-UI 路由集成（2-3 天）
**目标**: 统一 AG-UI 端点

- [ ] `/api/v1/agent/agui/stream` 端点
- [ ] 事件转换层
- [ ] 完整测试

---

### 阶段 3: E2E 测试与优化（1 周）

- [ ] 完整功能测试
- [ ] 性能优化
- [ ] 错误处理完善
- [ ] 文档完善

---

## 📝 调整后的时间估算

| 阶段 | 内容 | 工作量 |
|------|------|--------|
| **阶段 1** | Agent 编排基础 | 2-3 周 |
| **阶段 2** | AG-UI 协议集成 | 2-3 周 |
| **阶段 3** | E2E 测试与优化 | 1 周 |
| **总计** | | **5-7 周** |

---

## 🎯 核心结论

### 1. 优先级调整

**之前的理解**（错误）：
```
直接实现 AG-UI → 完成
```

**现在的理解**（正确）：
```
阶段 1: Agent 编排（Plan + Skills）
    ↓
阶段 2: AG-UI 协议
    ↓
阶段 3: 完整产品
```

### 2. 为什么要先做 Agent 编排？

| 能力 | 没有 Agent 编排 | 有 Agent 编排 |
|------|---------------|-------------|
| **任务分解** | ❌ 只能一次性回答 | ✅ 能分解为多步骤 |
| **Skills 调用** | ❌ 无法使用领域知识 | ✅ 能使用专业工作流 |
| **复杂任务** | ❌ 无法处理 | ✅ 能自动规划执行 |
| **AG-UI** | ⚠️ 能用但效果差 | ✅ 完整体验 |

**举例**：

**场景**: 用户说"帮我优化项目 A 的广告投放"

**没有 Agent 编排**:
```
AI: "建议你做以下事情：
1. 分析数据
2. 调整预算
3. 优化素材
..."

→ 只是建议，不会执行
```

**有 Agent 编排**:
```
AI: [Planning]
Todo 1: 分析项目 A 的数据
Todo 2: 识别表现差的广告计划
Todo 3: 生成优化建议
Todo 4: 请求用户确认
Todo 5: 执行调整

[Execute Todo 1]
调用 Skill: data-analysis
...

→ 真正执行，有步骤，可追踪
```

---

## 下一步：写可执行的 Block 文档

基于以上真实状态，我会写一个**完全基于实际情况**的 Block 化开发手册。

需要我开始写吗？


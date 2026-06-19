# Session State Architecture 设计结论

日期：2026-06-19
状态：架构设计阶段，尚未实现

---

## 核心结论

ANIFORCE 的 Agent 不是聊天机器人，它是驾驶舱里的自动驾驶员。用户不是在和 Agent "聊天"，用户是在和 Agent "协作完成一个长程业务任务"。这个协作过程是结构化的：按 Act 组织，按 Panel 投影，按 HITL 审批，按 side_effect 同步业务状态。

---

## 产品理解

### 驾驶舱模型

```text
左侧：任务历史（你做过什么）
中间：你和 Agent 的对话流（正在发生什么）
右侧：业务实体的实时投影（Agent 执行结果改变了哪些业务状态）

这三者不是独立的三块 UI，而是同一个任务的三种视角。
```

### Act（幕）抽象

每一幕对应一个完整的业务动作：

```text
Act 1: 创建项目 → panel = context
Act 3: 生成素材 → panel = creative
Act 7: 获取数据 → panel = analysis
Act 9: 调整预算 → panel = budget
Act 10: 总结 → panel = audit

Agent 的每个执行阶段，不只是产生文本，
它还决定了用户应该看哪个业务维度。
```

这不是"消息驱动 UI"，这是"Act 驱动 Workspace 投影"。

### Panel（投影面板）

五个 panel 是业务实体的五种投影维度：

```text
context  → 项目 + 计划列表（当前业务上下文）
creative → 素材库（创作产出）
analysis → 投放数据对比（分析结果）
budget   → 预算分配变动（调整动作）
audit    → 全流程复盘（审计记录）
```

### 用户在任意工位进入

```text
✓  用户可能直接从"调预算"开始（跳过创建项目和计划）
✓  用户可能在"生成素材"阶段回滚到上一个版本
✓  用户可能在"分析"阶段改了参数重新跑
✓  用户可能在一个已经运行了 3 天的 session 上继续追加操作
✓  用户可能把一个 session 的方案 clone 到新 session 做对比实验

Act 不是固定序列，而是 DAG
Panel 不是自动切换，而是用户可以手动切换也可以被 Agent 推荐
side_effect 不是单向推进，而是可以回滚、覆盖、重建
```

---

## 状态存储的分层

### Layer 0: 权威业务数据（backend DB）

```text
project, campaign, material, budget, performance

特点：
- 已落库的事实，不可随意修改
- 修改必须通过业务 API（有审计）
- 这是所有状态的权威源
- 没有上下文限制问题
```

### Layer 1: Session 状态存储（backend）

```text
存什么：
- 当前 session 的业务上下文摘要
  （当前 project_id、关联 campaigns、状态）
- session 内的变更历史
  （谁在什么时候改了什么）
- 用户草稿 / 待确认操作
  （HITL pending 状态）
- Agent 执行计划进度
  （当前 act、已完成 acts、待执行 acts）

特点：
- 不受 LLM 上下文限制
- 可以无限增长
- Agent 每轮执行前从这里读取摘要
- 前端可以从这里重建 Workspace 投影
- 支持回滚（记录了变更历史）
```

### Layer 2: LLM 对话缓存（SQLiteSession）

```text
存什么：
- 用户消息 + Agent 回复 + 工具调用历史

特点：
- 有上下文窗口硬上限
- 只用于 LLM 推理时的上下文拼接
- 不是业务状态的事实源
- 超出上限时需要 compaction（摘要压缩）

关键设计：
- 不往 session 里塞完整的业务数据
- 只塞必要摘要和引用
- 超长历史做 compaction：
  保留最近 N 轮完整，更早的压缩成摘要
```

### Layer 3: 前端临时状态

```text
存什么：
- 当前 tab / 选中实体
- 表单草稿（未保存的编辑）
- UI 交互状态

特点：
- 不是事实源
- 但 Agent 应该知道（通过 context_snapshot）
- 用户刷新页面后可能丢失
- 需要的关键草稿可以持久化到 Layer 1
```

---

## Agent 每轮执行的上下文构建

不再是"把全部 session 历史喂给 LLM"，而是：

```text
每轮 Agent 执行时的 prompt 构建：

1. System Prompt（固定的能力描述）

2. Session Context Summary（从 Layer 1 读取）
   - 当前 session 关联的项目和计划
   - 当前各实体的最新状态摘要
   - 待确认的 HITL 操作
   - 最近变更历史

3. 近 N 轮对话历史（从 Layer 2 读取）
   - 只保留最近几轮完整对话
   - 更早的已经 compaction 成摘要，放在 Session Context Summary 里

4. 当前用户消息 + context_snapshot（从 Layer 3）

这样：
- 不管 session 有多长，LLM 上下文都不会超限
- Agent 总能看到最新的业务状态，不会因为历史太长遗漏
- 用户在任意时刻进入，Agent 都能正确理解当前现场
- 回滚时只需要更新 Layer 1 的状态，Agent 下一轮自动拿到最新事实
```

---

## Session State Schema 设计方向

```text
SessionState（存 Layer 1，backend 维护）：
{
  session_id,
  user_id,

  // 业务上下文：当前 session 关联的实体
  context: {
    project_id,
    campaign_ids: [...],
    material_ids: [...],
    active_entities: {
      project: { id, name, budget, status },
      campaigns: [{ id, name, platform, budget, status }],
      materials: [{ id, name, type, status }],
    }
  },

  // 执行状态：当前进度
  execution: {
    current_phase: "budget_adjustment",
    completed_phases: ["project_creation", "campaign_creation", ...],
    pending_hitl: [{ operation_id, type, detail }],
  },

  // 变更日志：可回滚的记录
  changelog: [
    { entity, field, old, new, timestamp, rollbackable }
  ],

  // 对话摘要（compaction 结果）
  conversation_summary: "用户创建了 RPG 项目，2 个计划，3 张 AI 素材..."

  // 前端状态快照（每次发消息时更新）
  ui_snapshot: {
    route, tab, selected_entities, draft_edits
  }
}
```

---

## 架构拓扑

```text
┌──────────────────────────────────────────────────────────────┐
│  Frontend                                                    │
│                                                              │
│  不是"回放固定剧本"                                          │
│  而是"实时展示当前业务状态 + Agent 执行过程"                  │
│                                                              │
│  Workspace 投影数据来源：                                     │
│    - 权威数据：backend API 返回的最新实体状态                 │
│    - Agent 事件：side_effect 事件触发对应 Panel 刷新          │
│    - 本地草稿：frontend form state                           │
│                                                              │
│  不需要在前端存完整业务状态                                   │
│  前端是投影，不是事实源                                       │
│  打开任何 session，重新拉 Layer 0 + Layer 1 就能重建视图     │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │  POST /api/v1/agent/runs
                            │  { prompt, session_id, context_snapshot }
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  Backend                                                     │
│                                                              │
│  三件事：                                                    │
│    1. JWT 校验 + 用户态                                     │
│    2. 维护 Session State（Layer 1）                         │
│       - 接收 context_snapshot，合并到 session state          │
│       - Agent 工具调用后更新 session state                   │
│       - 提供 session state 给 agent-service                  │
│    3. 转发 + SSE 透传                                       │
│                                                              │
│  关键：Agent 工具调用回 backend 时，                          │
│  backend 更新 DB（Layer 0）+ 更新 session state（Layer 1）   │
│  + 发 side_effect 事件给前端                                 │
│                                                              │
│  这不是简单 proxy，这是 Session State Manager                │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │  POST /api/agent/runs
                            │  { prompt, session_id, jwt, session_state }
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  Agent Service                                               │
│                                                              │
│  每轮执行上下文构建：                                        │
│    system_prompt                                             │
│    + session_state.summary（从 Layer 1）                    │
│    + 近 N 轮对话历史（从 Layer 2，SQLiteSession）            │
│    + 用户消息                                                │
│                                                              │
│  SQLiteSession 只存对话历史，                                │
│  不存业务状态，有 compaction 机制                             │
│                                                              │
│  工具调用 → backend REST → backend 更新 DB + session state   │
│  → side_effect 事件回 frontend                               │
│                                                              │
│  HITL → interrupt/resume，不是前端弹窗                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 关键设计决策

### 决策 1：frontend 到 agent-service 必须经过 backend

```text
✗  frontend → agent-service
✓  frontend → backend → agent-service

理由：
- backend 拥有用户态，必须校验后才放行
- backend 是业务事实源，Agent 调工具后结果要回 backend
- agent-service 是内部服务，frontend 不应该知道它的存在
- 后续限流、审计、降级都在 backend 做
```

### 决策 2：backend 对 agent-service 不是简单 proxy

backend 是 Session State Manager，要做：

```text
① 校验：JWT → current_user
② 上下文：接收 frontend context_snapshot，存到 session_state
③ 转发：把 prompt + session_id + JWT + session_state 传给 agent-service
④ 透传：SSE 流不缓冲，直接回 frontend
⑤ 更新：Agent 工具调用后更新 DB + session_state
⑥ 事件：发 side_effect 事件给前端刷新 Workspace
```

### 冰策 3：三类状态各有事实源

```text
权威状态（已落库）  → backend DB
  project, campaign, material, budget, performance

临时状态（未保存）  → frontend
  用户正在编辑的表单草稿、当前选中实体、当前 tab

Agent 可见状态      → session_state（backend 维护）
  权威状态的投影 + 临时状态的快照 + 最近 UI 事件
```

### 决策 4：Agent 不直接控制前端 UI

```text
✗  Agent 发指令让前端切换 tab / 打开弹窗
✓  Agent 通过工具修改后端数据，后端广播语义事件，前端自行决定如何响应

事件方向：
frontend → backend：用户消息 + context_snapshot
backend → agent-service：prompt + session_id + JWT + session_state
agent-service → backend：MCP 工具调用（回 backend REST）
backend → frontend：SSE 流 + 语义事件
```

### 决策 5：LLM 上下文必须 compaction

```text
SQLiteSession 不是状态存储，它是对话缓存
有硬上限（模型上下文窗口）

超出上限时：
- 把更早的对话压缩成摘要
- 摘要存到 Layer 1 的 conversation_summary
- 最近 N 轮保持完整在 Layer 2

压缩时机：
- 每轮 run 结束后检查 token 数
- 或定期 compaction（后台任务）
```

---

## 尚未解决的问题

### 问题 1：Session State 的存储介质

```text
- backend DB 里单独一张表？
- 还是 Redis / KV？
- changelog 要不要单独存？
- compaction 策略什么时候触发？
```

### 问题 2：Compaction 机制细节

```text
- SQLiteSession 超过 N 条时怎么压缩？
- 压缩后的摘要存到哪里？（应该是 Layer 1 的 conversation_summary）
- 压缩时机：每轮 run 结束后检查？还是定期？
```

### 问题 3：side_effect 事件的传输方式

```text
- 混在 SSE 流里？
- 还是单独的 WebSocket channel？
- 前端怎么区分"消息事件"和"业务变更事件"？
```

### 问题 4：HITL 的 interrupt/resume 机制

```text
- Agent runtime 怎么暂停？
- 用户确认后怎么恢复？
- 暂停期间 Agent 状态存哪？
```

### 问题 5：Session State 和 Agent 执行的耦合度

```text
- Agent 每轮都从 backend 拿 state？还是 agent-service 自己维护一份？
- 如果 backend 和 agent-service 的 state 不一致怎么办？
```

---

## 落地顺序（待定）

```text
Step 1：backend agent gateway（基础转发）
Step 2：Session State schema + backend 存储表
Step 3：context_snapshot 定义 + 前端发送
Step 4：Agent 执行前注入 session_state 到 prompt
Step 5：side_effect 事件定义 + SSE 传输
Step 6：compaction 机制
Step 7：HITL interrupt/resume
Step 8：回滚和版本控制
```

---

## 参考设计稿

- `docs/design/260619_home_design.vue`：驾驶舱两态 + Act-driven 投影原型
- 设计稿揭示了：Act 驱动 Panel、ToolStep 分 HITL/backend、applyActSideEffect 是状态投影同步

---

## 结论

架构要支撑的不是"前端调后端 API"，而是"Act-driven 的状态投影系统"。Session State Manager 是核心，它维护 Layer 1，连接 Layer 0（权威数据）和 Layer 2（对话缓存），驱动 Layer 3（前端投影）。LLM 上下文限制通过 compaction 解决，用户在任意工位进入通过 Session State Summary 解决，回滚通过 changelog 解决。
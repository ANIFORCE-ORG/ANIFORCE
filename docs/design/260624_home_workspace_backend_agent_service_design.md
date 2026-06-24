# 首页 Workspace 终态的 Backend / Agent-Service 承接方案

**日期**：2026-06-24
**性质**：产品终态承接设计，不是代码改造手册
**输入**：

- `docs/design/aniforce-首页-增加workspace-v1.0.html`
- `docs/design/260623_agent_session_run_refactor_dev_manual.md`
- `docs/design/session-state-architecture.md`
- `resources/openai-agents-python/docs/sessions/index.md`
- `resources/openai-agents-python/docs/running_agents.md`
- `resources/openai-agents-python/docs/streaming.md`
- `resources/openai-agents-python/docs/results.md`
- `resources/openai-agents-python/docs/human_in_the_loop.md`

---

## 0. 结论

首页设计稿表达的终态不是一个 Chatbot 页面，而是：

```text
左侧：产品 session 列表
中间：用户与 Agent 的可见协作过程
右侧：当前 session 的 workspace 投影
```

其中 Workspace 不是 agent-service 的 runtime UI，也不是 OpenAI SDK Session 的对话历史副产物。它是 backend 业务事实和 session 状态的产品化投影。

因此承接原则是：

```text
Backend = 产品事实源 + Workspace 投影源
Agent Service = LLM runtime + tool execution adapter
OpenAI Agents SDK Session = LLM replay cache
Frontend = 投影展示 + 临时交互态
```

首期不要做复杂 Act，也不要做队列、RunState resume、完整 DAG。首页终态可以先用更小模型承接：

```text
Session
Message
Run
WorkspaceDraft
WorkspaceVersion
SessionState
Changelog
SideEffect
```

---

## 1. 从设计稿反推的真实产品状态

设计稿里有两种页面模式：

```text
empty  = 新任务空态，只显示大输入框
active = 工作中状态，显示 Chat + Workflow + Workspace
```

active 状态里，前端当前用本地 JS 模拟了以下事实：

### 1.1 Session 历史

设计稿的 `historyTemplates` 和 `sessions` 表达了：

- 每个历史会话有 `label`。
- 每个会话有自己的消息流。
- 每个会话有自己的 draft、history、versions、activeVersionId。
- 点击历史会话后，Chat 和 Workspace 必须一起恢复。

这要求 backend 不能只存聊天消息，还必须存 workspace 当前状态和版本。

### 1.2 Chat 可见消息

设计稿的 `messages` 是用户可见消息：

```js
{ role: "user", text: "..." }
{ role: "agent", text: "...", html: "..." }
```

终态里它应该落到 backend `agent_messages`，用于：

- 刷新页面后恢复聊天流。
- 历史会话打开后恢复对话。
- 展示 prompt diff、校验摘要、工具进度等用户可见内容。

但它不应该成为业务状态事实源。

### 1.3 Workspace Draft

设计稿的 `draft` 表达的是当前可编辑业务草稿：

```js
{
  prefix,
  budget,
  country,
  device,
  event,
  bid,
  account,
  materials,
  published
}
```

这不是纯 UI state。用户刷新、切 session、继续追问、保存草稿、发布校验时都依赖它。

所以它应该有 backend 持久化模型：

```text
workspace_drafts
```

首期可以先用 JSON 存储投放计划草稿，后续再拆成强业务表。

### 1.4 Workspace Version

设计稿的 `versions` 表达的是“历史修改信息”：

```js
{
  id,
  number,
  time,
  prompt,
  changes,
  draft
}
```

它支持：

- 显示 V1 / V2 / 当前修订。
- 查看每次 prompt 对草稿改了什么。
- 回溯某个修订版本。

这不是 agent run log，也不是 changelog 的完全替代品。它更接近用户可见的 workspace 版本快照。

所以需要：

```text
workspace_versions
```

### 1.5 Workflow Strip

设计稿有四个节点：

```text
Prompt 解析 -> SaaS 草稿 -> 发布校验 -> 同步平台
```

这不是必须引入 Act 的理由。首期可以把它作为 `SessionState.workflow_json` 或 `workspace_status` 的投影：

```text
current_step: prompt_parsed | draft_ready | validation_required | syncing | published
checks: [{type, status, message}]
```

### 1.6 Workspace Context Cards

设计稿会根据 prompt intent 切换右侧视图：

```text
project/material/analysis/plan
```

这说明 backend 要能返回：

- 当前 workspace 类型。
- 当前关联实体。
- 当前草稿。
- 当前分析/素材/项目投影摘要。

但首期不需要让 Agent 直接控制前端组件树。Agent 只产生业务变更和推荐的 workspace intent；前端从 backend 拉投影数据后决定展示哪个组件。

---

## 2. Backend 需要承接什么

### 2.1 必须成为事实源的数据

```text
agent_sessions        产品会话元数据
agent_messages        用户可见消息
agent_runs            一次用户 turn 的执行记录
session_states        当前 session 的业务上下文投影
workspace_drafts      当前 workspace 草稿
workspace_versions    用户可见 workspace 修订版本
business DB           projects / campaigns / materials / metrics 等业务事实
```

### 2.2 不应该由 backend 高频承接的数据

```text
OpenAI SDK ResponseInputItem replay items
raw token deltas
agent-service 内部 RunState 临时对象
LLM 推理链完整 thinking.content（生产默认不存）
```

这些数据属于 runtime cache、debug 信息或隐私高风险数据。

---

## 3. 建议的最小数据模型

### 3.1 `workspace_drafts`

首期建议 JSON 化，避免过早拆表：

```sql
CREATE TABLE workspace_drafts (
    draft_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    draft_type TEXT NOT NULL DEFAULT 'campaign_plan',
    status TEXT NOT NULL DEFAULT 'draft',
    content_json TEXT NOT NULL,
    active_version_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES agent_sessions(session_id)
);

CREATE UNIQUE INDEX idx_workspace_drafts_session
ON workspace_drafts(session_id);
```

`content_json` 示例：

```json
{
  "prefix": "AUTO",
  "campaign_name": "AUTO_US_REG_META_202606",
  "budget": 800,
  "country": "US",
  "device": "iOS",
  "event": "CompleteRegistration",
  "bid": "Lowest cost",
  "account": "FunGame_Meta_US_iOS",
  "materials": ["Video_A_winner", "Playable_03", "Endcard_US_Reg"],
  "published": false,
  "validation": [
    {"type": "ok", "text": "平台权限通过"},
    {"type": "warn", "text": "素材偏少，建议补 2 条"}
  ]
}
```

### 3.2 `workspace_versions`

```sql
CREATE TABLE workspace_versions (
    version_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    version_no INTEGER NOT NULL,
    source_run_id TEXT,
    source_message_id TEXT,
    prompt TEXT,
    changes_json TEXT NOT NULL,
    draft_snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES agent_sessions(session_id)
);

CREATE UNIQUE INDEX idx_workspace_versions_session_no
ON workspace_versions(session_id, version_no);

CREATE INDEX idx_workspace_versions_session_created
ON workspace_versions(session_id, created_at DESC);
```

说明：

- `workspace_versions` 是用户可见修订历史。
- `session_states.changelog` 是业务审计变更记录。
- 二者可以关联同一个 `run_id`，但语义不同。

### 3.3 `session_states` 补充字段方向

现有 `session_states` 可继续保留 JSON 字段，但需要语义收敛：

```text
linked_entities_json      当前 session 关联业务实体
summary                   给 Agent 的业务上下文摘要
pending_approvals_json    待审批项，后续 HITL 用
changelog_json            业务事实变更历史
ui_snapshot_json          前端路由、选中实体、临时上下文
workflow_json             首页 workflow strip 的当前状态
workspace_intent          plan / project / material / analysis
version                   乐观锁
```

所有 mutation 必须经过：

```text
backend/app/services/session_state_mutation.py
```

业务 API 不允许绕过该服务直接写 `session_states`。

---

## 4. Backend 服务分工

### 4.1 `agent_session_service.py`

负责：

- 创建 / 列表 / 重命名 / 归档 session。
- 权限隔离。
- 新 session 初始化空 workspace 状态。

不负责：

- 执行 LLM。
- 解释 tool call。

### 4.2 `agent_message_service.py`

负责：

- 保存 user message。
- 保存 assistant visible message。
- 存储 text / thinking summary / tool_call display blocks / prompt_diff blocks。

不负责：

- 保存完整 SDK item。
- 保存生产完整 thinking.content。
- 作为业务审计事实源。

### 4.3 `agent_run_service.py`

负责：

- 创建 `agent_runs`。
- 幂等处理 `idempotency_key`。
- 同 session running/requires_action 直接返回 `409 SESSION_RUN_IN_PROGRESS`。
- 记录 status、usage、error。

不负责：

- 长期排队。
- 业务状态 mutation。

### 4.4 `workspace_service.py`

新增服务，负责首页右侧 Workspace 的产品状态：

- 读取当前 `workspace_drafts`。
- 根据 prompt/tool result 更新草稿。
- 创建 `workspace_versions`。
- 回溯某个 version。
- 生成 frontend 可直接渲染的 workspace projection。

建议接口：

```text
GET  /api/v1/agent/sessions/{session_id}/workspace
POST /api/v1/agent/sessions/{session_id}/workspace/versions/{version_id}/rollback
POST /api/v1/agent/sessions/{session_id}/workspace/save-draft
POST /api/v1/agent/sessions/{session_id}/workspace/validate
POST /api/v1/agent/sessions/{session_id}/workspace/publish
```

### 4.5 `business_context_builder.py`

负责给 Agent 每轮构建业务上下文：

```text
SessionState.summary
WorkspaceDraft 摘要
最近 N 条 changelog
当前 active version
ui_snapshot
linked business entities
```

这比把完整历史消息塞给 LLM 更稳定。

### 4.6 `side_effect_service.py`

负责把业务变化翻译成前端刷新信号：

```json
{
  "type": "side_effect",
  "run_id": "run_xxx",
  "effects": [
    {"target": "workspace", "action": "refresh"},
    {"target": "workspace_versions", "action": "append", "version_id": "v2"},
    {"target": "campaigns", "action": "refresh", "entity_id": "camp_xxx"}
  ]
}
```

---

## 5. Agent-Service 需要承接什么

### 5.1 只承接 runtime

Agent-service 负责：

```text
- 接收 backend 下发的 run_id / session_id / user_id / prompt
- 构造 Agent / tools / MCP client
- 调 OpenAI Agents SDK Runner.run_streamed
- 使用 SDK Session 作为 LLM replay cache
- 把 SDK stream events 转成 backend 可消费的 runtime events
- tool call 通过 backend business API 执行
```

Agent-service 不负责：

```text
- 创建产品 session
- 保存用户可见消息历史
- 保存 workspace draft/version
- 决定 session 归属和权限
- 保存业务 changelog
- 维护前端历史会话列表
```

### 5.2 Runtime API 入参

```json
{
  "run_id": "run_xxx",
  "session_id": "session_xxx",
  "user_id": "user_xxx",
  "prompt": "帮我创建 Candy Blast 美国 Meta 注册计划，日预算 800 美元，先跑 iOS。",
  "auth_token": "Bearer ...",
  "business_context_summary": "当前无已发布计划，当前草稿为空...",
  "workspace_snapshot": {
    "draft": {},
    "active_version_id": null,
    "workspace_intent": "plan"
  },
  "ui_snapshot": {
    "route": "/",
    "activePanel": "workspace",
    "selected_entities": {}
  },
  "sdk_session_mode": "sqlite"
}
```

### 5.3 Runtime events 输出

Agent-service 输出的是过程事件，不是产品事实：

```text
runtime.started
thinking.updated
message.updated
tool_call.started
tool_call.completed
workspace_delta.suggested
runtime.completed
runtime.error
runtime.cancelled
runtime.requires_action  # 后续 HITL 才启用
```

其中：

- `message.updated` 用于组装 assistant visible message。
- `tool_call.*` 用于前端过程展示，可脱敏裁剪。
- `workspace_delta.suggested` 只能作为建议，最终 workspace mutation 必须由 backend 服务确认并落库。
- `runtime.completed` 只代表 runtime 完成，不代表所有 business mutation 都已成功；backend 应以自身事务结果作为事实。

---

## 6. OpenAI Agents SDK 的使用边界

### 6.1 Session 只做 LLM replay cache

SDK `Session` 接口只有：

```text
get_items(limit)
add_items(items)
pop_item()
clear_session()
```

它适合保存 ResponseInputItem / tool call replay items，让多轮对话不用手动拼 `to_input_list()`。

它不适合保存：

```text
用户会话元数据
workspace draft
workspace version
业务实体状态
changelog
权限归属
审计日志
```

### 6.2 RunResult / new_items 可用于 runtime 解释

SDK `RunResult` / `RunResultStreaming` 提供：

```text
final_output
new_items
raw_responses
last_agent
last_response_id
interruptions
to_state()
usage via context_wrapper
```

其中 `new_items` 适合转换成：

```text
message block
tool_call display block
reasoning summary block
runtime event log
```

但不能直接作为 Workspace 事实源。

### 6.3 Streaming 必须完整 drain

SDK 文档明确：

```text
stream_events() 结束前，run 不算完成。
最后一个可见 token 后，SDK 可能还在做 session persistence / approval bookkeeping / compaction。
```

所以 backend gateway 必须：

- 持续消费到 stream iterator 完成。
- 再标记 run completed/error/cancelled。
- 再写 assistant message / usage / final runtime state。

### 6.4 HITL / RunState 后置

SDK 的 HITL 能力完整，但首期不建议承接首页终态时就引入 `RunState` 持久化。

原因：

- 当前首页核心是草稿、版本、校验、发布，不是长时间挂起恢复。
- RunState 会携带 agent graph、tool schema、context、trace 等 runtime 细节。
- 版本升级和工具变更后恢复复杂。

首期只保留字段和事件位：

```text
runtime.requires_action
pending_approvals_json
```

真正需要时再做 HITL MVP。

---

## 7. 首页关键链路如何落地

### 7.1 新任务空态 -> 第一轮 prompt

```text
Frontend
  POST /api/v1/agent/sessions         # 可显式创建，也可 run 时自动创建
  POST /api/v1/agent/runs
    {session_id, prompt, context_snapshot, idempotency_key}

Backend
  写 user message
  创建 agent_run queued/running
  初始化 workspace_draft
  构建 business_context_summary
  调 agent-service runtime

Agent Service
  调 Runner.run_streamed
  stream message/tool events
  tool call 调 backend business/workspace API

Backend
  聚合 assistant message
  更新 workspace_draft
  创建 workspace_version V1
  写 session_state changelog/workflow
  SSE side_effect 通知前端刷新 workspace
```

### 7.2 用户继续改参数

```text
用户：预算改到 1200，补充两个素材变体

Backend
  写新 user message
  创建 run
  business_context_summary 包含当前 draft + active V1

Agent Service
  识别变更意图
  可调用 update_workspace_draft tool

Backend workspace_service
  更新 draft
  创建 V2
  写 changes: ["预算 $1200", "素材补充变体"]
  返回 side_effect: workspace refresh + version append
```

### 7.3 回溯修订版本

回溯不应该交给 LLM 做。它是确定性产品操作：

```text
Frontend
  POST /workspace/versions/{version_id}/rollback

Backend
  校验 session/user
  读取 version snapshot
  覆盖 workspace_draft.content_json
  设置 active_version_id
  写 changelog: workspace.rollback
  可写一条 assistant system visible message: 已回溯到 Vx
  返回最新 workspace projection
```

### 7.4 保存草稿 / 发布校验 / 发布

这些也不应该依赖 LLM：

```text
保存草稿：workspace_draft.status = draft_saved
发布校验：backend validator 产生 validation checks
发布：backend business API / external platform API 执行，成功后写 business DB + changelog
```

Agent 可以建议或触发，但最终必须由 backend 服务执行并落库。

---

## 8. API Projection 建议

首页打开 session 时，前端需要一次性拿到可恢复视图：

```text
GET /api/v1/agent/sessions/{session_id}/home
```

返回：

```json
{
  "session": {
    "session_id": "session_xxx",
    "title": "Candy Blast 注册",
    "status": "active"
  },
  "messages": [],
  "workspace": {
    "mode": "active",
    "intent": "plan",
    "draft": {},
    "active_version_id": "v2",
    "versions": [],
    "workflow": {
      "current_step": "validation_required",
      "steps": [
        {"key": "prompt_parsed", "label": "Prompt 解析", "status": "done"},
        {"key": "draft_ready", "label": "SaaS 草稿", "status": "done"},
        {"key": "validation", "label": "发布校验", "status": "warn"},
        {"key": "sync", "label": "同步平台", "status": "pending"}
      ]
    },
    "context_cards": []
  }
}
```

这样前端不需要从 messages 里反推 workspace。

---

## 9. 与昨天 refactor 手册的关系

昨天的 `260623_agent_session_run_refactor_dev_manual.md` 解决的是：

```text
产品事实源从 agent-service 迁到 backend
Task 降级 Run
SDK Session 降级 replay cache
```

今天这份文档补齐的是：

```text
首页 Workspace 终态需要哪些产品事实
这些事实如何由 backend 维护
agent-service runtime 如何只负责生成和执行
前端如何从 backend projection 恢复设计稿状态
```

二者关系：

```text
260623 文档 = 底层边界和迁移顺序
260624 文档 = 首页终态产品状态承接模型
```

---

## 10. 首期实现边界

为了保证当前已调试能力不受影响，首期建议只做这些：

```text
必须做：
1. backend agent_sessions / agent_messages / agent_runs
2. backend workspace_drafts / workspace_versions
3. backend session_states 的 workflow_json / workspace_intent 语义
4. backend home projection API
5. backend run gateway 聚合 assistant message + side_effect
6. agent-service runtime API 瘦身，不再保存产品 session/task
7. SDK SQLiteSession 保留为 LLM replay cache

暂不做：
1. Act DAG
2. run queue
3. RunState 持久化 resume
4. 完整 HITL
5. BackendSession 通过 HTTP 承接 SDK items
6. 从 agent_messages 反推 workspace
7. 生产长期保存完整 thinking.content
```

---

## 11. 最小验收标准

首页终态承接的首期验收，不是“Agent 多聪明”，而是状态闭环正确：

```text
1. 新任务空态发 prompt 后，页面进入 active。
2. session 列表出现新会话。
3. 刷新页面后，messages + workspace draft + versions 能恢复。
4. 第二轮改预算/素材后，workspace draft 更新，version +1。
5. 点击历史 version rollback 后，draft 回到对应快照。
6. 发布校验结果进入 workflow 和 validation checks。
7. agent-service 重启不影响历史会话和 workspace。
8. 清空 SDK Session cache 不影响 backend home projection。
9. 同 session 并发 run 返回 409，不重复更新 draft/version。
10. 相同 idempotency_key 重试不重复创建 run/version/business mutation。
```

---

## 12. 最重要的设计约束

```text
1. Workspace 不是消息回放结果，而是 backend projection。
2. Workspace Version 不是 Run，也不是 Changelog。
3. tool_call 是用户可见过程，changelog 是业务事实审计。
4. Agent 可以建议 workspace_delta，但 backend 才能确认 mutation。
5. SDK Session 只为 LLM 记忆服务，可以清空、裁剪、compaction。
6. 回溯、保存、校验、发布优先走确定性 backend 服务，不交给 LLM 猜。
7. 首期先保住现有 chat/run/tool 能力，再逐步接入 workspace projection。
```

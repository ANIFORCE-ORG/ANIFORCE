# ANIFORCE Agent 开发手册

**性质**：开发交付物 + E2E 验证一体。改一个 Block，测一个 Block。
**依据**：`/workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE/AGENTS.md`（架构设计与 SDK 协议）
**原则**：真实生产场景，不造假数据；每个 Block = 一个交付物。

---

## 总览

| Block | 交付物 | 状态 | 脚本 |
|-------|--------|------|------|
| 1 | 基础连通性 + JWT(sub) | ✅ 通过 | `block1_basic_connectivity.py` |
| 2 | Claude SDK 调通（最小闭环） | ✅ SDK 调通 | `block2_claude_sdk.py` |
| 3 | AG-UI 适配层 | ✅ 核心通过 | （探针 05/06） |
| 4 | SDK 集成（Sandbox + Skill） | ⏸️ 待开发 | `block4_sdk_integration.py` |
| 5 | MCP 工具接 backend | ⏸️ 待开发 | `block5_mcp_tools.py` |
| 6 | 前端 Action + 共享状态 | ⏸️ 待前端 | `block6_frontend_action.py` |
| 7 | 多租户隔离 | ⏸️ 待重测 | `block7_multi_tenant.py` |
| 8 | 对话历史 + resume | ⏸️ 待开发 | `block8_history_resume.py` |

**执行顺序**：1 → 2 → 3 → 4 → 5 → 7 → 8 → 6（6 依赖前端，最后做）

---

## 环境准备

### 启动 agent 服务

```bash
cd /workspace/nas-data/huya_projects/OpenAgents/projects/ANIFORCE/aniforce-agent
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8020
```

### 环境变量（.env）

```bash
ANTHROPIC_API_KEY=sk-xxx
ANTHROPIC_AUTH_TOKEN=sk-xxx          # Claude SDK 需要，与 API_KEY 一致
ANTHROPIC_BASE_URL=https://copilot.huya.info/api/anthropic
CLAUDE_AGENT_MODEL=claude-sonnet-4-6
JWT_SECRET=xxx
BACKEND_URL=http://localhost:18003
TASK_DB_PATH=runtime/agent/tasks.db
SESSION_DB_PATH=runtime/agent/sessions.db
RUNTIME_DIR=runtime/sessions
SKILLS_SOURCE_DIR=app/skills
```

⚠️ 测试时注意 shell 环境污染（见 AGENTS.md「配置污染排查记录」）。
验证 .env 纯净的方法：
```bash
env -i HOME=$HOME PATH="...:.venv/bin" bash -c \
  'cd aniforce-agent && .venv/bin/python -c "from app.config.settings import get_settings; s=get_settings(); print(s.ANTHROPIC_BASE_URL)"'
```

### 生产对齐标准

- JWT Token 用后端格式：`{"sub": user_id, "email": ..., "name": ..., "exp": ...}`
- Session ID 必须是标准 UUID（Claude SDK 强制）
- Claude SDK 调用必须 `CLAUDE_CONFIG_DIR` 隔离 + 显式 `env` 只带 `ANTHROPIC_*`/`CLAUDE_*`
- 详见 AGENTS.md「E2E 测试标准」

---

## Block 1: 基础连通性 + JWT(sub)

**交付物**：FastAPI 服务 + JWT 认证中间件（对齐后端 `sub` 字段）
**状态**：✅ 通过（2026-06-17）

### 执行
```bash
.venv/bin/python tests/e2e/block1_basic_connectivity.py
```

### 验证点
- [ ] `GET /health` 返回 200
- [ ] `GET /api/agent/copilotkit/info` 返回 Agent 列表
- [ ] 无 Token 请求返回 401
- [ ] 带 Token（`sub` 字段）可创建任务
- [ ] `runtime/agent/tasks.db` 存在可读

### 已修复问题
1. JWT 中间件改用 `sub` 字段（JWT RFC 7519 标准），不再兼容 `user_id`
2. Settings 补齐 `ANTHROPIC_AUTH_TOKEN`/`ANTHROPIC_BASE_URL`/`CLAUDE_AGENT_MODEL`/`SKILL_SOURCE_DIR` 字段
3. 删除 `.bashrc` 中 covs 插件污染配置

---

## Block 2: Claude SDK 调通（最小闭环）

**交付物**：agent 服务能通过 Claude SDK 返回真实文本（不涉及 AG-UI 翻译）
**目的**：隔离 SDK 调用问题与适配层问题。Block 2 失败 = SDK/配置问题，不是适配问题。
**状态**：✅ SDK 调通（2026-06-17）
  - SDK 不再 api_retry，Session Store 有数据，SSE 有响应
  - 剩余「空文本」问题属于 Block 3 适配层，不属于 Block 2

### 前置
- Block 1 通过
- `.env` 配置正确（copilot_sonnet profile 验证可用）
- `runtime.py` 的 `_build_options` 已修复（env 隔离 + CLAUDE_CONFIG_DIR）

### 最小 query 验证（已通过）
探针：`drafts/260617/260617_03_learn_manual_style.py`
```bash
env -i HOME=$HOME PATH="...:.venv/bin" bash -c \
  'cd aniforce-agent && .venv/bin/python ../drafts/260617/260617_03_learn_manual_style.py'
```
预期：3 条消息（SystemMessage(init) / AssistantMessage(TextBlock) / ResultMessage(success)）

### HTTP 接口验证（已通过）
探针：`drafts/260617/260617_05_sse_format_probe.py`
- `POST /api/agent/copilotkit/agent/default/run` 返回 200
- SSE 有完整事件流（TEXT_MESSAGE_START/END/RUN_FINISHED）
- SDK 调用链路通畅，Session Store 落盘
- ⚠️ 当前 TEXT_MESSAGE_START 与 END 之间无 CONTENT（适配层未翻译 StreamEvent，属 Block 3）

### 验证点
- [x] 最小 query 探针返回 3 条消息，ResultMessage.subtype=success
- [x] AssistantMessage.content 含 TextBlock 且 text 非空
- [x] init.apiKeySource=none（走 AUTH_TOKEN 代理，正常）
- [x] HTTP 接口返回 200 + SSE 事件流
- [x] 无 api_retry 连续重试
- [x] Session Store 落盘（sessions.db 有记录）

### 已修复（本次）
`app/agent/runtime.py` `_build_options` 三处缺陷已修复：
1. `env` 从 `**os.environ` 全量展开 → 改为只带 `ANTHROPIC_*`/`CLAUDE_*` 前缀
2. 新增 `CLAUDE_CONFIG_DIR` 隔离（session 目录下 `.claude_config/`），避免本机 hooks 污染
3. 新增 `CLAUDE_AGENT_SDK_CLIENT_APP=aniforce-agent/1.0`

### 失败诊断
- `api_retry` 连续 6 次 → 检查 CLAUDE_CONFIG_DIR 是否隔离（本机 hooks 污染）
- `Invalid session ID` → threadId 必须是 UUID
- 401 → 检查 ANTHROPIC_AUTH_TOKEN 是否正确传递

---

## Block 3: AG-UI 适配层

**交付物**：`copilotkit_adapter.py` 重写，Claude SDK 消息流 → 标准 AG-UI 事件
**这是落地顺序第 1 步，最关键的交付物。**
**状态**：✅ 核心通过（2026-06-17）
  - 纯文本场景：RunStarted → TextMessageStart → Content×N → End → RunFinished
  - 工具调用场景：ActionExecutionStart/Args/End/Result + 文本流
  - 事件名全部对齐 CopilotKit 标准

### 执行
```bash
# 纯文本探针
.venv/bin/python ../drafts/260617/260617_05_sse_format_probe.py
# 工具调用探针
.venv/bin/python ../drafts/260617/260617_06_sse_tool_probe.py
```

### 依据
AGENTS.md「Claude SDK 消息 → AG-UI 事件 映射表」。事件名对齐 CopilotKit sdk-python `protocol.py`：
- `TextMessageStart/Content/End`（PascalCase 字符串值）
- `ActionExecutionStart/Args/End/Result`
- `RunStarted/RunFinished/RunError`

### 已实现
1. **StreamEvent 处理**（核心修复空文本）：content_block_start/delta/stop → TextMessage 三件套
2. **二选一策略**：消费 StreamEvent 推增量，AssistantMessage 只捕 ToolUseBlock（不重复推文本）
3. **工具调用映射**：ToolUseBlock → ActionExecutionStart/Args；ToolResultBlock → ActionExecutionEnd/Result
4. **生命周期**：RunStarted（开头）/ RunFinished（成功）/ RunError（失败）
5. **SystemMessage 进日志**不发前端（init/api_retry/thinking_tokens）
6. **ResultMessage 终态**：is_error=True → RunError，否则 RunFinished

### 验证点
- [x] 事件名全部对齐 CopilotKit 标准（PascalCase）
- [x] 文本增量正确（逐 chunk，不重复）
- [x] actionExecutionId = tool_use.id（前后端能关联）
- [x] 流式选择：用 StreamEvent 推增量，忽略完整 AssistantMessage（不重复）
- [x] SystemMessage 不发前端，进日志
- [x] ThinkingBlock 默认不发前端
- [x] 纯文本场景完整链路（探针 05）
- [x] 工具调用场景完整链路（探针 06）

### 待优化（非阻塞，后续 Block 处理）
1. `ActionExecutionResult.actionName` 为空 —— UserMessage 不带工具名，需建 tool_use_id→name 映射
2. 工具参数增量 `input_json_delta` 未推前端（当前由 AssistantMessage 一次性发 Args）
3. ThinkingBlock 未发 `MetaEvent`（调试面板用，暂不需要）
4. 业务信息（cost/usage/turns）目前只进日志，未写 backend DB（Block 8 处理）
5. 适配层收到 ResultMessage 后 `return` 提前结束，触发 SDK 内部 `aclose(): asynchronous generator is already running` warning（数据流探针 07 观察到）。功能正常，待优化关闭生成器的顺序

### 信号源
- SDK 协议 dump：`drafts/260615_claude_sdk_learning/outputs/260617_04_protocol_dump_{text,tool,stream}.json`
- 事件类型定义：`resources/CopilotKit/sdk-python/copilotkit/protocol.py`

---

## Block 4: SDK 集成（Sandbox + Skill）

**交付物**：Sandbox 隔离 + Skill 动态注入在真实 Agent 会话中生效
**说明**：Sandbox/Skill 是 SDK options 配置项，合并测，不再当独立模块。
**状态**：⏸️ 待开发（合并旧 Block 3+4）

### 执行
```bash
.venv/bin/python tests/e2e/block4_sdk_integration.py
```

### 测试内容
1. **Sandbox 隔离**
   - Session 目录自动创建在 `runtime/sessions/{uuid}/`
   - 不同 Session 写同名文件不冲突
   - ClaudeAgentOptions.cwd 指向 session 目录
   - Session 清理后目录删除，不影响其他 Session
2. **Skill 动态注入**
   - Skill 从 `app/skills/` 复制到 `{session_dir}/.claude/skills/`
   - Agent 能识别并使用 Skill
   - 不同 Session 的 Skill 相互独立

### 验证点
- [ ] 发起对话后 `runtime/sessions/{uuid}/` 自动创建
- [ ] Agent 在 cwd 内操作文件，不越界
- [ ] Skill 复制路径正确
- [ ] Agent 回复能体现 Skill 内容（如用了 Skill 里的知识）
- [ ] Session 清理生效

---

## Block 5: MCP 工具接 backend

**交付物**：Agent 通过 MCP 调 backend API（projects/campaigns/materials），JWT 透传
**状态**：⏸️ 待开发（依赖 Block 3 适配层）

### 前置
- backend 服务运行（18003）
- Block 3 适配层完成（工具调用走 ActionExecution* 事件）

### 执行
```bash
.venv/bin/python tests/e2e/block5_mcp_tools.py
```

### 测试内容
1. **MCP 配置**：`create_backend_mcp_servers` 正确生成 HTTP MCP 配置
2. **工具调用**：Agent 调 list_projects / create_project 等后端工具
3. **JWT 透传**：后端收到的请求头含正确 JWT，能解析 user_id
4. **事件暴露**：工具调用通过 ActionExecution* 事件推给前端

### 验证点
- [ ] `ClaudeAgentOptions.mcp_servers` 含 backend 配置
- [ ] Agent 决策调用后端工具（不是自己编答案）
- [ ] 后端日志显示 JWT 中的 user_id 正确
- [ ] ActionExecutionResult 含真实工具结果
- [ ] Agent 基于工具结果生成回复

---

## Block 6: 前端 Action + 共享状态

**交付物**：方案 B 两机制——Agent 感知前端上下文 + 操作 UI
**状态**：⏸️ 待前端就位（先占位，不写脚本）

### 机制 1：共享状态（AgentStateMessage）
前端推送上下文，Agent 感知：
```json
{
  "current_project_id": "proj_123",
  "current_view": "campaign_list",
  "selected_campaign_ids": ["camp_a", "camp_b"]
}
```

### 机制 2：前端 Action（ActionExecution* 反向）
前端注册 UI action，Agent 调用：
- `navigate_to(view, id)` - 跳页面
- `highlight_campaign(id)` - 高亮计划
- `open_create_dialog(type)` - 打开创建弹窗
- `prefill_form(data)` - 预填表单

### 验证点（待前端就位后补）
- [ ] 前端状态变化能同步到 Agent
- [ ] Agent 能调用前端 action 触发 UI 变化
- [ ] 前端 action 返回结果能被 Agent 使用
- [ ] HITL 确认流程闭环

---

## Block 7: 多租户隔离

**交付物**：不同用户的数据/Session/对话完全隔离
**状态**：⏸️ 待重测（旧脚本保留，事件名待对齐）

### 执行
```bash
.venv/bin/python tests/e2e/block7_multi_tenant.py
```

### 验证点
- [ ] User B 无法访问 User A 的任务（API 403/404）
- [ ] 数据库查询都带 user_id 过滤
- [ ] Session 目录按 session_id 隔离
- [ ] 对话内容不泄露（User B 不知道 User A 的对话）
- [ ] MCP 工具调用带正确 JWT（后端按 user_id 过滤）

---

## Block 8: 对话历史 + resume

**交付物**：SDK session 为主，backend 存业务元数据，agent 重启可 resume
**状态**：⏸️ 待开发（依赖 Block 2/3/7）

### 依据
AGENTS.md「对话历史归属决策」：
- session.db（agent 本地 SQLite）= 对话原文真相源
- backend DB = 业务元数据 + 索引
- session_id = threadId = UUID

### 测试内容
1. **Session 持久化**：对话后 session.db 有记录
2. **多轮上下文**：同 session_id 多轮对话，Agent 记得上文
3. **Agent 重启 resume**：杀掉 client 实例，用同 session_id 恢复，上下文仍在
4. **业务元数据**：backend agent_task 表记录 task_id↔session_id↔user_id↔title

### 验证点
- [ ] `sessions.db` 按 session_id 存对话条目
- [ ] 同 session_id 多轮 query 上下文保持
- [ ] client 实例销毁后重建，session_id 不变即可 resume
- [ ] backend agent_task 表有完整业务索引
- [ ] backend 不重放历史给 SDK（不拼 prompt）

---

## 故障排查速查

| 现象 | 根因 | 排查 |
|------|------|------|
| api_retry 连续 6 次 | CLAUDE_CONFIG_DIR 未隔离，本机 hooks 污染 | 检查 `_build_options` 的 env |
| Invalid session ID | threadId 非 UUID | 测试脚本用 `uuid.uuid4()` |
| 401 无效令牌 | AUTH_TOKEN 未传或被 shell 污染 | `env -i` 验证 .env 纯净 |
| 空响应 | 适配层没翻译消息类型 | 对照 SDK 协议 dump 检查映射 |
| no active connection | 流式生成器内 DB 连接关闭 | 在生成器内重建连接 |
| 上下文丢失 | session_id 不一致或未用 Client | 确认 threadId 贯穿 + 用 ClaudeSDKClient |

---

## 维护规则

- 改一个 Block 代码 → 立刻跑对应 Block 测试 → 更新本手册状态
- 新增交付物 → 在总览表加行
- 状态变更：⏸️待开发 / 🔧开发中 / ⚠️部分 / ✅通过 / ❌失败
- 每个 Block 的「已修复问题」「失败诊断」要持续累积
- 详细架构依据查 `AGENTS.md`，本手册只记 Block 级执行

---

**最后更新**：2026-06-17
**测试标准**：真实生产场景，不造假数据

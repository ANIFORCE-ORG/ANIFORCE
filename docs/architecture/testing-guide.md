# ANIFORCE Agent 服务测试手册

## 目标

系统验证 ANIFORCE Agent 服务的核心功能，确保所有模块符合设计目标。本手册参考 `drafts/260615_claude_sdk_learning/study_notes.md` 的格式，每个测试都有完整的验证脚本、预期输出和实际结果。

## 测试原则

- **独立性**：每个测试独立运行，互不依赖
- **可复现**：所有测试可重复执行，结果一致
- **完整性**：覆盖核心功能的所有关键路径
- **真实性**：使用真实 Claude API（需要 API Key）和真实数据库
- **可追溯**：每个测试输出保存到 `tests/outputs/`，便于事后审查

## 测试路线

### Phase 1：基础架构测试（无需 API Key）
1. ✅ SQLite 数据库初始化
2. ✅ JWT 认证与权限过滤
3. ✅ Repository 层数据隔离
4. ✅ Session Store 持久化
5. ✅ Skill Manager 动态注入
6. ✅ Sandbox 目录隔离

### Phase 2：Agent Runtime 集成测试（需要 API Key）
7. ⏳ ClaudeSDKClient 实例池管理
8. ⏳ Session 持久化与恢复
9. ⏳ 流式输出（include_partial_messages）
10. ⏳ 多轮对话上下文保持

### Phase 3：HTTP MCP 集成测试（需要后端服务）
11. ⏳ HTTP MCP 配置正确性
12. ⏳ JWT Token 透传
13. ⏳ 后端工具调用完整链路
14. ⏳ 工具调用结果映射

### Phase 4：CopilotKit 协议测试（需要 API Key）
15. ⏳ AG-UI 事件映射
16. ⏳ SSE 流式推送
17. ⏳ 工具调用事件完整性
18. ⏳ 错误处理与兜底

### Phase 5：端到端测试（完整功能）
19. ⏳ 用户完整对话流程
20. ⏳ 多租户并发隔离
21. ⏳ 任务取消与清理
22. ⏳ 性能与资源占用

## 测试环境准备

### 1. 环境变量配置

创建 `aniforce-agent/.env.test`：

```bash
# 基础配置
DEBUG=true
PORT=8020

# 数据库（测试专用）
TASK_DB_PATH=tests/outputs/test_tasks.db
SESSION_DB_PATH=tests/outputs/test_sessions.db

# JWT（与生产环境一致）
JWT_SECRET=test-secret-key-for-agent-service
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Claude API（需要真实 Key）
ANTHROPIC_API_KEY=sk-ant-xxxxx  # 替换为真实 Key

# 后端服务（测试时可选）
BACKEND_URL=http://localhost:8010
INTERNAL_TOKEN=test-internal-token

# CORS
CORS_ALLOW_ORIGINS=*

# 运行时目录
RUNTIME_DIR=tests/runtime/sessions
SKILL_SOURCE_DIR=app/skills
```

### 2. 创建测试输出目录

```bash
mkdir -p aniforce-agent/tests/outputs
mkdir -p aniforce-agent/tests/runtime/sessions
```

### 3. 初始化测试数据库

```bash
cd aniforce-agent
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python -c "
from app.config.database import init_task_db
import asyncio
asyncio.run(init_task_db())
"
```

---

## Phase 1：基础架构测试（无需 API Key）

### 测试 1.1：SQLite 数据库初始化

**目标**：验证 Task 和 Event 表结构正确创建

**测试脚本**：`tests/test_01_database_init.py`（已存在，即 `tests/test_repositories.py` 部分）

**运行命令**：
```bash
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python pytest tests/test_repositories.py -v
```

**预期输出**：
```
tests/test_repositories.py::test_task_create_and_get PASSED
tests/test_repositories.py::test_task_permission_filter PASSED
tests/test_repositories.py::test_event_append_and_list PASSED
tests/test_repositories.py::test_event_after_sequence PASSED
```

**已验证**：✅ 全部通过
- 任务可正常创建和查询
- 权限过滤正常（user_id 隔离）
- 事件可按序追加
- 事件断点续传（after_sequence）正常

---

### 测试 1.2：JWT 认证与权限过滤

**目标**：验证 JWT Token 创建、解析和多租户隔离

**测试脚本**：`tests/test_auth.py`（已存在）

**运行命令**：
```bash
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python pytest tests/test_auth.py -v
```

**预期输出**：
```
tests/test_auth.py::test_create_and_decode_token PASSED
tests/test_auth.py::test_decode_invalid_token PASSED
tests/test_auth.py::test_decode_expired_token PASSED
```

**已验证**：✅ 全部通过
- Token 可正常创建和解析
- 无效 Token 正确抛出 AuthError
- 过期 Token 正确拒绝

---

### 测试 1.3：多租户数据隔离

**目标**：验证不同用户数据完全隔离

**测试脚本**：`tests/test_e2e.py::test_multi_tenant_isolation`（已存在）

**运行命令**：
```bash
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python pytest tests/test_e2e.py::test_multi_tenant_isolation -v
```

**预期输出**：
```
tests/test_e2e.py::test_multi_tenant_isolation PASSED
```

**已验证**：✅ 通过
- 用户 A 只能看到自己的任务
- 用户 B 只能看到自己的任务
- 用户 A 无法获取用户 B 的任务详情
- 用户 B 无法获取用户 A 的任务详情

---

### 测试 1.4：Session Store 持久化

**目标**：验证 SQLiteSessionStore 可正常读写

**测试脚本**：`tests/test_agent_integration.py::test_session_store_basic`（已存在）

**运行命令**：
```bash
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python pytest tests/test_agent_integration.py::test_session_store_basic -v
```

**预期输出**：
```
tests/test_agent_integration.py::test_session_store_basic PASSED
```

**已验证**：✅ 通过
- Session 条目可追加
- Session 条目可按 key 加载
- 数据库表结构正确

---

### 测试 1.5：Skill Manager 动态注入

**目标**：验证 Skills 可动态复制到会话目录

**测试脚本**：`tests/test_agent_integration.py::test_skill_manager_basic`（已存在）

**运行命令**：
```bash
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python pytest tests/test_agent_integration.py::test_skill_manager_basic -v
```

**预期输出**：
```
tests/test_agent_integration.py::test_skill_manager_basic PASSED
```

**已验证**：✅ 通过
- Skills 可从源目录复制到会话目录
- 目录结构正确（`.claude/skills/{skill-name}/SKILL.md`）

---

### 测试 1.6：Sandbox 目录隔离

**目标**：验证每个会话有独立的工作目录

**测试脚本**：`tests/test_agent_integration.py::test_sandbox_manager_basic`（已存在）

**运行命令**：
```bash
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python pytest tests/test_agent_integration.py::test_sandbox_manager_basic -v
```

**预期输出**：
```
tests/test_agent_integration.py::test_sandbox_manager_basic PASSED
```

**已验证**：✅ 通过
- 会话目录可正常创建
- 不同会话目录相互独立
- 目录清理正常

---

## Phase 1 总结

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 数据库初始化 | ✅ | 表结构正确，读写正常 |
| JWT 认证 | ✅ | Token 创建/解析/校验正常 |
| 多租户隔离 | ✅ | 用户数据完全隔离 |
| Session Store | ✅ | 持久化读写正常 |
| Skill Manager | ✅ | 动态注入正常 |
| Sandbox 隔离 | ✅ | 目录独立，清理正常 |

**Phase 1 结论**：基础架构完善，所有单元测试通过，可进入 Phase 2。

---

## Phase 2：Agent Runtime 集成测试（需要 API Key）

⚠️ **重要**：以下测试需要真实 Claude API Key，会产生实际费用。

### 测试 2.1：ClaudeSDKClient 实例池管理

**目标**：验证 Client 实例正确创建、复用和清理

**测试脚本**：`tests/integration/test_02_01_client_pool.py`（待创建）

**核心验证点**：
1. 同一 session_id 两次调用，复用同一 Client 实例
2. 不同 session_id，创建不同 Client 实例
3. disconnect_client 后，实例从池中移除
4. cleanup_all 清理所有实例

**实现状态**：⏳ 待创建

---

### 测试 2.2：Session 持久化与恢复

**目标**：验证 Session 数据可持久化并在重启后恢复

**测试脚本**：`tests/integration/test_02_02_session_persistence.py`（待创建）

**核心验证点**：
1. 第一轮对话后，Session 数据写入 SQLite
2. 断开 Client，模拟服务重启
3. 重新创建 Client（相同 session_id）
4. 第二轮对话可获取第一轮上下文

**实现状态**：⏳ 待创建

---

### 测试 2.3：流式输出（include_partial_messages）

**目标**：验证 `include_partial_messages=True` 后可接收增量文本块

**测试脚本**：`tests/integration/test_02_03_streaming_output.py`（待创建）

**核心验证点**：
1. 接收到 `StreamEvent` 类型消息
2. `content_block_delta` 事件包含增量文本
3. 文本块按序拼接可还原完整响应
4. 流式事件数量 > 1（不是单一完整块）

**实现状态**：⏳ 待创建

---

### 测试 2.4：多轮对话上下文保持

**目标**：验证同一 Client 实例内多轮对话共享上下文

**测试脚本**：`tests/integration/test_02_04_multi_turn_context.py`（待创建）

**核心验证点**：
1. 第一轮：告知"France 的首都是 Paris"
2. 第二轮：问"我上一条消息提到的城市是什么"
3. 模型回答"Paris"（证明记得上下文）
4. 两轮 session_id 相同

**参考**：学习手册第 5 章验证结论

**实现状态**：⏳ 待创建

---

## Phase 2 总结

⏳ **待完成**：需创建 4 个集成测试脚本并验证。

---

## Phase 3：HTTP MCP 集成测试（需要后端服务）

⚠️ **重要**：以下测试需要后端服务运行在 `http://localhost:8010`。

### 测试 3.1：HTTP MCP 配置正确性

**目标**：验证 MCP 配置格式符合 Claude SDK 要求

**测试脚本**：`tests/integration/test_03_01_mcp_config.py`（待创建）

**核心验证点**：
1. `create_backend_mcp_servers` 返回正确格式
2. 配置包含 `command: http`
3. 配置包含正确的 `args`（后端 URL）
4. 配置包含正确的 `env.HTTP_HEADERS`（JWT + Internal Token）

**实现状态**：⏳ 待创建

---

### 测试 3.2：JWT Token 透传

**目标**：验证 JWT Token 正确传递到后端服务

**测试脚本**：`tests/integration/test_03_02_jwt_passthrough.py`（待创建）

**核心验证点**：
1. Context 中存储正确的 JWT Token
2. MCP 请求头包含 `Authorization: Bearer <token>`
3. 后端服务可解析 Token 获取 user_id
4. 后端返回数据符合当前用户权限

**实现状态**：⏳ 待创建

---

### 测试 3.3：后端工具调用完整链路

**目标**：验证 Agent 可通过 MCP 调用后端工具

**测试脚本**：`tests/integration/test_03_03_tool_call_e2e.py`（待创建）

**核心验证点**：
1. Agent 接收 prompt："列出我的所有项目"
2. Agent 调用 `list_projects` 工具
3. 后端返回项目列表
4. Agent 整合结果并返回给用户
5. 完整消息流包含 `ToolUseBlock` 和 `ToolResultBlock`

**实现状态**：⏳ 待创建

---

### 测试 3.4：工具调用结果映射

**目标**：验证后端工具结果正确映射为 AG-UI 事件

**测试脚本**：`tests/integration/test_03_04_tool_result_mapping.py`（待创建）

**核心验证点**：
1. `TOOL_CALL_START` 事件包含工具名称
2. `TOOL_CALL_ARGS` 事件包含工具参数
3. `TOOL_CALL_RESULT` 事件包含工具返回值
4. 事件顺序正确（START → ARGS → RESULT）

**实现状态**：⏳ 待创建

---

## Phase 3 总结

⏳ **待完成**：需创建 4 个 MCP 集成测试脚本并验证。

---

## Phase 4：CopilotKit 协议测试（需要 API Key）

### 测试 4.1：AG-UI 事件映射

**目标**：验证 Claude SDK 消息正确转换为 AG-UI 事件

**测试脚本**：`tests/integration/test_04_01_ag_ui_mapping.py`（待创建）

**核心验证点**：
1. `AssistantMessage` → TEXT_MESSAGE_START/CONTENT/END
2. `ToolUseBlock` → TOOL_CALL_START/ARGS
3. `ToolResultBlock` → TOOL_CALL_RESULT
4. `ResultMessage` → RUN_FINISHED

**实现状态**：⏳ 待创建

---

### 测试 4.2：SSE 流式推送

**目标**：验证 SSE 格式正确，前端可正常解析

**测试脚本**：`tests/integration/test_04_02_sse_streaming.py`（待创建）

**核心验证点**：
1. 每个事件格式：`event: TYPE\ndata: JSON\n\n`
2. JSON 数据可正常解析
3. 事件按序推送，无丢失
4. 最后一个事件是 `RUN_FINISHED`

**实现状态**：⏳ 待创建

---

## Phase 4 总结

⏳ **待完成**：需创建 2 个 CopilotKit 协议测试脚本并验证。

---

## Phase 5：端到端测试（完整功能）

### 测试 5.1：用户完整对话流程

**目标**：模拟真实用户从登录到对话完成的完整流程

**测试脚本**：`tests/integration/test_05_01_full_conversation.py`（待创建）

**核心验证点**：
1. 创建 JWT Token
2. 调用 `/api/agent/copilotkit/agent/default/run`
3. 接收 SSE 流式事件
4. 解析事件并验证完整性
5. 任务状态正确（PENDING → RUNNING → COMPLETED）

**实现状态**：⏳ 待创建

---

## 测试总结

| Phase | 已完成 | 待完成 | 总计 |
|-------|--------|--------|------|
| Phase 1 基础架构 | 6 | 0 | 6 |
| Phase 2 Agent Runtime | 0 | 4 | 4 |
| Phase 3 HTTP MCP | 0 | 4 | 4 |
| Phase 4 CopilotKit | 0 | 2 | 2 |
| Phase 5 端到端 | 0 | 1 | 1 |
| **总计** | **6** | **11** | **17** |

**当前进度**：6/17（35%）

**下一步**：创建 Phase 2 集成测试脚本，验证 ClaudeSDKClient 核心功能。

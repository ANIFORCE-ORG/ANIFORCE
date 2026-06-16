# Claude Agent Service Migration Design

## 目标

将 ANIFORCE 当前内嵌在后端中的 agent 能力迁移为可独立部署的 `agent-service/` 子项目。迁移后，现有 `backend/` 继续负责鉴权、用户/组织上下文、session 管理、task 系统和业务数据访问；新 `agent-service/` 负责 Claude Agent SDK 运行时、对话编排、工具适配和流式事件输出；前端对话承接逐步切换到 CopilotKit 组件与 AG-UI 事件模型。

第一阶段目标是跑通最小闭环：用户在前端发送消息，当前后端完成鉴权并创建/维护 task，然后调用独立 agent-service 执行，agent-service 返回事件流，后端转成前端可消费的 AG-UI/CopilotKit 流。

## 设计原则

- 分离部署优先：`agent-service/` 必须能单独安装依赖、启动、健康检查和部署。
- 业务主状态不迁移：鉴权、session、task、用户/组织权限、业务数据仍归 `backend/` 管理。
- agent-service 不直连主数据库：业务操作通过当前后端的受控 API 或 MCP/tool gateway 完成。
- 前端不直连 agent-service：前端仍通过当前后端入口，避免绕过鉴权、审计和 task 状态管理。
- 小步迁移：保留现有 `backend/app/agent_platform` 可回退，先新增 Claude 路径，再逐步替换旧 OpenAI/自研 runtime 路径。
- 参考 AiToEarn 的分层思想，不复制其目录和实现。

## 总体架构

```text
frontend/packages/main-app
  CopilotKit components / existing ANIFORCE views
              |
              | HTTP SSE / AG-UI
              v
backend/
  auth, user, org, session, task, business APIs
  agent gateway: validates token, creates task, calls agent-service
              |
              | internal HTTP SSE
              v
agent-service/
  FastAPI app
  Claude Agent SDK runtime
  prompt and tool adapters
  event normalization
```

## 项目边界

### frontend

前端负责对话体验，不负责 agent 执行编排。第一阶段保留现有页面结构，逐步将 `components/agent` 和 `useAgUiAgent` 的承接层切换到 CopilotKit 组件。若 CopilotKit 组件无法覆盖 ANIFORCE 的时间线、工具活动、工作区联动等体验，再在项目内做二开包装。

前端只调用当前后端的 `/api/v1/copilotkit` 或后续统一 agent gateway，不直接访问 `agent-service`。

### backend

当前后端继续作为控制面和业务网关。它负责：

- JWT 鉴权和当前用户解析。
- 用户、组织和权限上下文组装。
- task 创建、状态更新、事件存储和查询。
- session 归属、续接和历史查询。
- 将前端请求转换为 agent-service 执行请求。
- 将 agent-service 事件流转换为 AG-UI/CopilotKit SSE。
- 暴露业务 API、MCP 或内部 tool gateway 给 agent-service 调用。

后端不再直接承载 Claude Agent SDK 的长程执行逻辑。

### agent-service

`agent-service/` 是独立 Python 服务，第一阶段建议使用 FastAPI。它负责：

- 加载 `claude-agent-sdk-python`。
- 管理 Claude Agent SDK 的单次执行或交互式 client 生命周期。
- 根据后端传入的用户上下文、session 上下文和 task 上下文构造 agent prompt。
- 将工具调用适配到当前后端的受控 API/MCP。
- 将 Claude SDK 消息转换为内部标准事件流。
- 输出健康检查、执行接口和流式执行接口。

agent-service 不保存业务主状态；如需本地 trace/log，只作为运行诊断产物，不作为业务事实来源。

## 代码产物路径

第一阶段预计新增：

```text
agent-service/
  pyproject.toml
  README.md
  .env.example
  app/
    main.py
    config.py
    schemas.py
    runtime/
      claude_client.py
      prompt_builder.py
      event_mapper.py
    tools/
      backend_client.py
      registry.py
    api/
      health.py
      runs.py
  tests/
    test_event_mapper.py
    test_prompt_builder.py
```

预计修改：

```text
backend/app/api/v1/copilotkit.py
backend/app/services/agent_task_service.py
backend/app/config/settings.py
frontend/packages/main-app/src/composables/useAgUiAgent.ts
frontend/packages/main-app/src/components/agent/* 或新增 CopilotKit wrapper
docs/superpowers/plans/2026-06-15-claude-agent-service-migration.md
```

## 后端与 agent-service 接口

第一阶段使用内部 HTTP，避免引入消息队列。接口保持小而明确。

### 健康检查

```http
GET /health
```

返回：

```json
{
  "status": "ok",
  "runtime": "claude-agent-sdk-python"
}
```

### 流式执行

```http
POST /v1/runs/stream
Authorization: Bearer <internal-service-token>
Content-Type: application/json
```

请求体：

```json
{
  "task_id": "task_xxx",
  "session_id": "session_xxx",
  "user_id": "user_xxx",
  "org_code": "org_xxx",
  "input": "用户输入",
  "history": [],
  "context": {
    "backend_base_url": "http://127.0.0.1:8000",
    "user_access_token": "原用户 JWT 或后端签发的代理 token"
  }
}
```

响应为 SSE，每条事件使用 agent-service 内部事件类型：

```text
event: agent_event
data: {"type":"message_delta","task_id":"task_xxx","text":"..."}
```

后端负责把这些事件再映射成现有 `AgentTaskEvent` 和 AG-UI 事件。

## 权限与安全

- 前端请求必须先进入 `backend/` 鉴权。
- backend 调用 agent-service 使用内部服务 token，不能透传未经限制的公开入口。
- agent-service 调用 backend tool/API 时，第一阶段优先使用后端签发的短期代理 token；如果先透传用户 JWT，必须限制目标 base URL 和可调用路径。
- Claude SDK 的工具权限要做 allowlist。默认不开放文件写入、任意 Bash 或系统路径访问。
- agent-service 工作目录限制在 `agent-service/` 自身运行目录或专用 sandbox 目录。

## Session 与 Task 续接

session 和 task 的主记录仍在 backend。agent-service 每次执行只接收必要上下文：

- `session_id` 用于关联历史，不作为 agent-service 的持久业务 ID。
- `task_id` 用于日志和事件回传。
- `history` 由 backend 从当前 session 管理中读取并裁剪后传入。
- agent-service 生成的事件由 backend 写回 task event store。

如果 Claude SDK 后续需要长期 interactive client，会在 backend task 生命周期中显式创建和关闭，不在第一阶段隐式常驻。

## 前端迁移策略

前端第一阶段不重写整个 Home Agent。优先保持现有页面和状态入口，替换对话协议承接：

- 继续使用现有 `/api/v1/copilotkit` 作为前端入口。
- 引入或包装 CopilotKit 组件承接消息、运行状态和工具活动。
- 保留 ANIFORCE 已有 timeline/workspace 组件，必要时通过 AG-UI state/tool event 驱动。
- 等最小闭环稳定后，再决定是否替换 `AgentShell.vue` 和 `ChatWindow.vue` 的内部实现。

## 迁移阶段

### 阶段 0：Draft 探针验证门禁

正式迁移代码前，必须先在 `drafts/260615_claude_migration_probes/` 中验证高风险环节，并把结论写入 `findings.md`。阶段 0 不修改正式业务代码，只产出可重复脚本、样例输出和结论。

必须覆盖：

- Claude Agent SDK runtime：import、query/client、真实模型调用、streaming、权限收敛。
- 输入输出协议：Claude SDK 消息到 ANIFORCE 内部事件，再到 AG-UI/CopilotKit SSE。
- 目录结构：未来 `agent-service/` 的最小目录和运行边界。
- system prompt：ANIFORCE 角色、工具规则、输出风格和安全边界。
- skill 机制：skills 发现、加载、prompt 注入、工具 allowlist。
- MCP/tool：in-process MCP、后端 API/tool gateway、错误返回格式。
- CopilotKit/AG-UI：组件样式、协议适配、Vue 复用方式。
- task/session/error：task sequence、session history snapshot、异常兜底、trace 输出。

阶段 0 完成标准：离线探针全部通过；需要真实凭据的探针要么通过，要么在 `findings.md` 明确阻塞原因和下一步；不得在未记录结论的情况下进入正式代码迁移。

### 阶段 1：骨架与最小闭环

- 创建 `agent-service/` 独立项目。
- 实现 `/health` 和 `/v1/runs/stream`。
- 实现 Claude SDK 最小 query/client 封装。
- 实现 Claude 消息到内部事件的 mapper。
- backend 新增 agent-service client，并在 `copilotkit.py` 中切换到可配置的远程 runtime。
- 前端保持现有入口，验证消息能流式显示。

### 阶段 2：工具与业务能力迁移

- 将项目、投放计划、素材等能力通过 backend tool gateway 暴露给 agent-service。
- 建立工具 allowlist 和参数 schema。
- 将现有 `agent_platform` 中可复用的 event/task 模型保留在 backend，runtime 逻辑逐步下沉到 agent-service。

### 阶段 3：CopilotKit 组件化替换

- 评估 CopilotKit 原生组件与当前 ANIFORCE UI 的差距。
- 新增项目内 wrapper 组件，统一样式和事件适配。
- 逐步替换现有手写对话状态管理。

### 阶段 4：部署与回退

- 为 `agent-service/` 增加独立启动脚本和环境变量说明。
- backend 增加开关：本地旧 runtime / 远程 Claude agent-service。
- 保留可回退路径直到 Claude runtime 覆盖当前关键能力。

## 校验策略

- agent-service 单元测试：prompt builder、event mapper、schema validation。
- backend 单元测试：agent-service client、task 创建与事件映射。
- 前端类型检查：AG-UI/CopilotKit 接入点类型无误。
- 集成冒烟：启动 backend 与 agent-service，发送一条消息，确认 task 创建、事件流输出、前端可显示。

所有 Python 命令遵循项目规范：使用项目内 `.venv` 和 `UV_CACHE_DIR=./uv_cache`。所有 Node 命令显式设置 `npm_config_cache=./npm_cache`。

## 风险与约束

- `claude-agent-sdk-python` 默认工具能力较强，必须显式收敛权限和工作目录。
- CopilotKit 组件可能与当前 Vue 前端栈存在适配成本；如果资源里的组件偏 React，需要先抽协议和样式思路，再决定二开方式。
- 第一阶段不保证覆盖现有 agent 的所有 timeline/workspace 交互，只保证可验证的最小闭环。
- 当前工作区已有运行数据库、trace 和草稿变更，本迁移不清理、不回滚这些内容。

## 下一步

基于本设计编写实施计划：`docs/superpowers/plans/2026-06-15-claude-agent-service-migration.md`。实施计划应按任务拆分到可测试的小步骤，并在每个任务中明确文件、测试和回退点。

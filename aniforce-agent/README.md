# ANIFORCE Agent Service

基于 **Claude Agent SDK (Python)** 的智能 Agent 服务，为 ANIFORCE 广告投放平台提供对话式 AI 能力。

## 核心特性

- ✅ **Claude Agent SDK 集成**：使用 ClaudeSDKClient 实现有状态对话
- ✅ **CopilotKit 协议**：完整支持 AG-UI 协议，前端流式对话体验
- ✅ **独立部署**：与后端服务解耦，独立扩展
- ✅ **SQLite 存储**：零配置、高性能的本地持久化
- ✅ **多租户隔离**：基于 JWT 的用户级权限控制
- ✅ **HTTP MCP 集成**：远程调用后端业务能力
- ✅ **Session 管理**：会话持久化与恢复
- ✅ **Skill 动态注入**：运行时加载技能模块
- ✅ **事件流**：完整的任务执行追踪与断点续传

## 快速开始

### 安装依赖

```bash
# 创建虚拟环境
UV_CACHE_DIR=./uv_cache uv venv --python 3.11

# 安装依赖
UV_CACHE_DIR=./uv_cache uv pip install --python .venv/bin/python -r requirements.txt

# 安装 Claude Agent SDK（本地）
UV_CACHE_DIR=./uv_cache uv pip install --python .venv/bin/python -e ../resources/claude-agent-sdk-python
```

### 配置环境变量

创建 `.env` 文件：

```bash
DEBUG=true
PORT=8020
TASK_DB_PATH=runtime/agent/tasks.db
SESSION_DB_PATH=runtime/agent/sessions.db
JWT_SECRET=your-secret-key
BACKEND_URL=http://localhost:8010
INTERNAL_TOKEN=your-internal-token
ANTHROPIC_API_KEY=sk-ant-xxxxx
CORS_ALLOW_ORIGINS=http://localhost:3000
```

### 启动服务

```bash
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8020 \
    --reload
```

访问：
- 健康检查: http://localhost:8020/health
- API 文档: http://localhost:8020/docs

### 运行测试

```bash
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python pytest tests/ -v
```

## 项目结构

```
aniforce-agent/
├── app/
│   ├── main.py                    # FastAPI 应用入口
│   ├── config/                    # 配置管理
│   │   ├── settings.py            # 环境变量配置
│   │   └── database.py            # 数据库初始化
│   ├── core/                      # 核心功能
│   │   ├── auth.py                # JWT 验证
│   │   └── context.py             # 请求上下文（user_id）
│   ├── agent/                     # Agent 运行时
│   │   ├── runtime.py             # AgentRuntime（ClaudeSDKClient 封装）
│   │   ├── session_store.py       # SQLite SessionStore
│   │   ├── skill_manager.py       # Skill 动态注入
│   │   └── sandbox.py             # Sandbox 隔离管理
│   ├── mcp/                       # MCP 工具
│   │   ├── local/                 # 本地工具（SDK MCP）
│   │   └── remote.py              # HTTP MCP 桥接
│   ├── models/                    # 数据模型
│   │   ├── task.py                # AgentTask ORM
│   │   └── event.py               # AgentEvent ORM
│   ├── repositories/              # 数据访问层
│   │   ├── task_repo.py           # Task Repository
│   │   └── event_repo.py          # Event Repository
│   ├── services/                  # 业务逻辑层
│   │   ├── task_service.py        # Task Service
│   │   └── copilotkit_adapter.py  # AG-UI 协议适配
│   ├── api/                       # API 端点
│   │   ├── copilotkit.py          # CopilotKit 标准接口
│   │   └── tasks.py               # Task 管理接口
│   ├── middleware/                # 中间件
│   │   └── auth.py                # JWT 认证中间件
│   └── skills/                    # Skill 源文件
│       ├── project-management/
│       └── campaign-management/
├── tests/                         # 测试套件
│   ├── conftest.py                # 测试配置与 Fixtures
│   ├── test_auth.py               # 认证测试
│   ├── test_repositories.py       # Repository 测试
│   ├── test_agent_integration.py  # Agent 集成测试
│   ├── test_api_endpoints.py      # API 端点测试
│   └── test_e2e.py                # 端到端测试
├── runtime/                       # 运行时数据
│   ├── agent/                     # 数据库文件
│   │   ├── tasks.db               # 任务数据
│   │   └── sessions.db            # Session 数据
│   └── sessions/                  # 会话工作目录
├── requirements.txt               # Python 依赖
├── DEPLOYMENT.md                  # 部署文档
└── README.md                      # 项目说明
```

## API 端点

### CopilotKit 标准接口

#### 获取 Agent 信息
```http
GET /api/agent/copilotkit/info
```

#### 运行 Agent（流式对话）
```http
POST /api/agent/copilotkit/agent/default/run
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "创建一个新项目"}
  ],
  "threadId": "session_abc123"
}
```

### 任务管理接口

```http
POST   /api/agent/tasks              # 创建任务
GET    /api/agent/tasks              # 查询任务列表
GET    /api/agent/tasks/{task_id}    # 获取任务详情
GET    /api/agent/tasks/{task_id}/events  # 获取事件流（支持断点续传）
DELETE /api/agent/tasks/{task_id}    # 取消任务
```

## 核心架构

### 1. ClaudeSDKClient 状态管理

每个 `session_id` 对应一个长期存活的 `ClaudeSDKClient` 实例：

```python
# app/agent/runtime.py
class AgentRuntime:
    def __init__(self):
        self._clients: Dict[str, ClaudeSDKClient] = {}  # 实例池
        self._locks: Dict[str, asyncio.Lock] = {}       # 并发控制
    
    async def get_or_create_client(self, session_id, user_id, task_id, ...):
        # 复用已有实例或创建新实例（双重检查锁）
        if session_id in self._clients:
            return self._clients[session_id]
        
        async with self._locks[session_id]:
            if session_id not in self._clients:
                client = ClaudeSDKClient(options)
                await client.connect()
                self._clients[session_id] = client
            return self._clients[session_id]
```

### 2. SQLite SessionStore

会话数据持久化到 SQLite：

```python
# app/agent/session_store.py
class SQLiteSessionStore(SessionStore):
    async def append(self, key: SessionKey, entries: list[SessionStoreEntry]):
        # 追加 Session 条目到数据库
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany("INSERT INTO sessions ...", values)
    
    async def load(self, key: SessionKey) -> list[SessionStoreEntry] | None:
        # 加载 Session 历史
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT entry FROM sessions ...")
            return [json.loads(row[0]) for row in await cursor.fetchall()]
```

### 3. AG-UI 协议适配

将 Claude SDK 消息流转换为 CopilotKit AG-UI 事件：

```python
# app/services/copilotkit_adapter.py
async def stream_ag_ui_events(task_id, sdk_messages):
    async for message in sdk_messages:
        if message["type"] == "assistant":
            yield {"event": "TEXT_MESSAGE_START", "data": {...}}
            yield {"event": "TEXT_MESSAGE_CONTENT", "data": {...}}
            yield {"event": "TEXT_MESSAGE_END", "data": {...}}
        elif message["type"] == "user" and has_tool_result:
            yield {"event": "TOOL_CALL_RESULT", "data": {...}}
    
    yield {"event": "RUN_FINISHED", "data": {"runId": task_id}}
```

### 4. 多租户隔离

所有 Repository 方法强制过滤 `user_id`：

```python
# app/repositories/task_repo.py
async def get(self, task_id: str, user_id: str) -> AgentTask | None:
    cursor = await self.db.execute(
        "SELECT * FROM tasks WHERE task_id = ? AND user_id = ?",
        (task_id, user_id)  # 强制 user_id 过滤
    )
```

## 测试覆盖

- **单元测试**：认证、Repository、Service
- **集成测试**：Agent Runtime、ClaudeSDKClient
- **API 测试**：所有端点、认证中间件
- **E2E 测试**：完整用户流程、多租户隔离、断点续传

```bash
# 运行所有测试
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python pytest tests/ -v

# 生成覆盖率报告
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python pytest tests/ --cov=app --cov-report=html
```

**当前测试结果**：23 个测试全部通过 ✅

## 技术栈

- **框架**: FastAPI 0.115.0 + Uvicorn 0.32.0
- **Agent SDK**: Claude Agent SDK (Python) 0.2.101
- **数据库**: SQLite + aiosqlite 0.20.0
- **认证**: python-jose 3.3.0 (JWT)
- **HTTP 客户端**: httpx 0.27.2 + aiohttp 3.10.10
- **测试**: pytest 8.3.3 + pytest-asyncio 0.24.0
- **包管理**: uv + Python 3.11

## 开发规范

### 代码风格

- 使用 Black 格式化（行长 100）
- 使用 isort 排序导入
- 使用 pylint 静态检查
- 所有公共 API 必须有 docstring

### 提交规范

```
feat(scope): 功能描述
fix(scope): 修复描述
test(scope): 测试描述
docs(scope): 文档描述
refactor(scope): 重构描述
```

### 测试要求

- 新功能必须有对应测试
- PR 前确保所有测试通过
- 关键路径保持 80%+ 覆盖率

## 部署

详见 [DEPLOYMENT.md](./DEPLOYMENT.md)

## 相关文档

- [迁移方案](../docs/migration-plan.md) - 从 OpenAI SDK 迁移到 Claude SDK 的完整方案
- [架构设计](../docs/architecture.md) - 系统架构与技术选型
- [学习手册](../drafts/260615_claude_sdk_learning/study_notes.md) - Claude SDK 调试经验

## 常见问题

### 1. JWT Token 认证失败

确保 `JWT_SECRET` 与后端服务一致，且 Token 未过期。

### 2. Claude SDK 连接错误

检查 `ANTHROPIC_API_KEY` 是否配置正确，以及网络是否可访问 api.anthropic.com。

### 3. HTTP MCP 调用失败

确保 `BACKEND_URL` 和 `INTERNAL_TOKEN` 配置正确，且后端服务正常运行。

### 4. Session 无法恢复

检查 `SESSION_DB_PATH` 是否有写入权限，以及数据库文件是否存在。

## 贡献指南

1. Fork 本项目
2. 创建功能分支（`git checkout -b feat/amazing-feature`）
3. 提交变更（`git commit -m 'feat: add amazing feature'`）
4. 推送到分支（`git push origin feat/amazing-feature`）
5. 提交 Pull Request

## License

Copyright © 2025 ANIFORCE Team. All rights reserved.

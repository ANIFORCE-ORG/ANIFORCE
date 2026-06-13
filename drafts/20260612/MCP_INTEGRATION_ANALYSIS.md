# OpenAI Agents SDK - MCP 集成分析

## 1. SDK 架构概览

### 1.1 核心模块结构

```
agents/
├── mcp/
│   ├── __init__.py          # MCP 模块入口，懒加载
│   ├── server.py            # MCPServer 基类和各种传输实现
│   ├── manager.py           # MCPServerManager 生命周期管理
│   └── util.py              # 工具转换、过滤、元数据解析
├── agent.py                 # Agent 定义，支持 mcp_servers 参数
├── run.py                   # Runner 执行引擎
└── tool.py                  # FunctionTool 定义
```

### 1.2 关键设计理念

- **适配器模式**：MCPServer 作为适配器，将 MCP 工具转换为 SDK FunctionTool
- **生命周期管理**：MCPServerManager 统一管理多个 MCP 服务的连接/清理
- **传输层抽象**：支持 Stdio、SSE、StreamableHTTP 三种传输方式
- **工具过滤**：支持静态（allowlist/blocklist）和动态（callable）过滤
- **审批流程**：支持工具调用前的审批机制（require_approval）

---

## 2. MCP 服务端实现

### 2.1 标准 MCP Server 示例

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "Example Server",
    host="127.0.0.1",
    port=8000,
)

@mcp.tool()
def add(a: int, b: int) -> int:
    """加法工具"""
    return a + b

@mcp.tool()
def echo(message: str) -> str:
    """回声工具"""
    return f"echo: {message}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

**关键点**：
- 使用 `fastmcp` 快速构建 MCP 服务
- 通过 `@mcp.tool()` 装饰器注册工具
- 支持 `stdio`、`sse`、`streamable-http` 三种传输方式

### 2.2 部署方式

#### 方案 A：独立进程（适合本地开发）
```bash
# 启动 MCP 服务
python mcp_server.py

# Agent 通过 StreamableHTTP 连接
# MCPServerStreamableHttp({"url": "http://localhost:8000/mcp"})
```

#### 方案 B：内嵌启动（适合生产环境）
```python
# 在 FastAPI lifespan 中启动 MCP 服务进程
import subprocess
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动 MCP 服务进程
    mcp_process = subprocess.Popen([
        "python", "mcp_server.py"
    ])
    
    await asyncio.sleep(1)  # 等待服务启动
    
    # 初始化 MCPServerManager
    async with MCPServerManager([...]) as manager:
        app.state.mcp_manager = manager
        yield
    
    # 清理 MCP 服务进程
    mcp_process.terminate()
    mcp_process.wait()
```

#### 方案 C：Stdio（适合本地工具）
```python
# 直接通过 Stdio 启动子进程
MCPServerStdio(
    name="Filesystem Server",
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"],
    },
)
```

---

## 3. Agent 端集成

### 3.1 基础集成

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp

# 创建 MCP 服务连接
async with MCPServerStreamableHttp(
    {"url": "http://localhost:8000/mcp"}
) as server:
    # 创建 Agent 并关联 MCP 服务
    agent = Agent(
        name="Assistant",
        instructions="Use the tools to help user.",
        mcp_servers=[server],  # 关联 MCP 服务
    )
    
    # 执行任务
    result = await Runner.run(
        starting_agent=agent,
        input="Calculate 5 + 3"
    )
    print(result.final_output)
```

### 3.2 多服务管理（推荐）

```python
from agents.mcp import MCPServerManager

servers = [
    MCPServerStreamableHttp({"url": "http://localhost:8001/mcp"}),
    MCPServerStreamableHttp({"url": "http://localhost:8002/mcp"}),
]

async with MCPServerManager(
    servers=servers,
    connect_in_parallel=True,      # 并行连接
    drop_failed_servers=True,      # 移除失败服务
    strict=False,                  # 容错模式
    connect_timeout_seconds=10.0,
) as manager:
    agent = Agent(
        name="Assistant",
        instructions="...",
        mcp_servers=manager.active_servers,  # 只使用成功连接的服务
    )
    
    # 运行时重连失败的服务
    await manager.reconnect(failed_only=True)
```

### 3.3 工具过滤

```python
# 静态过滤
server = MCPServerStreamableHttp(
    {"url": "..."},
    tool_filter={
        "allowed_tool_names": ["add", "echo"],  # 白名单
        "blocked_tool_names": ["delete"],        # 黑名单
    }
)

# 动态过滤
async def my_filter(ctx: ToolFilterContext, tool: MCPTool) -> bool:
    # 根据运行时上下文动态决定
    if ctx.agent.name == "Admin":
        return True
    return tool.name not in ["delete", "modify"]

server = MCPServerStreamableHttp(
    {"url": "..."},
    tool_filter=my_filter,
)
```

### 3.4 审批流程

```python
# 全局审批策略
server = MCPServerStreamableHttp(
    {"url": "..."},
    require_approval="always",  # always | never
)

# 按工具名配置
server = MCPServerStreamableHttp(
    {"url": "..."},
    require_approval={
        "delete": True,   # 需要审批
        "read": False,    # 不需要审批
    }
)

# 自定义审批逻辑
async def my_approval(
    run_context: RunContextWrapper,
    agent: AgentBase,
    tool: MCPTool
) -> bool:
    # 返回 True = 需要审批，False = 直接执行
    if tool.name.startswith("delete_"):
        return True
    return False

server = MCPServerStreamableHttp(
    {"url": "..."},
    require_approval=my_approval,
)
```

---

## 4. 适配到 ANIFORCE 的改造点

### 4.1 当前架构

```
Agent Runtime (runtime.py)
    ↓
OpenAISDKAdapter (adapters/openai_adapter.py)
    ↓
agents SDK (Agent + Runner)
    ↓
LLM (Chat Completions API)
```

### 4.2 需要改造的模块

#### 1. OpenAISDKAdapter 扩展

**文件**: `backend/app/agent_platform/adapters/openai_adapter.py`

**改造点**:
- 添加 `mcp_servers` 参数支持
- 在 `create_agent` 时传递 MCP 服务列表
- 处理 MCP 工具调用事件的转换

```python
class OpenAISDKAdapter:
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        enable_tracing: bool = True,
        mcp_servers: list[MCPServer] | None = None,  # 新增
    ):
        # ...
        self.mcp_servers = mcp_servers or []
    
    def create_agent(
        self,
        name: str,
        instructions: str,
        mcp_servers: list[MCPServer] | None = None,  # 新增
    ) -> Agent:
        agent = Agent(
            name=name,
            instructions=instructions,
            model=self.model,
            mcp_servers=mcp_servers or self.mcp_servers,  # 新增
        )
        return agent
```

#### 2. AgentRuntime 扩展

**文件**: `backend/app/agent_platform/runtime.py`

**改造点**:
- 集成 MCPServerManager
- 在 `run_task` 时传递 MCP 服务
- 处理 MCP 连接失败的情况

```python
class AgentRuntime:
    def __init__(
        self,
        adapter: OpenAISDKAdapter,
        repo: AgentTaskRepository,
        session_db_path: str = "runtime/agent/sessions.db",
        enable_tracing: bool = True,
        mcp_manager: MCPServerManager | None = None,  # 新增
    ):
        # ...
        self.mcp_manager = mcp_manager
    
    async def run_task(self, task: AgentTask, user_input: str):
        # ...
        
        # 获取可用的 MCP 服务
        mcp_servers = []
        if self.mcp_manager:
            mcp_servers = self.mcp_manager.active_servers
        
        # 创建 Agent 时传递 MCP 服务
        agent = self.adapter.create_agent(
            name="ANIFORCE Assistant",
            instructions=self._get_system_prompt(task.task_type),
            mcp_servers=mcp_servers,  # 新增
        )
        
        # ...
```

#### 3. MCP 服务管理模块（新增）

**文件**: `backend/app/agent_platform/mcp/manager.py`

**功能**:
- 统一管理所有 MCP 服务配置
- 提供 MCP 服务的生命周期管理
- 支持动态注册/注销 MCP 服务

```python
from agents.mcp import MCPServerManager, MCPServerStreamableHttp

class MCPServiceManager:
    """MCP 服务管理器（业务层）"""
    
    def __init__(self, config: dict):
        self.config = config
        self.sdk_manager: MCPServerManager | None = None
    
    async def initialize(self):
        """初始化所有 MCP 服务"""
        servers = []
        
        for service_config in self.config.get("services", []):
            server = self._create_server(service_config)
            servers.append(server)
        
        # 使用 SDK 的 MCPServerManager
        self.sdk_manager = MCPServerManager(
            servers=servers,
            connect_in_parallel=True,
            drop_failed_servers=True,
            strict=False,
        )
        
        await self.sdk_manager.__aenter__()
        return self.sdk_manager
    
    def _create_server(self, config: dict) -> MCPServerStreamableHttp:
        return MCPServerStreamableHttp(
            params={"url": config["url"]},
            cache_tools_list=config.get("cache_tools", True),
            tool_filter=self._build_tool_filter(config),
            require_approval=config.get("require_approval", False),
        )
    
    async def cleanup(self):
        if self.sdk_manager:
            await self.sdk_manager.__aexit__(None, None, None)
```

#### 4. FastAPI 集成

**文件**: `backend/app/main.py`

**改造点**:
- 在 lifespan 中启动 MCP 服务和管理器
- 将 MCPServerManager 注入到 Runtime

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 加载 MCP 配置
    mcp_config = load_mcp_config()
    
    # 2. 启动 MCP 服务进程（如果需要）
    mcp_processes = []
    for service in mcp_config.get("local_services", []):
        process = subprocess.Popen([
            "python", service["script_path"]
        ])
        mcp_processes.append(process)
    
    await asyncio.sleep(1)  # 等待服务启动
    
    # 3. 初始化 MCP 管理器
    mcp_service_manager = MCPServiceManager(mcp_config)
    sdk_manager = await mcp_service_manager.initialize()
    
    # 4. 注入到应用状态
    app.state.mcp_manager = sdk_manager
    
    yield
    
    # 5. 清理
    await mcp_service_manager.cleanup()
    for process in mcp_processes:
        process.terminate()
        process.wait()

app = FastAPI(lifespan=lifespan)
```

---

## 5. 事件流转换

### 5.1 SDK 事件 → AgentTaskEvent

SDK 的 MCP 工具调用会产生以下事件:

```python
# SDK 事件类型
run_item_stream_event:
  - name: "tool_called"    → EventType.TOOL_CALL_STARTED
  - name: "tool_output"    → EventType.TOOL_CALL_COMPLETED
```

### 5.2 现有转换逻辑扩展

在 `OpenAISDKAdapter._transform_sdk_event` 中已经处理了 `tool_called` 和 `tool_output`，
MCP 工具调用会走相同的转换流程，无需额外修改。

---

## 6. 配置示例

### 6.1 MCP 服务配置文件

**文件**: `backend/conf/mcp_services.yaml`

```yaml
# MCP 服务配置
services:
  # 文件系统服务（本地 Stdio）
  - name: filesystem
    type: stdio
    enabled: true
    command: npx
    args:
      - "-y"
      - "@modelcontextprotocol/server-filesystem"
      - "/workspace/shared"
    cache_tools: true
    require_approval: false

  # 计算服务（远程 HTTP）
  - name: calculator
    type: streamable-http
    enabled: true
    url: http://localhost:8001/mcp
    cache_tools: true
    tool_filter:
      allowed_tool_names:
        - add
        - subtract
        - multiply
    require_approval: false

  # 数据库服务（远程 HTTP，需审批）
  - name: database
    type: streamable-http
    enabled: true
    url: http://localhost:8002/mcp
    cache_tools: false
    tool_filter:
      blocked_tool_names:
        - drop_table
        - truncate_table
    require_approval:
      delete_record: true
      update_record: true

# 本地服务定义（需要由 FastAPI 启动）
local_services:
  - name: calculator
    script_path: backend/app/mcp_servers/calculator_server.py
    host: 127.0.0.1
    port: 8001
```

### 6.2 加载配置

```python
import yaml

def load_mcp_config() -> dict:
    config_path = "backend/conf/mcp_services.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)
```

---

## 7. 部署架构图

```
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Application                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │              AgentRuntime                          │ │
│  │                                                    │ │
│  │  ┌──────────────────────────────────────────────┐ │ │
│  │  │      OpenAISDKAdapter                        │ │ │
│  │  │                                              │ │ │
│  │  │  ┌────────────────────────────────────────┐ │ │ │
│  │  │  │   agents.Agent                         │ │ │ │
│  │  │  │   - mcp_servers: [...]                 │ │ │ │
│  │  │  └────────────────────────────────────────┘ │ │ │
│  │  └──────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────┘ │
│                         ↓                                │
│  ┌────────────────────────────────────────────────────┐ │
│  │         MCPServerManager (SDK)                     │ │
│  │  - active_servers: [Server A, Server B]           │ │
│  │  - failed_servers: []                              │ │
│  └────────────────────────────────────────────────────┘ │
│                         ↓                                │
│         ┌───────────────┴───────────────┐               │
│         ↓                               ↓               │
│  ┌──────────────┐              ┌──────────────┐        │
│  │ MCP Server A │              │ MCP Server B │        │
│  │  (Stdio)     │              │  (HTTP)      │        │
│  └──────────────┘              └──────────────┘        │
│         ↓                               ↓               │
│  ┌──────────────┐              ┌──────────────┐        │
│  │ Local Tool   │              │ Remote HTTP  │        │
│  │ Process      │              │ Service      │        │
│  └──────────────┘              └──────────────┘        │
└─────────────────────────────────────────────────────────┘
```

---

## 8. 实施步骤

### Phase 1: 基础设施（1-2天）
1. 创建 MCP 服务管理模块
2. 实现配置加载和解析
3. 编写 MCP Server 示例（calculator）
4. 集成到 FastAPI lifespan

### Phase 2: SDK 适配（1天）
1. 扩展 OpenAISDKAdapter 支持 mcp_servers
2. 扩展 AgentRuntime 集成 MCPServerManager
3. 测试基础的 MCP 工具调用

### Phase 3: 高级特性（1-2天）
1. 实现工具过滤
2. 实现审批流程
3. 实现动态重连
4. 完善错误处理

### Phase 4: 测试和文档（1天）
1. 编写单元测试
2. 编写集成测试
3. 更新 API 文档
4. 编写运维手册

---

## 9. 风险和注意事项

### 9.1 连接失败处理
- MCP 服务可能启动失败或连接超时
- 使用 `MCPServerManager` 的容错模式（`strict=False`）
- 监控 `manager.failed_servers` 并记录日志

### 9.2 工具冲突
- 多个 MCP 服务可能提供同名工具
- SDK 会自动处理（后加载的覆盖先加载的）
- 建议：使用 tool_filter 明确限制工具集

### 9.3 性能开销
- 每次 `list_tools` 都会发起 MCP 请求
- 建议：设置 `cache_tools_list=True`
- 只在工具列表变更时调用 `invalidate_tools_cache()`

### 9.4 安全考虑
- MCP 工具可能执行危险操作（文件删除、数据修改）
- 建议：对敏感工具设置 `require_approval=True`
- 使用 `tool_filter` 限制可用工具范围

---

## 10. 总结

新 SDK 的 MCP 适配方案非常完善：

**优势**:
- ✅ 开箱即用的 MCPServer 适配器
- ✅ 完善的生命周期管理（MCPServerManager）
- ✅ 灵活的工具过滤和审批机制
- ✅ 支持多种传输方式（Stdio、SSE、HTTP）
- ✅ 内置重连和容错机制

**改造工作量**:
- 🔧 适配器层：小改（添加 mcp_servers 参数传递）
- 🔧 运行时层：小改（集成 MCPServerManager）
- 🆕 MCP 管理：新增（配置加载、服务管理）
- 🆕 MCP 服务：新增（编写业务工具）

**总工作量预估**: 3-5 天（包含测试和文档）

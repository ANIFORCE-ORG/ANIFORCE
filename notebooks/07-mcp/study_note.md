# MCP 生产特性学习笔记

本章重点不是 MCP 基础概念，而是针对生产环境的 3 个高价值特性：
1. `require_approval` - 高风险工具触发 HITL 审批
2. `tool_filter` - 基于角色动态筛选工具（RBAC）
3. `failure_error_function` - 自定义错误格式化 + 脱敏 + 日志

---

## 1. 当前项目 MCP 架构回顾

### 1.1 现有实现

```text
agent-service 内部：
  FastMCP 定义业务工具 (mcp_server.py)
    ↓
  mount 到 /mcp (main.py)
    ↓
  Agent runtime 通过 MCPServerStreamableHttp 连接本地 /mcp
    ↓
  tool_meta_resolver 注入 jwt_token/session_id/run_id
    ↓
  MCP 工具函数通过 backend_client 调 backend REST API
```

### 1.2 已有配置

```python
mcp_server = MCPServerStreamableHttp(
    name="ANIFORCE Tools",
    params={"url": mcp_url, "timeout": 30},
    cache_tools_list=True,              # ✅ 已启用
    max_retry_attempts=2,                # ✅ 已启用
    tool_meta_resolver=_meta_resolver,   # ✅ 已启用
)
```

**当前缺失的生产特性：**
- ❌ `require_approval` - 高风险工具审批
- ❌ `tool_filter` - 基于角色的工具权限
- ❌ `failure_error_function` - 自定义错误格式化

---

## 2. require_approval - 高风险工具审批

### 2.1 功能说明

在高风险 MCP 工具（创建、删除、上线、改预算等）执行前，触发 HITL 审批流程。

### 2.2 配置方式

```python
HIGH_RISK_TOOLS = [
    "create_project",
    "create_campaign",
    "update_campaign_status",
    "delete_project",
    "delete_campaign",
]

SAFE_TOOLS = [
    "list_projects",
    "get_project_detail",
    "list_campaigns",
    "get_campaign_detail",
    "list_materials",
    "get_material_detail",
]

mcp_server = MCPServerStreamableHttp(
    name="ANIFORCE Tools",
    params={"url": mcp_url, "timeout": 30},
    cache_tools_list=True,
    require_approval={
        "always": {"tool_names": HIGH_RISK_TOOLS},
        "never": {"tool_names": SAFE_TOOLS},
    },
)
```

### 2.3 流式审批流程

```python
# 1. 启动流式运行
result = Runner.run_streamed(agent, user_input, context=ctx)

# 2. 消费流式事件直到暂停
async for event in result.stream_events():
    if event.type == "run_item_stream_event" and event.item.type == "tool_call_item":
        print(f"工具调用: {event.item.tool_name}")

# 3. 检查是否有审批请求
if result.interruptions:
    for interruption in result.interruptions:
        print(f"需要审批: {interruption.tool_name}")
        print(f"参数: {interruption.arguments}")
    
    # 4. 批准或拒绝
    state = result.to_state()
    for item in result.interruptions:
        if should_approve(item):
            state.approve(item)
        else:
            state.reject(item, rejection_message="拒绝原因")
    
    # 5. 恢复运行
    result = Runner.run_streamed(agent, state, context=ctx)
    async for event in result.stream_events():
        pass

print(result.final_output)
```

### 2.4 生产建议

**审批策略：**
- 查询类工具：`"never"`
- 创建/更新类工具：`"always"`
- 删除类工具：`"always"`
- 高风险配置修改：`"always"`

**状态持久化：**
```python
# 审批暂停时保存状态
if result.interruptions:
    state_json = result.to_state().to_json()
    await db.save_run_state(run_id, state_json)
    await notify_approver(run_id, result.interruptions)

# 用户批准后恢复
state_json = await db.load_run_state(run_id)
state = await RunState.from_json(agent, state_json)
state.approve(interruption)
result = Runner.run_streamed(agent, state, context=ctx)
```

**前端对接：**
- 流式输出到 WebSocket/SSE
- 检测到 `interruptions` 时显示审批 UI
- 用户批准/拒绝后调用 backend API 恢复运行
- 状态保存到 `agent_runs.run_state_json`

---

## 3. tool_filter - 基于角色的工具权限（RBAC）

### 3.1 功能说明

根据用户角色动态筛选 MCP 工具，实现细粒度的权限控制。

### 3.2 动态筛选器（推荐）

```python
from agents.mcp import ToolFilterContext

async def role_based_tool_filter(context: ToolFilterContext, tool) -> bool:
    """基于用户角色动态筛选工具"""
    run_context = context.run_context.context
    user_role = run_context.user_role  # 从 RunContext 读取角色
    
    # viewer 只能查询
    if user_role == "viewer":
        return tool.name.startswith("list_") or tool.name.startswith("get_")
    
    # editor 可以创建和更新，但不能删除
    if user_role == "editor":
        return not tool.name.startswith("delete_")
    
    # admin 全部工具
    return True

mcp_server = MCPServerStreamableHttp(
    name="ANIFORCE Tools",
    params={"url": mcp_url, "timeout": 30},
    tool_filter=role_based_tool_filter,
)
```

### 3.3 静态筛选器（简单场景）

```python
from agents.mcp import create_static_tool_filter

# 只读 Agent
readonly_filter = create_static_tool_filter(
    allowed_tool_names=["list_projects", "get_project_detail", "list_campaigns"]
)

# 阻止删除操作
no_delete_filter = create_static_tool_filter(
    blocked_tool_names=["delete_project", "delete_campaign"]
)

mcp_server = MCPServerStreamableHttp(
    name="ANIFORCE Tools",
    params={"url": mcp_url, "timeout": 30},
    tool_filter=readonly_filter,
)
```

### 3.4 ToolFilterContext 结构

```python
ToolFilterContext 提供：
- run_context: RunContextWrapper  # 访问 WorkspaceRunContext
- agent: Agent                     # 当前 Agent
- server_name: str                 # MCP server 名称
```

### 3.5 生产建议

**角色定义：**
- `viewer`：只能查询（list_* / get_*）
- `editor`：可以创建和更新，不能删除
- `admin`：全部工具
- `auditor`：只能查询 + 导出报告

**与 backend 权限对齐：**
```python
async def role_based_tool_filter(context: ToolFilterContext, tool) -> bool:
    run_context = context.run_context.context
    user_id = run_context.user_id
    
    # 从 backend 实时查询用户权限
    permissions = await get_user_permissions(user_id)
    
    # 检查工具权限
    if tool.name in permissions.allowed_tools:
        return True
    
    # 默认拒绝
    return False
```

**多租户隔离：**
```python
async def tenant_aware_tool_filter(context: ToolFilterContext, tool) -> bool:
    run_context = context.run_context.context
    tenant_id = run_context.tenant_id
    
    # 某些工具只对特定租户开放
    if tool.name == "export_all_data" and tenant_id != "enterprise_tenant":
        return False
    
    return True
```

---

## 4. failure_error_function - 自定义错误格式化

### 4.1 功能说明

当 MCP 工具调用失败时，自定义错误格式化、记录日志、脱敏敏感信息。

### 4.2 实现方式

```python
def custom_mcp_error_formatter(error: Exception, tool_name: str, arguments: dict) -> str:
    """MCP 工具失败时的用户友好提示"""
    # 1. 记录日志到监控系统
    logger.error(
        f"MCP tool {tool_name} failed",
        exc_info=error,
        extra={
            "tool_name": tool_name,
            "arguments": arguments,
            "error_type": type(error).__name__,
        }
    )
    
    # 2. 脱敏敏感信息
    if "Unauthorized" in str(error) or isinstance(error, PermissionError):
        return "当前用户无权限执行此操作，请联系管理员。"
    
    if "NotFound" in str(error):
        return "资源未找到，请检查 ID 是否正确。"
    
    if "Timeout" in str(error):
        return "操作超时，请稍后重试。"
    
    # 3. 通用错误提示（不暴露内部细节）
    return "工具调用失败，请稍后重试或联系技术支持。"

mcp_server = MCPServerStreamableHttp(
    name="ANIFORCE Tools",
    params={"url": mcp_url, "timeout": 30},
    failure_error_function=custom_mcp_error_formatter,
)
```

### 4.3 错误类型处理

**常见错误类型：**
- `PermissionError` / `Unauthorized` → "无权限执行此操作"
- `ValueError` / `NotFound` → "资源未找到"
- `TimeoutError` → "操作超时"
- `ConnectionError` → "服务连接失败"
- `RuntimeError` / 通用错误 → "工具调用失败"

**脱敏策略：**
```python
def sanitize_error_message(error: Exception, tool_name: str) -> str:
    error_msg = str(error)
    
    # 脱敏 SQL 语句
    error_msg = re.sub(r"SQL:.*", "SQL: [REDACTED]", error_msg)
    
    # 脱敏 API key
    error_msg = re.sub(r"(api[_-]?key|token)[:\s=]+[^\s]+", r"\1: [REDACTED]", error_msg, flags=re.IGNORECASE)
    
    # 脱敏文件路径
    error_msg = re.sub(r"/[\w/]+/[\w/]+", "[PATH]", error_msg)
    
    return error_msg
```

### 4.4 生产建议

**日志记录：**
```python
def custom_mcp_error_formatter(error: Exception, tool_name: str, arguments: dict) -> str:
    # 记录到 Sentry / CloudWatch / Datadog
    sentry_sdk.capture_exception(
        error,
        contexts={
            "mcp_tool": {
                "tool_name": tool_name,
                "arguments": json.dumps(arguments, default=str),
            }
        }
    )
    
    # 记录到业务日志
    await db.log_tool_failure(
        tool_name=tool_name,
        error_type=type(error).__name__,
        error_message=str(error),
        arguments=arguments,
        timestamp=datetime.now(),
    )
    
    return format_user_friendly_error(error)
```

**用户友好提示：**
- ✅ "当前用户无权限执行此操作"
- ✅ "资源未找到，请检查 ID 是否正确"
- ✅ "操作超时，请稍后重试"
- ❌ "HTTPStatusError: 401 Unauthorized"
- ❌ "sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) ..."

**错误兜底：**
```python
def custom_mcp_error_formatter(error: Exception, tool_name: str, arguments: dict) -> str:
    try:
        return format_error_by_type(error)
    except Exception as fmt_error:
        # 格式化器本身出错时的兜底
        logger.error(f"Error formatter failed: {fmt_error}")
        return "工具调用失败，请联系技术支持。"
```

---

## 5. 生产配置完整示例

### 5.1 推荐配置

```python
# aniforce-agent/app/agent/runtime.py

from agents.mcp import MCPServerStreamableHttp, MCPToolMetaContext, ToolFilterContext

async def _mcp_connection(self, task: AgentTask) -> AsyncIterator[list]:
    settings = get_settings()
    mcp_url = f"http://127.0.0.1:{settings.PORT}/mcp"
    jwt_token = (task.context or {}).get("auth_token", "")
    run_meta = (task.context or {}).get("run_meta", {}) or {}
    user_role = (task.context or {}).get("user_role", "viewer")

    # 1. tool_meta_resolver - 注入租户身份
    def _meta_resolver(ctx: MCPToolMetaContext) -> dict[str, str] | None:
        meta: dict[str, str] = {}
        if jwt_token:
            meta["jwt_token"] = jwt_token
        if task.session_id:
            meta["session_id"] = task.session_id
        if run_meta.get("run_id"):
            meta["run_id"] = str(run_meta["run_id"])
        return meta or None

    # 2. tool_filter - 基于角色动态筛选
    async def _role_based_tool_filter(context: ToolFilterContext, tool) -> bool:
        if user_role == "viewer":
            return tool.name.startswith("list_") or tool.name.startswith("get_")
        if user_role == "editor":
            return not tool.name.startswith("delete_")
        return True  # admin

    # 3. failure_error_function - 自定义错误格式化
    def _custom_error_formatter(error: Exception, tool_name: str, arguments: dict) -> str:
        logger.error(f"MCP tool {tool_name} failed", exc_info=error, extra={"arguments": arguments})
        if "Unauthorized" in str(error) or isinstance(error, PermissionError):
            return "当前用户无权限执行此操作。"
        if "NotFound" in str(error):
            return "资源未找到，请检查 ID 是否正确。"
        return "工具调用失败，请稍后重试。"

    # 4. 高风险工具审批策略
    HIGH_RISK_TOOLS = [
        "create_project",
        "create_campaign",
        "update_campaign_status",
        "delete_project",
        "delete_campaign",
    ]

    mcp_server = None
    mcp_servers = []

    try:
        mcp_server = MCPServerStreamableHttp(
            name="ANIFORCE Tools",
            params={"url": mcp_url, "timeout": 30},
            cache_tools_list=True,
            max_retry_attempts=2,
            tool_meta_resolver=_meta_resolver,
            tool_filter=_role_based_tool_filter,           # 🔥 动态工具筛选
            failure_error_function=_custom_error_formatter,  # 🔥 自定义错误格式化
            require_approval={                               # 🔥 高风险工具审批
                "always": {"tool_names": HIGH_RISK_TOOLS},
            },
        )
        await mcp_server.__aenter__()
        mcp_servers.append(mcp_server)
        yield mcp_servers
    finally:
        if mcp_server:
            await mcp_server.__aexit__(None, None, None)
```

### 5.2 前端审批 UI 对接

```typescript
// frontend/packages/main-app/src/composables/useHomeAgentSession.ts

async function handleApprovalRequest(runId: string, interruptions: Interruption[]) {
  // 1. 显示审批 UI
  const approval = await showApprovalDialog({
    tools: interruptions.map(i => ({
      name: i.tool_name,
      arguments: i.arguments,
      risk_level: getRiskLevel(i.tool_name),
    }))
  })
  
  // 2. 调用 backend API 恢复运行
  if (approval.approved) {
    await api.approveAndResume(runId, interruptions.map(i => i.id))
  } else {
    await api.rejectAndResume(runId, interruptions.map(i => i.id), approval.reason)
  }
}
```

---

## 6. 调试验证结果

调试脚本：`notebooks/07-mcp/260702_01_mcp_production_features_debug.py`

### 6.1 场景1：require_approval ✅

**验证内容：**
- 安全工具（list_projects）不触发审批
- 高风险工具（create_project）触发审批
- 批准后继续运行
- 拒绝后继续运行

**结果：** 全部通过

### 6.2 场景2：tool_filter ✅

**验证内容：**
- viewer 角色只能看到 list_* / get_* 工具
- editor 角色可以 create_* 但看不到 delete_*
- admin 角色可以看到全部工具（包括 delete_*）

**结果：** 全部通过

### 6.3 场景3：failure_error_function ✅

**验证内容：**
- Unauthorized 错误 → "当前用户无权限执行此操作"
- NotFound 错误 → "资源不存在"
- 通用错误 → "模拟的通用错误"

**结果：** 全部通过，错误格式化和日志记录正常

### 6.4 场景4：静态筛选 ✅

**验证内容：**
- allowed_tool_names 只允许指定工具
- blocked_tool_names 阻止指定工具

**结果：** 全部通过

---

## 7. 与现有架构的集成点

### 7.1 WorkspaceRunContext

```python
@dataclass
class WorkspaceRunContext:
    user_id: str
    session_id: str
    run_id: str
    user_role: str      # 🔥 用于 tool_filter
    auth_token: str
    ui_snapshot: dict
    business_context_summary: str
```

### 7.2 agent_routes.py

```python
# backend/app/api/v1/agent_routes.py

async def create_agent_run(...):
    # 从 JWT 解析用户角色
    user_role = get_user_role_from_jwt(jwt_token)
    
    # 构建 run context
    run_context = {
        "auth_token": jwt_token,
        "user_role": user_role,  # 🔥 传递给 runtime
        "run_meta": {"run_id": run_id},
    }
    
    # 启动 Agent run
    async for event in runtime.run_task(task, user_input):
        yield event
```

### 7.3 审批状态持久化

```python
# backend/app/models/agent_run.py

class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("agent_sessions.id"))
    status: Mapped[str] = mapped_column(String)  # running / paused / completed
    run_state_json: Mapped[str | None] = mapped_column(Text)  # 🔥 保存 RunState
    pending_approvals: Mapped[list] = mapped_column(JSON)     # 🔥 保存待审批工具
```

---

## 8. 生产部署检查清单

### 8.1 MCP 服务配置

- ✅ `cache_tools_list=True` - 避免每次运行都 list_tools
- ✅ `max_retry_attempts=2` - 自动重试
- ✅ `tool_meta_resolver` - 注入租户身份
- ✅ `tool_filter` - 基于角色的工具权限
- ✅ `failure_error_function` - 自定义错误格式化
- ✅ `require_approval` - 高风险工具审批

### 8.2 审批流程

- ✅ 流式运行支持审批暂停
- ✅ RunState 序列化并持久化到 DB
- ✅ 前端 UI 展示审批请求
- ✅ 批准/拒绝后恢复运行
- ✅ 审批记录可审计

### 8.3 错误处理

- ✅ MCP 工具失败记录到日志
- ✅ 敏感信息脱敏
- ✅ 用户友好提示
- ✅ 错误兜底机制

### 8.4 权限管理

- ✅ 用户角色从 JWT 解析
- ✅ tool_filter 实时筛选工具
- ✅ 与 backend 权限体系对齐
- ✅ 多租户隔离

---

## 9. 关键结论

1. **`require_approval` 是生产必备**：高风险操作（创建、删除、上线）必须审批，避免误操作。

2. **`tool_filter` 实现细粒度 RBAC**：不同角色看到不同工具，viewer 只读、editor 可编辑、admin 全权限。

3. **`failure_error_function` 提升用户体验**：自定义错误格式化、脱敏、记录日志，避免暴露内部细节。

4. **三个特性互补**：
   - `tool_filter` 在前：阻止用户看到不该看的工具
   - `require_approval` 在中：高风险工具触发审批
   - `failure_error_function` 在后：工具失败时友好提示

5. **生产实现优先级**：
   - 短期（1-2周）：添加 `failure_error_function`（工作量小、价值高）
   - 中期（2-4周）：添加 `tool_filter`（实现 RBAC）
   - 长期（1-2月）：添加 `require_approval`（需要前端 UI 和状态持久化）

6. **现有架构兼容性好**：三个特性都可以在不改变现有 FastMCP + backend_client 架构的前提下增量添加。

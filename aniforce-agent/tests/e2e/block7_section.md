## Block 7: MCP 工具接 backend

**交付物**：Agent 通过 MCP 调用 backend API + JWT 透传  
**状态**：🔧 待验证（需 Backend 服务配合）

### 执行
```bash
# 前置条件：启动 Backend 服务
cd backend && npm run dev

# 运行测试
cd aniforce-agent
.venv/bin/python tests/e2e/block7_mcp_backend.py
```

### 验证点
- [ ] Backend 服务可访问
- [ ] Backend MCP 端点 `/api/v1/mcp/tools` 可用
- [ ] MCP 工具包含 `list_campaigns` / `list_projects`
- [ ] Agent 调用 MCP 工具（检测到 TaskProgressUpdated 事件）
- [ ] Agent 基于工具结果生成回复
- [ ] JWT 透传验证（Backend 日志显示正确 user_id）

### 已实现

**1. MCP 工具配置**
- `app/mcp/backend_tools.py`：Backend API 调用工具集（备用，未使用）
- `app/mcp/remote.py`：HTTP MCP 配置生成器
  - `create_backend_mcp_servers(auth_token)`：自动配置 Backend MCP
  - 支持 JWT Token 透传

**2. JWT Token 透传链路**
```
Request → AuthMiddleware → set_jwt_token(token)
                              ↓
          AgentRuntime → get_jwt_token()
                              ↓
          create_backend_mcp_servers(auth_token=jwt_token)
                              ↓
          HTTP MCP → Backend /api/v1/mcp/tools/{tool_name}
                     Header: Authorization: Bearer {token}
```

**3. Runtime 自动配置**
- `app/agent/runtime.py` `_build_options` 方法：
  - 从 context 获取 JWT Token
  - 自动调用 `create_backend_mcp_servers(auth_token)`
  - 注入环境变量：`ANIFORCE_USER_ID` / `ANIFORCE_TASK_ID`

**4. Backend MCP 端点（已存在）**
- `backend/app/api/v1/mcp.py`：
  - `GET /mcp/tools`：列出工具
  - `POST /mcp/tools/{tool_name}`：调用工具
- `backend/app/services/mcp_service.py`：工具实现
  - `list_projects` / `get_project`
  - `list_campaigns` / `get_campaign`
  - `list_materials` / `get_material`
  - `list_platform_auths` / `get_platform_auth`

### 配置要求

**Agent 配置（`.env`）**：
```bash
BACKEND_URL=http://localhost:18003
INTERNAL_TOKEN=test-internal-token-change-me
```

**Backend 配置（`.env`）**：
```bash
PORT=18003
INTERNAL_TOKEN=test-internal-token-change-me
```

### 测试状态（2026-06-17）

**代码层验证**：✅ 通过
- JWT Token 透传链路完整
- MCP 配置自动生成
- Runtime 正确注入环境变量

**集成测试**：⏸️ 待验证
- 需要 Backend 服务运行
- 需要验证实际工具调用
- 需要查看 Backend 日志确认 JWT 透传

### 后续验证步骤

1. 启动 Backend 服务：`cd backend && npm run dev`
2. 运行 Block 7 测试：`.venv/bin/python tests/e2e/block7_mcp_backend.py`
3. 查看 Backend 日志，确认：
   - MCP 工具调用成功
   - JWT Token 正确解析
   - user_id = `test_user_block7`
4. 查看 Agent 日志，确认：
   - `TaskProgressUpdated` 事件包含 tool 信息
   - Agent 基于工具结果生成回复

---

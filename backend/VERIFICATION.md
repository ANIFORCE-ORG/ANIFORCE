# 请求上下文系统 & MCP 鉴权 - 快速验证

## 1. 快速验证

### 步骤 1: 启动主应用（已自动集成上下文中间件）

```bash
cd backend
UV_CACHE_DIR=./uv_cache uv run uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/health 应该返回 OK

### 步骤 2: 测试上下文系统

```bash
# 运行测试
UV_CACHE_DIR=./uv_cache uv run pytest tests/test_context.py -v
```

预期输出：
```
test_authenticated_request PASSED              ✓
test_unauthenticated_request PASSED            ✓
test_optional_authentication_with_token PASSED ✓
test_optional_authentication_without_token PASSED ✓
test_request_id_auto_generated PASSED          ✓
test_request_id_from_header PASSED             ✓
test_invalid_token PASSED                      ✓
test_context_isolation PASSED                  ✓
```

### 步骤 3: 启动 MCP 服务

```bash
# 新开一个终端
cd backend
UV_CACHE_DIR=./uv_cache uv run python app/mcp_servers/campaign_server.py
```

预期输出：
```
🚀 Starting Campaign Management MCP Server...
📍 Listening on: http://127.0.0.1:8001/mcp
🔐 Authentication: Required (JWT Bearer Token)
```

### 步骤 4: 测试 MCP 鉴权

```bash
# 新开一个终端
cd backend
UV_CACHE_DIR=./uv_cache uv run pytest tests/test_mcp_auth.py -v
```

预期输出：
```
test_mcp_authenticated_request PASSED          ✓
test_mcp_unauthenticated_request PASSED        ✓
test_mcp_invalid_token PASSED                  ✓
test_mcp_admin_user PASSED                     ✓
test_mcp_user_isolation PASSED                 ✓
```

---

## 2. 手动测试（使用 curl）

### 2.1 测试主应用的上下文系统

```bash
# 先登录获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@animagus.com","password":"your_password"}' \
  | jq -r '.data.access_token')

# 测试需要鉴权的端点（使用现有的 API）
curl -X GET http://localhost:8000/api/v1/chat/sessions \
  -H "Authorization: Bearer $TOKEN"

# 应该返回用户的对话列表（根据 token 中的 user_id）
```

### 2.2 测试 MCP 服务鉴权

```bash
# 不带 token（应该返回 401）
curl -X POST http://localhost:8001/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "1.0.0",
      "capabilities": {}
    },
    "id": 1
  }'

# 预期输出:
# {"detail":"Missing or invalid authorization header"}

# 带 token（应该成功）
curl -X POST http://localhost:8001/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
      "protocolVersion": "1.0.0",
      "capabilities": {}
    },
    "id": 1
  }'
```

### 2.3 测试 MCP 工具调用

```bash
# 调用 get_campaign_list 工具
curl -X POST http://localhost:8001/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "get_campaign_list",
      "arguments": {}
    },
    "id": 2
  }'

# 预期输出：返回该用户的广告计划列表

# 调用 create_campaign 工具
curl -X POST http://localhost:8001/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "create_campaign",
      "arguments": {
        "name": "测试计划",
        "budget": 5000,
        "platform": "meta"
      }
    },
    "id": 3
  }'
```

---

## 3. 验证向后兼容性

### 3.1 现有 API 继续工作

```bash
# 所有现有端点应该继续正常工作
# 例如：用户登录
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@animagus.com","password":"your_password"}'

# 获取对话列表
curl -X GET http://localhost:8000/api/v1/chat/sessions \
  -H "Authorization: Bearer $TOKEN"

# 平台配置
curl -X GET http://localhost:8000/api/v1/platform-auth/meta \
  -H "Authorization: Bearer $TOKEN"
```

所有这些应该和之前一样正常工作。

---

## 4. 验证关键特性

### 4.1 Request ID 自动生成

```bash
# 不提供 request_id
curl -i http://localhost:8000/health

# 响应头应该包含:
# x-request-id: <自动生成的 UUID>

# 提供自定义 request_id
curl -i -H "x-request-id: my-custom-id" http://localhost:8000/health

# 响应头应该返回:
# x-request-id: my-custom-id
```

### 4.2 用户数据隔离

```bash
# 用户 A 登录
TOKEN_A=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"userA@test.com","password":"password123","name":"User A"}' \
  | jq -r '.data.access_token')

# 用户 B 登录
TOKEN_B=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"userB@test.com","password":"password123","name":"User B"}' \
  | jq -r '.data.access_token')

# 用户 A 调用 MCP 工具
curl -X POST http://localhost:8001/mcp \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_campaign_list"},"id":1}'

# 用户 B 调用 MCP 工具
curl -X POST http://localhost:8001/mcp \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_campaign_list"},"id":1}'

# 两个用户应该看到不同的数据（根据 user_id 隔离）
```

---

## 5. 验收标准

### ✅ 上下文系统

- [ ] 所有测试通过（test_context.py）
- [ ] 现有 55 处 API 继续工作
- [ ] Request ID 自动生成并返回
- [ ] 可以在业务代码中使用 `get_current_user()` 获取用户

### ✅ MCP 鉴权

- [ ] 所有测试通过（test_mcp_auth.py）
- [ ] MCP 服务可以正常启动
- [ ] 未鉴权请求返回 401
- [ ] MCP 工具可以通过 `get_current_user_id()` 获取用户身份
- [ ] 不同用户的数据完全隔离

### ✅ 向后兼容

- [ ] 所有现有 API 端点正常工作
- [ ] 前端无需修改
- [ ] 现有测试继续通过

---

## 6. 常见问题

### Q: 如果测试失败怎么办？

**A**: 快速回滚
```python
# backend/app/main.py
# 注释掉这一行即可回滚
# app.add_middleware(RequestContextMiddleware)
```

### Q: 现有代码需要修改吗？

**A**: 不需要！现有的 `Depends(get_current_user)` 继续工作。
新代码可以选择使用 `get_current_user()` 从上下文获取。

### Q: MCP 服务怎么部署？

**A**: 有两种方式：
1. 独立进程：`python app/mcp_servers/campaign_server.py`
2. 集成到主应用：在 FastAPI lifespan 中启动

### Q: 如何添加新的 MCP 工具？

**A**: 
```python
@mcp.tool()
def your_new_tool(param1: str) -> str:
    user_id = get_current_user_id()  # 获取用户
    # 业务逻辑
    return "result"
```

---

## 7. 下一步

完成验证后，可以：

1. ✅ 集成到 Agent Runtime（让 Agent 可以调用 MCP 工具）
2. ✅ 添加更多 MCP 工具（内容管理、数据分析等）
3. ✅ 逐步重构业务代码使用新的上下文 API
4. ✅ 添加日志和监控（structlog + Prometheus）

---

## 8. 参考文档

- 上下文系统实现：`backend/app/core/context.py`
- MCP 鉴权实现：`backend/app/agent_platform/mcp/`
- 示例 MCP 服务：`backend/app/mcp_servers/campaign_server.py`
- 完整架构分析：`drafts/20260612/ARCHITECTURE_ANALYSIS_*.md`

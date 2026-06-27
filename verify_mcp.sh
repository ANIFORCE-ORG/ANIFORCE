#!/bin/bash
# MCP 集成验证脚本

set -e

echo "🚀 MCP 集成验证开始..."
echo ""

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_PORT=18003
BACKEND_URL="http://localhost:$BACKEND_PORT"

# 检查后端是否运行
echo "1️⃣ 检查后端服务..."
if curl -s "$BACKEND_URL/docs" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 后端服务运行中 ($BACKEND_URL)${NC}"
else
    echo -e "${RED}✗ 后端服务未运行${NC}"
    echo "   请先启动后端: ./run_server.sh --backend-port $BACKEND_PORT"
    exit 1
fi
echo ""

# 检查 MCP 端点
echo "2️⃣ 检查 MCP 端点..."
MCP_TOOLS=$(curl -s "$BACKEND_URL/api/v1/mcp/tools" 2>/dev/null)
if [ $? -eq 0 ]; then
    TOOL_COUNT=$(echo "$MCP_TOOLS" | jq -r '.count' 2>/dev/null || echo "0")
    if [ "$TOOL_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓ MCP 端点正常，发现 $TOOL_COUNT 个工具${NC}"
        echo "   工具列表："
        echo "$MCP_TOOLS" | jq -r '.tools[] | "   - \(.name): \(.description)"' 2>/dev/null
    else
        echo -e "${YELLOW}⚠ MCP 端点响应异常${NC}"
        echo "$MCP_TOOLS"
    fi
else
    echo -e "${RED}✗ MCP 端点无法访问${NC}"
    exit 1
fi
echo ""

# 检查数据库
echo "3️⃣ 检查数据库..."
DB_FILES=(
    "backend/data/sqlite/animagus.db"
    "backend/runtime/agent/tasks.db"
    "backend/runtime/agent/sessions.db"
)

for db in "${DB_FILES[@]}"; do
    if [ -f "$db" ]; then
        echo -e "${GREEN}✓ $db${NC}"
    else
        echo -e "${YELLOW}⚠ $db 不存在${NC}"
    fi
done
echo ""

# 检查日志配置
echo "4️⃣ 检查日志配置..."
if [ -d "logs" ]; then
    LOG_FILES=$(ls -1 logs/backend_logs_*.log 2>/dev/null | head -1)
    if [ -n "$LOG_FILES" ]; then
        echo -e "${GREEN}✓ 日志目录正常 (logs/)${NC}"
        echo "   最新日志: $LOG_FILES"
    else
        echo -e "${YELLOW}⚠ 没有找到日志文件${NC}"
    fi
else
    echo -e "${YELLOW}⚠ 日志目录不存在${NC}"
fi
echo ""

# 测试 MCP 调用（需要登录）
echo "5️⃣ 测试 MCP 工具调用..."
echo "   需要手动测试："
echo ""
echo "   # 1. 登录获取 token"
echo "   TOKEN=\$(curl -s -X POST $BACKEND_URL/api/v1/auth/login \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"email\":\"test@example.com\",\"password\":\"password\"}' \\"
echo "     | jq -r '.data.access_token')"
echo ""
echo "   # 2. 直接调用 MCP 端点"
echo "   curl -X POST $BACKEND_URL/api/v1/mcp \\"
echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{"
echo "       \"jsonrpc\": \"2.0\","
echo "       \"method\": \"tools/list\","
echo "       \"id\": 1"
echo "     }'"
echo ""
echo "   # 3. 创建对话并发送消息（Agent 自动调用 MCP）"
echo "   SESSION_ID=\$(curl -s -X POST $BACKEND_URL/api/v1/agent/chat/sessions \\"
echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"title\":\"测试MCP\"}' \\"
echo "     | jq -r '.id')"
echo ""
echo "   curl -X POST $BACKEND_URL/api/v1/agent/chat/sessions/\$SESSION_ID/stream \\"
echo "     -H \"Authorization: Bearer \$TOKEN\" \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"message\":\"帮我创建一个测试项目，预算5万元\"}'"
echo ""

# 检查关键文件
echo "6️⃣ 检查关键文件..."
KEY_FILES=(
    "backend/app/api/v1/mcp.py"
    "backend/app/core/context.py"
    "backend/app/middleware/context.py"
    "backend/app/agent_platform/runtime.py"
    "backend/app/agent_platform/adapters/openai_adapter.py"
)

ALL_EXISTS=true
for file in "${KEY_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ $file${NC}"
    else
        echo -e "${RED}✗ $file 缺失${NC}"
        ALL_EXISTS=false
    fi
done
echo ""

if [ "$ALL_EXISTS" = true ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ MCP 集成验证通过！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "📋 下一步："
    echo "  1. 使用上面的命令测试 MCP 工具调用"
    echo "  2. 在前端创建对话并发送消息"
    echo "  3. 观察 Agent 自动调用 MCP 工具"
    echo "  4. 查看日志: tail -f logs/backend_logs_*.log | grep MCP"
    echo ""
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ 验证失败：有文件缺失${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi

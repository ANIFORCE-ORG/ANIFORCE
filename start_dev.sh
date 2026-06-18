#!/bin/bash
# ANIFORCE 一键启动开发环境
# 启动 backend (8010) + agent (8020) + frontend (5173)
# 日志输出到 logs/backend.log, logs/agent.log, logs/frontend.log

set -e

cd "$(dirname "$0")"

echo "=============================================="
echo "  ANIFORCE 开发环境一键启动"
echo "=============================================="

# ---- 1. 清理端口（杀旧进程） ----
echo ""
echo "🧹 清理旧进程..."

# backend 端口 8010
pkill -f 'uvicorn.*8010' 2>/dev/null || true
# agent 端口 8020  
pkill -f 'uvicorn.*8020' 2>/dev/null || true
pkill -f 'uvicorn.*app.main:app' 2>/dev/null || true
# frontend 端口 5173
pkill -f 'vite.*5173' 2>/dev/null || true

sleep 2

# 确认端口已释放
echo "   端口状态检查:"
for port in 8010 8020 5173; do
    if ss -ltn | grep -q ":${port}"; then
        echo "   ❌ 端口 ${port} 仍被占用，强制清理..."
        ss -ltnp | grep ":${port}" | awk '{print $7}' | sed 's/pid=//' | cut -d, -f1 | xargs -r kill -9 2>/dev/null || true
    else
        echo "   ✓ 端口 ${port} 已释放"
    fi
done

sleep 1

# ---- 2. 创建日志目录和清理旧日志 ----
mkdir -p logs
rm -f logs/backend.log logs/agent.log logs/frontend.log logs/start_dev_combined.log

run_clean() {
    env -u VIRTUAL_ENV -u PYTHONPATH -u PYTHONHOME "$@"
}

echo ""
echo "📝 日志输出到:"
echo "   backend: logs/backend.log"
echo "   agent:   logs/agent.log"
echo "   frontend: logs/frontend.log"

# ---- 3. 启动 Backend (8010) ----
echo ""
echo "🚀 [1/3] 启动 Backend (8010)..."

cd backend
if [ ! -d .venv ]; then
    echo "   创建 backend 虚拟环境..."
    UV_CACHE_DIR=./uv_cache uv venv --python 3.11
fi

# 加载 .env
set -a
[ -f .env ] && source .env
set +a

PORT=8010
nohup env -u VIRTUAL_ENV -u PYTHONPATH -u PYTHONHOME bash -lc "echo '[backend] pwd='\$(pwd); UV_CACHE_DIR=./uv_cache uv run python -c 'import sys; print(\"[backend] python=\" + sys.executable)'; UV_CACHE_DIR=./uv_cache uv run python -m uvicorn app.main:app --host 127.0.0.1 --port ${PORT} --reload --reload-dir app" > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   PID: $BACKEND_PID"

cd ..

# ---- 4. 启动 Agent (8020) ----
echo ""
echo "🚀 [2/3] 启动 Agent (8020)..."

cd aniforce-agent
if [ ! -d .venv ]; then
    echo "   创建 agent 虚拟环境..."
    UV_CACHE_DIR=./uv_cache uv venv --python 3.11
fi

nohup env -u VIRTUAL_ENV -u PYTHONPATH -u PYTHONHOME bash -lc "echo '[agent] pwd='\$(pwd); UV_CACHE_DIR=./uv_cache uv run python -c 'import sys; print(\"[agent] python=\" + sys.executable)'; UV_CACHE_DIR=./uv_cache uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8020" > ../logs/agent.log 2>&1 &
AGENT_PID=$!
echo "   PID: $AGENT_PID"

cd ..

# ---- 5. 启动 Frontend (5173) ----
echo ""
echo "🚀 [3/3] 启动 Frontend (5173)..."

cd frontend/packages/main-app
nohup bash -lc "echo '[frontend] pwd='\$(pwd); npm_config_cache=../npm_cache npx vite --host 0.0.0.0 --port 5173" > ../../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   PID: $FRONTEND_PID"

cd ..

cd ..

# ---- 6. 等待服务就绪 ----
echo ""
echo "⏳ 等待服务启动..."

wait_http() {
    local name="$1"
    local url="$2"
    local max_wait="${3:-30}"
    local elapsed=0
    local code="000"

    while [ "$elapsed" -lt "$max_wait" ]; do
        code=$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)
        if [ "$code" = "200" ]; then
            echo "   ✅ ${name} - HTTP ${code}"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    echo "   ❌ ${name} - HTTP ${code}"
    return 1
}

# ---- 7. Health Check ----
echo ""
echo "🔍 服务健康检查:"

wait_http "Backend (8010)" "http://127.0.0.1:8010/health" 30 || true
wait_http "Agent (8020)" "http://localhost:8020/health" 30 || true
wait_http "Frontend (5173)" "http://localhost:5173/" 30 || true

# ---- 8. 输出访问地址 ----
echo ""
echo "=============================================="
echo "  🎉 服务启动完成"
echo "=============================================="
echo ""
echo "📍 访问地址:"
echo "   Backend API:  http://127.0.0.1:8010/docs"
echo "   Agent API:    http://localhost:8020/docs"
echo "   Frontend:     http://localhost:5173/"
echo "   驾驶舱:       http://localhost:5173/home"
echo ""
echo "📝 查看日志:"
echo "   tail -f logs/backend.log"
echo "   tail -f logs/agent.log"
echo "   tail -f logs/frontend.log"
echo ""
echo "🛑 停止服务:"
echo "   pkill -f 'uvicorn.*8010'"
echo "   pkill -f 'uvicorn.*8020'"
echo "   pkill -f 'vite.*5173'"
echo ""
echo "=============================================="
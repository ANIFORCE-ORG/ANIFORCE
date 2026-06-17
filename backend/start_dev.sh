#!/bin/bash
# ANIFORCE Backend 开发服务启动脚本

set -e

cd "$(dirname "$0")"

echo "🚀 启动 ANIFORCE Backend 服务（热重载模式）"

# 加载环境变量
if [ ! -f .env ]; then
    echo "❌ .env 文件不存在"
    exit 1
fi

set -a
source .env
set +a

# 创建日志目录
mkdir -p logs

# 检查虚拟环境
if [ ! -d .venv ]; then
    echo "⚠️  虚拟环境不存在，正在创建..."
    UV_CACHE_DIR=./uv_cache uv venv --python 3.11
fi

# 获取端口（默认 18003）
PORT=${PORT:-18003}

echo "📍 服务将运行在: http://127.0.0.1:${PORT}"
echo "📝 API 文档: http://127.0.0.1:${PORT}/docs"
echo ""

# 启动服务（热重载模式）
UV_CACHE_DIR=./uv_cache uv run python -m uvicorn app.main:app \
    --host 127.0.0.1 \
    --port ${PORT} \
    --reload \
    --reload-dir app \
    --log-level info

# 服务关闭后执行清理
echo "服务已停止"

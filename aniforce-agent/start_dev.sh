#!/bin/bash
# ANIFORCE Agent 开发服务启动脚本

set -e

cd "$(dirname "$0")"

echo "🚀 启动 ANIFORCE Agent 服务（热重载模式）"

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

# 启动服务（热重载模式）
.venv/bin/python -m uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8020 \
    --reload \
    --reload-dir app \
    --log-level info

# 服务关闭后执行清理
echo "服务已停止"

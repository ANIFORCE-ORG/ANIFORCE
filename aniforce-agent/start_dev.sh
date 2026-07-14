#!/usr/bin/env bash
# OpenAI Agent Service 一键启动脚本
# - 固定端口：18020
# - 启动前释放端口
# - 日志覆盖写入：logs/YYYYMMDD.dev.agent.uvicorn.log

set -euo pipefail
cd "$(dirname "$0")"

PORT=18020
LOG_DATE="$(date +%Y%m%d)"
LOG_ENV="${LOG_ENV:-dev}"
LOG_FILE="logs/${LOG_DATE}.${LOG_ENV}.agent.uvicorn.log"

mkdir -p logs runtime/agent runtime/skills runtime/agent/sandbox uv_cache

printf '\n==============================================\n'
printf '  OpenAI Agent Service 启动\n'
printf '==============================================\n\n'

printf '🧹 清理端口 %s...\n' "$PORT"
PIDS=""
if command -v ss >/dev/null 2>&1; then
  PIDS=$(ss -ltnp "sport = :${PORT}" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u | tr '\n' ' ' || true)
fi

if [ -n "${PIDS// }" ]; then
  printf '   发现占用进程: %s\n' "$PIDS"
  kill $PIDS 2>/dev/null || true
  sleep 2
fi

PIDS_AFTER=""
if command -v ss >/dev/null 2>&1; then
  PIDS_AFTER=$(ss -ltnp "sport = :${PORT}" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u | tr '\n' ' ' || true)
fi

if [ -n "${PIDS_AFTER// }" ]; then
  printf '   端口仍被占用，强制 kill: %s\n' "$PIDS_AFTER"
  kill -9 $PIDS_AFTER 2>/dev/null || true
  sleep 1
fi
printf '   ✓ 端口 %s 已释放\n\n' "$PORT"

printf '🧹 覆盖日志 %s...\n' "$LOG_FILE"
: > "$LOG_FILE"
printf '   ✓ 日志已清空\n\n'

if [ ! -d ".venv" ]; then
  printf '🐍 创建 Python 3.11 虚拟环境...\n'
  UV_CACHE_DIR=./uv_cache uv venv --python 3.11
fi

printf '🚀 启动 Agent Service，端口 %s...\n' "$PORT"
PORT="$PORT" UV_CACHE_DIR=./uv_cache nohup uv run python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" > "$LOG_FILE" 2>&1 &
PID=$!
printf '   PID: %s\n\n' "$PID"

printf '⏳ 等待服务就绪...\n'
READY=0
for _ in $(seq 1 30); do
  CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${PORT}/health" 2>/dev/null || true)
  if [ "$CODE" = "200" ]; then
    READY=1
    break
  fi
  sleep 1
done

if [ "$READY" = "1" ]; then
  printf '   ✅ 服务就绪\n\n'
else
  printf '   ❌ 服务未就绪\n\n'
  printf '最近日志：\n'
  tail -40 "$LOG_FILE" || true
  exit 1
fi

printf '==============================================\n'
printf '  🎉 Agent Service 启动完成\n'
printf '==============================================\n'
printf 'Health:   http://localhost:%s/health\n' "$PORT"
printf 'MCP:      http://localhost:%s/mcp\n' "$PORT"
printf 'Runs API: http://localhost:%s/api/agent/runs\n' "$PORT"
printf 'Log:      tail -f %s\n' "$LOG_FILE"
printf '==============================================\n'

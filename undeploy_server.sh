#!/usr/bin/env bash
# ============================================================
#  ANIFORCE 统一停止脚本
#  用法: ./undeploy_server.sh [--only all|agent|backend|frontend|nginx|phoenix]
# ============================================================
set -euo pipefail

# ---------- 颜色 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_CONFIG="$ROOT_DIR/.deploy_config"
NGINX_RUNTIME_CONF="$ROOT_DIR/.nginx_runtime.conf"
NGINX_PID_FILE="$ROOT_DIR/.nginx.pid"

# ---------- 默认参数 ----------
NGINX_PORT=80
FRONTEND_PORT=3010
BACKEND_PORT=8010
AGENT_PORT=8020
PHOENIX_PORT=6006
ONLY=all
WITH_NGINX=0
WITH_PHOENIX=0
WITHOUT_AGENT=0
HAS_DEPLOY_CONFIG=0
SHOW_HELP=0

for arg in "$@"; do
  case "$arg" in
    -h|--help) SHOW_HELP=1 ;;
  esac
done

# 从配置文件读取
if [ -f "$DEPLOY_CONFIG" ]; then
  HAS_DEPLOY_CONFIG=1
  source "$DEPLOY_CONFIG"
  info "从配置文件读取: ONLY=${ONLY}, WITH_NGINX=${WITH_NGINX}, WITH_PHOENIX=${WITH_PHOENIX}, WITHOUT_AGENT=${WITHOUT_AGENT}"
elif [ "$SHOW_HELP" -ne 1 ]; then
  warn "未找到部署配置文件: ${DEPLOY_CONFIG}，将仅停止可确认由当前部署启动的服务"
fi

DEPLOYED_ONLY="$ONLY"

DEPLOYED_WITH_NGINX=0
if [ "$HAS_DEPLOY_CONFIG" -eq 1 ] && [ "$WITH_NGINX" -eq 1 ] && { [ "$DEPLOYED_ONLY" = "all" ] || [ "$DEPLOYED_ONLY" = "nginx" ]; }; then
  DEPLOYED_WITH_NGINX=1
fi

DEPLOYED_WITH_AGENT=0
if [ "$HAS_DEPLOY_CONFIG" -eq 1 ] && [ "$WITHOUT_AGENT" -ne 1 ] && { [ "$DEPLOYED_ONLY" = "all" ] || [ "$DEPLOYED_ONLY" = "agent" ]; }; then
  DEPLOYED_WITH_AGENT=1
fi

DEPLOYED_WITH_PHOENIX=0
if [ "$HAS_DEPLOY_CONFIG" -eq 1 ] && { [ "$DEPLOYED_ONLY" = "phoenix" ] || { [ "$WITH_PHOENIX" -eq 1 ] && { [ "$DEPLOYED_ONLY" = "all" ] || [ "$DEPLOYED_ONLY" = "agent" ]; }; }; }; then
  DEPLOYED_WITH_PHOENIX=1
fi

# 命令行参数可覆盖
while [[ $# -gt 0 ]]; do
  case "$1" in
    --only) ONLY="$2"; shift 2 ;;
    --nginx-port) NGINX_PORT="$2"; shift 2 ;;
    --frontend-port) FRONTEND_PORT="$2"; shift 2 ;;
    --backend-port) BACKEND_PORT="$2"; shift 2 ;;
    --agent-port) AGENT_PORT="$2"; shift 2 ;;
    --phoenix-port) PHOENIX_PORT="$2"; shift 2 ;;
    -h|--help)
      echo "用法: $0 [选项]"
      echo ""
      echo "选项:"
      echo "  --only           仅停止: all(默认) / agent / backend / frontend / nginx / phoenix"
      echo "  --nginx-port     Nginx 端口 (默认: 80)"
      echo "  --frontend-port  前端端口 (默认: 3010)"
      echo "  --backend-port   后端端口 (默认: 8010)"
      echo "  --agent-port     Agent 服务端口 (默认: 8020)"
      echo "  --phoenix-port   Phoenix 端口 (默认: 6006)"
      echo ""
      echo "示例:"
      echo "  # 停止所有服务"
      echo "  $0"
      echo ""
      echo "  # 仅停止 Nginx"
      echo "  $0 --only nginx"
      exit 0 ;;
    *) fail "未知参数: $1  (使用 --help 查看帮助)" ;;
  esac
done

STOPPED=0

echo ""
info "========== 停止 ANIFORCE 服务 (ONLY=${ONLY}, DEPLOYED_ONLY=${DEPLOYED_ONLY}, WITH_NGINX=${WITH_NGINX}, WITH_PHOENIX=${WITH_PHOENIX}, WITHOUT_AGENT=${WITHOUT_AGENT}) =========="

# ============================================================
#  1. 停止 Nginx
# ============================================================
if [ "$ONLY" = "agent" ] || [ "$ONLY" = "backend" ] || [ "$ONLY" = "frontend" ] || [ "$ONLY" = "phoenix" ]; then
  warn "--only=$ONLY: 跳过 Nginx 停止"
elif [ "$DEPLOYED_WITH_NGINX" -ne 1 ]; then
  warn "当前部署未启动 Nginx: 跳过 Nginx 停止，避免误杀端口 ${NGINX_PORT} 上的其它服务"
else
  info "========== 停止 Nginx =========="

  NGINX_PIDS=""
  if [ -f "$NGINX_PID_FILE" ]; then
    NGINX_PIDS="$(cat "$NGINX_PID_FILE" 2>/dev/null || true)"
  fi

  if [ -z "$NGINX_PIDS" ]; then
    NGINX_CONF_MATCH="${NGINX_RUNTIME_CONF//./\\.}"
    NGINX_PIDS="$(pgrep -f "nginx.*$NGINX_CONF_MATCH" 2>/dev/null || true)"
  fi

  if [ -n "$NGINX_PIDS" ]; then
    info "检测到当前部署的 Nginx 进程，正在停止..."
    if command -v nginx &>/dev/null; then
      nginx -s quit -c "$NGINX_RUNTIME_CONF" 2>/dev/null || sudo nginx -s quit -c "$NGINX_RUNTIME_CONF" 2>/dev/null || true
    fi

    sleep 1
    for pid in $NGINX_PIDS; do
      if kill -0 "$pid" 2>/dev/null; then
        info "正在终止 Nginx 进程 PID $pid..."
        if kill "$pid" 2>/dev/null || sudo kill "$pid" 2>/dev/null; then
          ok "已停止 Nginx 进程 PID $pid"
          STOPPED=$((STOPPED + 1))
        fi
      else
        ok "Nginx 进程 PID $pid 已停止"
        STOPPED=$((STOPPED + 1))
      fi
    done

    sleep 1
    for pid in $NGINX_PIDS; do
      if kill -0 "$pid" 2>/dev/null; then
        warn "Nginx 进程 PID $pid 仍在运行，强制终止..."
        kill -9 "$pid" 2>/dev/null || sudo kill -9 "$pid" 2>/dev/null || true
      fi
    done
  else
    warn "未找到与当前部署匹配的 Nginx 进程，跳过停止"
  fi

  rm -f "$NGINX_RUNTIME_CONF" "$NGINX_PID_FILE"
fi

# ============================================================
#  2. 停止后端服务
# ============================================================
if [ "$ONLY" = "agent" ] || [ "$ONLY" = "nginx" ] || [ "$ONLY" = "frontend" ] || [ "$ONLY" = "phoenix" ]; then
  warn "--only=$ONLY: 跳过后端停止"
else
  info "========== 停止后端服务 =========="
  
  # 按已配置端口清理，避免误杀其他工作目录中的 uvicorn。
  BACKEND_PIDS=$(lsof -ti :$BACKEND_PORT 2>/dev/null || true)
  if [ -n "$BACKEND_PIDS" ]; then
    info "检测到端口 $BACKEND_PORT 上的进程，正在终止..."
    for pid in $BACKEND_PIDS; do
      if kill "$pid" 2>/dev/null; then
        ok "已停止后端进程 PID $pid"
        STOPPED=$((STOPPED + 1))
      fi
    done
    sleep 1
    if lsof -i :$BACKEND_PORT -sTCP:LISTEN &>/dev/null; then
      warn "端口 $BACKEND_PORT 仍被占用，强制终止..."
      lsof -ti :$BACKEND_PORT 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    fi
  fi

  WORKER_PIDS=$(pgrep -f "$ROOT_DIR/backend/.venv/bin/python scripts/run_agent_(worker|reconcile_worker)\\.py" 2>/dev/null || true)
  if [ -n "$WORKER_PIDS" ]; then
    info "检测到 Agent Worker，正在终止..."
    echo "$WORKER_PIDS" | xargs kill 2>/dev/null || true
    STOPPED=$((STOPPED + 1))
  fi
fi

# ============================================================
#  3. 停止 Agent 服务
# ============================================================
if [ "$ONLY" = "nginx" ] || [ "$ONLY" = "backend" ] || [ "$ONLY" = "frontend" ] || [ "$ONLY" = "phoenix" ]; then
  warn "--only=$ONLY: 跳过 Agent 停止"
elif [ "$DEPLOYED_WITH_AGENT" -ne 1 ]; then
  warn "当前部署未启动 Agent: 跳过 Agent 停止，避免误杀端口 ${AGENT_PORT} 上的其它服务"
else
  info "========== 停止 Agent 服务 =========="

  AGENT_PIDS=$(lsof -ti :$AGENT_PORT 2>/dev/null || true)
  if [ -n "$AGENT_PIDS" ]; then
    info "检测到端口 $AGENT_PORT 上的进程，正在终止..."
    for pid in $AGENT_PIDS; do
      if kill "$pid" 2>/dev/null; then
        ok "已停止 Agent 进程 PID $pid"
        STOPPED=$((STOPPED + 1))
      fi
    done
    sleep 1

    if lsof -i :$AGENT_PORT -sTCP:LISTEN &>/dev/null; then
      warn "端口 $AGENT_PORT 仍被占用，强制终止..."
      lsof -ti :$AGENT_PORT 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    fi
  fi
fi

# ============================================================
#  4. 停止 Phoenix 服务
# ============================================================
if [ "$ONLY" = "nginx" ] || [ "$ONLY" = "agent" ] || [ "$ONLY" = "backend" ] || [ "$ONLY" = "frontend" ]; then
  warn "--only=$ONLY: 跳过 Phoenix 停止"
elif [ "$ONLY" != "phoenix" ] && [ "$DEPLOYED_WITH_PHOENIX" -ne 1 ]; then
  warn "当前部署未启动 Phoenix: 跳过 Phoenix 停止，避免误杀端口 ${PHOENIX_PORT} 上的其它服务"
else
  info "========== 停止 Phoenix 服务 =========="

  PHOENIX_PID_FILE="$ROOT_DIR/.deploy_phoenix_pids"
  if [ -f "$PHOENIX_PID_FILE" ]; then
    while IFS= read -r pid; do
      if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        if kill "$pid" 2>/dev/null; then
          ok "已停止 Phoenix 进程 PID $pid"
          STOPPED=$((STOPPED + 1))
        fi
      fi
    done < "$PHOENIX_PID_FILE"
  fi

  sleep 1
  PHOENIX_PIDS=$(lsof -ti :$PHOENIX_PORT 2>/dev/null || true)
  if [ -n "$PHOENIX_PIDS" ]; then
    info "检测到端口 $PHOENIX_PORT 上的 Phoenix 进程，正在终止..."
    for pid in $PHOENIX_PIDS; do
      if kill "$pid" 2>/dev/null; then
        ok "已停止 Phoenix 进程 PID $pid"
        STOPPED=$((STOPPED + 1))
      fi
    done
  fi
fi

# ============================================================
#  5. 停止前端服务
# ============================================================
if [ "$ONLY" = "nginx" ] || [ "$ONLY" = "agent" ] || [ "$ONLY" = "backend" ] || [ "$ONLY" = "phoenix" ]; then
  warn "--only=$ONLY: 跳过前端停止"
else
  info "========== 停止前端服务 =========="
  
  FRONTEND_PIDS=$(lsof -ti :$FRONTEND_PORT 2>/dev/null || true)
  if [ -n "$FRONTEND_PIDS" ]; then
    info "检测到端口 $FRONTEND_PORT 上的进程，正在终止..."
    for pid in $FRONTEND_PIDS; do
      if kill "$pid" 2>/dev/null; then
        ok "已停止前端进程 PID $pid"
        STOPPED=$((STOPPED + 1))
      fi
    done
    sleep 1

    if lsof -i :$FRONTEND_PORT -sTCP:LISTEN &>/dev/null; then
      warn "端口 $FRONTEND_PORT 仍被占用，强制终止..."
      lsof -ti :$FRONTEND_PORT 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    fi
  fi
fi

# ============================================================
#  6. 清理 PID 文件
# ============================================================
info "清理临时文件..."
rm -f "$ROOT_DIR/.server_pids" "$ROOT_DIR/.server_ports" "$ROOT_DIR/.deploy_phoenix_pids"

# 仅在停止所有服务时清理部署配置
if [ "$ONLY" = "all" ]; then
  rm -f "$DEPLOY_CONFIG"
fi

# ============================================================
#  7. 结果
# ============================================================
echo ""
if [ "$STOPPED" -gt 0 ]; then
  echo -e "${GREEN}============================================${NC}"
  echo -e "${GREEN}  ANIFORCE 服务已停止 ✓${NC}"
  echo -e "${GREEN}============================================${NC}"
else
  echo -e "${YELLOW}============================================${NC}"
  echo -e "${YELLOW}  未检测到正在运行的服务${NC}"
  echo -e "${YELLOW}============================================${NC}"
fi
echo ""

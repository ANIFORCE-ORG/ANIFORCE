#!/usr/bin/env bash
# ============================================================
#  ANIMAGUS 一键启动脚本（本地 / 云端）
#  用法:
#    ./run_server.sh [--mode local|cloud] [--frontend-port 3010] [--backend-port 8010]
#                   [--only all|backend|frontend] [--skip-install] [--host 0.0.0.0]
# ============================================================
set -euo pipefail

# ---------- 颜色 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# ---------- 默认参数 ----------
MODE=local
ONLY=all
SKIP_INSTALL=0
HOST=0.0.0.0

FRONTEND_PORT_EXPLICIT=0
BACKEND_PORT_EXPLICIT=0

# ---------- 默认端口 ----------
FRONTEND_PORT=3010
BACKEND_PORT=8010

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --frontend-port) FRONTEND_PORT="$2"; FRONTEND_PORT_EXPLICIT=1; shift 2 ;;
    --backend-port)  BACKEND_PORT="$2";  BACKEND_PORT_EXPLICIT=1; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --skip-install) SKIP_INSTALL=1; shift 1 ;;
    --host) HOST="$2"; shift 2 ;;
    -h|--help)
      echo "用法: $0 [--mode local|cloud] [--frontend-port PORT] [--backend-port PORT] [--only all|backend|frontend] [--skip-install] [--host HOST]"
      echo "  --mode           启动模式: local(默认) / cloud"
      echo "  --only           仅启动: all(默认) / backend / frontend"
      echo "  --skip-install   跳过依赖安装（云端更常用）"
      echo "  --host           监听地址（默认: 0.0.0.0）"
      echo "  --frontend-port  前端端口 (默认: 3010；cloud 模式若存在环境变量 PORT 且未显式指定 --frontend-port，将使用 PORT)"
      echo "  --backend-port   后端端口 (默认: 8010)"
      exit 0 ;;
    *) fail "未知参数: $1  (使用 --help 查看帮助)" ;;
  esac
done

if [ "$MODE" != "local" ] && [ "$MODE" != "cloud" ]; then
  fail "--mode 仅支持 local 或 cloud，当前: $MODE"
fi
if [ "$ONLY" != "all" ] && [ "$ONLY" != "backend" ] && [ "$ONLY" != "frontend" ]; then
  fail "--only 仅支持 all/backend/frontend，当前: $ONLY"
fi

# cloud 模式下，若设置了 PORT 且用户没显式指定 --frontend-port，则使用 PORT 作为前端端口
if [ "$MODE" = "cloud" ] && [ -n "${PORT:-}" ]; then
  if [ "$FRONTEND_PORT_EXPLICIT" -eq 0 ]; then
    FRONTEND_PORT="$PORT"
  fi
fi

info "启动模式: MODE=$MODE, ONLY=$ONLY, SKIP_INSTALL=$SKIP_INSTALL, HOST=$HOST"
info "端口配置: 前端=$FRONTEND_PORT, 后端=$BACKEND_PORT"

# ---------- 项目根目录 ----------
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# ---------- PID & 端口信息文件（用于清理） ----------
PID_FILE="$ROOT_DIR/.server_pids"
PORT_FILE="$ROOT_DIR/.server_ports"
: > "$PID_FILE"
echo "FRONTEND_PORT=$FRONTEND_PORT" > "$PORT_FILE"
echo "BACKEND_PORT=$BACKEND_PORT" >> "$PORT_FILE"
echo "MODE=$MODE" >> "$PORT_FILE"
echo "ONLY=$ONLY" >> "$PORT_FILE"

cleanup() {
  echo ""
  info "正在停止服务..."
  while IFS= read -r pid; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null && ok "已停止进程 $pid" || true
    fi
  done < "$PID_FILE"
  rm -f "$PID_FILE" "$PORT_FILE"
  ok "所有服务已停止，再见！"
  exit 0
}
trap cleanup SIGINT SIGTERM

# ============================================================
#  1. 环境检测
# ============================================================
info "========== 环境检测 =========="

# --- Python ---
if [ -f "$BACKEND_DIR/venv/bin/python" ]; then
  PY="$BACKEND_DIR/venv/bin/python"
else
  PY=$(command -v python3 || command -v python)
fi
if [ -z "$PY" ]; then
  fail "未找到 Python 3，请先安装 Python"
fi
PY_VER=$($PY --version 2>&1 | awk '{print $2}')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  fail "Python 版本过低 ($PY_VER)，需要 3.10+"
fi
ok "Python $PY_VER"

# --- Node.js ---
if ! command -v node &>/dev/null; then
  fail "未检测到 Node.js，请先安装 Node.js 20+"
fi
NODE_VER=$(node -v | sed 's/v//')
NODE_MAJOR=$(echo "$NODE_VER" | cut -d. -f1)
if [ "$NODE_MAJOR" -lt 20 ]; then
  fail "Node.js 版本过低 ($NODE_VER)，需要 20+"
fi
ok "Node.js $NODE_VER"

# --- pnpm ---
if command -v pnpm &>/dev/null; then
  PNPM_VER=$(pnpm -v)
  ok "pnpm $PNPM_VER"
else
  if [ "$SKIP_INSTALL" -eq 1 ]; then
    warn "未检测到 pnpm，但启用了 --skip-install，将继续（若需要启动前端请确保 pnpm 已安装）"
  else
    warn "未检测到 pnpm，正在安装..."
    npm install -g pnpm@latest || fail "pnpm 安装失败"
    PNPM_VER=$(pnpm -v)
    ok "pnpm $PNPM_VER"
  fi
fi

# ============================================================
#  2. 后端依赖安装
# ============================================================
info "========== 后端依赖 =========="

cd "$BACKEND_DIR"

# 虚拟环境
if [ ! -d "venv/bin" ] && [ ! -d "venv/Scripts" ]; then
  info "创建 Python 虚拟环境..."
  $PY -m venv venv
fi

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
  source venv/Scripts/activate
fi
ok "虚拟环境已激活"

# 安装依赖
if [ "$ONLY" = "frontend" ]; then
  warn "--only=frontend：跳过后端依赖安装"
elif [ "$SKIP_INSTALL" -eq 1 ]; then
  warn "已启用 --skip-install，跳过后端依赖安装"
else
  info "安装 Python 依赖..."
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
  ok "后端依赖安装完成"
fi

# .env 文件
if [ ! -f ".env" ]; then
  warn ".env 文件不存在，从 .env.example 复制..."
  cp .env.example .env
  ok "已创建 .env（Demo 模式）"
else
  ok ".env 已存在"
fi

# ============================================================
#  3. 前端依赖安装
# ============================================================
info "========== 前端依赖 =========="

cd "$FRONTEND_DIR"

if [ "$ONLY" = "backend" ]; then
  warn "--only=backend：跳过前端依赖安装"
elif [ "$SKIP_INSTALL" -eq 1 ]; then
  warn "已启用 --skip-install，跳过前端依赖安装"
else
  if [ ! -d "node_modules" ] || [ ! -f "node_modules/.pnpm/lock.yaml" ]; then
    info "安装前端依赖 (pnpm install)..."
    pnpm install --frozen-lockfile 2>/dev/null || pnpm install
    ok "前端依赖安装完成"
  else
    ok "前端依赖已存在，跳过安装"
  fi
fi

# ============================================================
#  4. 启动后端服务
# ============================================================
if [ "$ONLY" = "frontend" ]; then
  warn "--only=frontend：跳过后端启动"
else
  info "========== 启动后端 =========="

  cd "$BACKEND_DIR"

# 检查后端端口
if lsof -i :$BACKEND_PORT -sTCP:LISTEN &>/dev/null; then
  warn "端口 $BACKEND_PORT 已被占用，尝试终止..."
  lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null || true
  sleep 1
fi

  info "启动 FastAPI 后端 (http://localhost:$BACKEND_PORT)..."
  UVICORN_RELOAD_FLAG="--reload"
  UVICORN_WORKERS_FLAG=""
  if [ "$MODE" = "cloud" ]; then
    UVICORN_RELOAD_FLAG=""
    UVICORN_WORKERS_FLAG="--workers 2"
  fi

  $PY -m uvicorn app.main:app --host "$HOST" --port "$BACKEND_PORT" $UVICORN_WORKERS_FLAG $UVICORN_RELOAD_FLAG &
  BACKEND_PID=$!
  echo "$BACKEND_PID" >> "$PID_FILE"
  sleep 2

  if kill -0 "$BACKEND_PID" 2>/dev/null; then
    ok "后端已启动 (PID: $BACKEND_PID)"
  else
    fail "后端启动失败，请检查日志"
  fi
fi

# ============================================================
#  5. 启动前端服务
# ============================================================
if [ "$ONLY" = "backend" ]; then
  warn "--only=backend：跳过前端启动"
else
  info "========== 启动前端 =========="

cd "$FRONTEND_DIR"

# 检查前端端口
if lsof -i :$FRONTEND_PORT -sTCP:LISTEN &>/dev/null; then
  warn "端口 $FRONTEND_PORT 已被占用，尝试终止..."
  lsof -ti :$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
  sleep 1
fi

  info "启动 Vite 前端 (http://localhost:$FRONTEND_PORT)..."
  VITE_BACKEND_HOST=${VITE_BACKEND_HOST:-127.0.0.1} VITE_FRONTEND_PORT=$FRONTEND_PORT VITE_BACKEND_PORT=$BACKEND_PORT pnpm dev &
  FRONTEND_PID=$!
  echo "$FRONTEND_PID" >> "$PID_FILE"
  sleep 3

  if kill -0 "$FRONTEND_PID" 2>/dev/null; then
    ok "前端已启动 (PID: $FRONTEND_PID)"
  else
    fail "前端启动失败，请检查日志"
  fi
fi

# ============================================================
#  6. 完成
# ============================================================

# 获取本机 Network IP（优先取第一个非 127 的 IPv4）
get_network_ip() {
  ip -4 addr show 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '^127\.' | head -1 || hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost"
}
NETWORK_IP=$(get_network_ip)

echo ""
echo -e "${GREEN}============================================${NC}"
if [ "$MODE" = "cloud" ]; then
  echo -e "${GREEN}  ANIMAGUS 云端服务已启动！${NC}"
else
  echo -e "${GREEN}  ANIMAGUS 本地服务已启动！${NC}"
fi
echo -e "${GREEN}============================================${NC}"
echo ""
if [ "$ONLY" != "backend" ]; then
  echo -e "  前端 (本地):   ${CYAN}http://localhost:$FRONTEND_PORT${NC}"
  echo -e "  前端 (网络):   ${CYAN}http://$NETWORK_IP:$FRONTEND_PORT${NC}"
fi
if [ "$ONLY" != "frontend" ]; then
  echo -e "  后端 (本地):   ${CYAN}http://localhost:$BACKEND_PORT${NC}"
  echo -e "  后端 (网络):   ${CYAN}http://$NETWORK_IP:$BACKEND_PORT${NC}"
  echo -e "  API 文档:      ${CYAN}http://$NETWORK_IP:$BACKEND_PORT/docs${NC}"
fi
echo ""
echo -e "  按 ${YELLOW}Ctrl+C${NC} 停止所有服务"
echo ""

# 自动打开浏览器访问前端（cloud 模式默认不打开）
if [ "$MODE" = "local" ]; then
  if command -v open &>/dev/null; then
    open "http://localhost:$FRONTEND_PORT"
  elif command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:$FRONTEND_PORT"
  fi
fi

# 保持脚本运行，等待 Ctrl+C
wait

#!/usr/bin/env bash
# ============================================================
#  ANIMAGUS 一键本地部署脚本
#  用法: ./run_server.sh [--frontend-port 3010] [--backend-port 8010]
# ============================================================
set -euo pipefail

# ---------- 颜色 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# ---------- 默认端口 & 参数解析 ----------
FRONTEND_PORT=3010
BACKEND_PORT=8010

while [[ $# -gt 0 ]]; do
  case "$1" in
    --frontend-port) FRONTEND_PORT="$2"; shift 2 ;;
    --backend-port)  BACKEND_PORT="$2";  shift 2 ;;
    -h|--help)
      echo "用法: $0 [--frontend-port PORT] [--backend-port PORT]"
      echo "  --frontend-port  前端端口 (默认: 3010)"
      echo "  --backend-port   后端端口 (默认: 8010)"
      exit 0 ;;
    *) fail "未知参数: $1  (使用 --help 查看帮助)" ;;
  esac
done

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
if command -v python3 &>/dev/null; then
  PY="python3"
elif command -v python &>/dev/null; then
  PY="python"
else
  fail "未检测到 Python，请先安装 Python 3.10+"
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
if ! command -v pnpm &>/dev/null; then
  warn "未检测到 pnpm，正在安装..."
  npm install -g pnpm@latest || fail "pnpm 安装失败"
fi
PNPM_VER=$(pnpm -v)
ok "pnpm $PNPM_VER"

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
info "安装 Python 依赖..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
ok "后端依赖安装完成"

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

if [ ! -d "node_modules" ] || [ ! -f "node_modules/.pnpm/lock.yaml" ]; then
  info "安装前端依赖 (pnpm install)..."
  pnpm install --frozen-lockfile 2>/dev/null || pnpm install
  ok "前端依赖安装完成"
else
  ok "前端依赖已存在，跳过安装"
fi

# ============================================================
#  4. 启动后端服务
# ============================================================
info "========== 启动后端 =========="

cd "$BACKEND_DIR"

# 检查后端端口
if lsof -i :$BACKEND_PORT -sTCP:LISTEN &>/dev/null; then
  warn "端口 $BACKEND_PORT 已被占用，尝试终止..."
  lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null || true
  sleep 1
fi

info "启动 FastAPI 后端 (http://localhost:$BACKEND_PORT)..."
$PY -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload &
BACKEND_PID=$!
echo "$BACKEND_PID" >> "$PID_FILE"
sleep 2

if kill -0 "$BACKEND_PID" 2>/dev/null; then
  ok "后端已启动 (PID: $BACKEND_PID)"
else
  fail "后端启动失败，请检查日志"
fi

# ============================================================
#  5. 启动前端服务
# ============================================================
info "========== 启动前端 =========="

cd "$FRONTEND_DIR"

# 检查前端端口
if lsof -i :$FRONTEND_PORT -sTCP:LISTEN &>/dev/null; then
  warn "端口 $FRONTEND_PORT 已被占用，尝试终止..."
  lsof -ti :$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
  sleep 1
fi

info "启动 Vite 前端 (http://localhost:$FRONTEND_PORT)..."
VITE_FRONTEND_PORT=$FRONTEND_PORT VITE_BACKEND_PORT=$BACKEND_PORT pnpm dev &
FRONTEND_PID=$!
echo "$FRONTEND_PID" >> "$PID_FILE"
sleep 3

if kill -0 "$FRONTEND_PID" 2>/dev/null; then
  ok "前端已启动 (PID: $FRONTEND_PID)"
else
  fail "前端启动失败，请检查日志"
fi

# ============================================================
#  6. 完成
# ============================================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  ANIMAGUS 本地服务已全部启动！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "  前端:  ${CYAN}http://localhost:$FRONTEND_PORT${NC}"
echo -e "  后端:  ${CYAN}http://localhost:$BACKEND_PORT${NC}"
echo -e "  API 文档: ${CYAN}http://localhost:$BACKEND_PORT/docs${NC}"
echo ""
echo -e "  按 ${YELLOW}Ctrl+C${NC} 停止所有服务"
echo ""

# 自动打开浏览器访问前端
if command -v open &>/dev/null; then
  open "http://localhost:$FRONTEND_PORT"
elif command -v xdg-open &>/dev/null; then
  xdg-open "http://localhost:$FRONTEND_PORT"
fi

# 保持脚本运行，等待 Ctrl+C
wait

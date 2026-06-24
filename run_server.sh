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

# ---------- 跨平台端口检查函数 ----------
check_port_in_use() {
  local port=$1
  
  # 方法1: 尝试使用 lsof（macOS 和部分 Linux）
  if command -v lsof &>/dev/null; then
    lsof -i :$port -sTCP:LISTEN &>/dev/null && return 0
  fi
  
  # 方法2: 尝试使用 ss（现代 Linux）
  if command -v ss &>/dev/null; then
    ss -ltn | grep -q ":$port " && return 0
  fi
  
  # 方法3: 尝试使用 netstat（传统 Linux/Unix）
  if command -v netstat &>/dev/null; then
    netstat -ltn 2>/dev/null | grep -q ":$port " && return 0
  fi
  
  # 方法4: 尝试连接端口（最后的手段）
  if command -v nc &>/dev/null; then
    nc -z localhost $port &>/dev/null && return 0
  fi
  
  # 如果所有方法都不可用，返回失败（假设端口未占用）
  return 1
}

# ---------- 跨平台杀死端口进程函数 ----------
kill_port_process() {
  local port=$1
  
  # 方法1: 使用 lsof（macOS 和部分 Linux）
  if command -v lsof &>/dev/null; then
    local pids=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pids" ]; then
      echo "$pids" | xargs kill -9 2>/dev/null || true
      return 0
    fi
  fi
  
  # 方法2: 使用 fuser（Linux）
  if command -v fuser &>/dev/null; then
    fuser -k $port/tcp 2>/dev/null || true
    return 0
  fi
  
  # 方法3: 使用 ss + grep + awk（现代 Linux）
  if command -v ss &>/dev/null; then
    local pids=$(ss -lptn 2>/dev/null | grep ":$port " | awk '{print $6}' | grep -oP 'pid=\K[0-9]+' | sort -u)
    if [ -n "$pids" ]; then
      echo "$pids" | xargs kill -9 2>/dev/null || true
      return 0
    fi
  fi
  
  warn "无法自动清理端口 $port，请手动检查"
  return 1
}

# ---------- 默认参数 ----------
MODE=local
ONLY=all
SKIP_INSTALL=0
HOST=0.0.0.0
DEMO_MODE=false

FRONTEND_PORT_EXPLICIT=0
BACKEND_PORT_EXPLICIT=0

# ---------- 默认端口 ----------
FRONTEND_PORT=3010
BACKEND_PORT=8010

# ---------- 日志配置 ----------
LOG_DIR="./logs"
LOG_DIR_EXPLICIT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --frontend-port) FRONTEND_PORT="$2"; FRONTEND_PORT_EXPLICIT=1; shift 2 ;;
    --backend-port)  BACKEND_PORT="$2";  BACKEND_PORT_EXPLICIT=1; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --skip-install) SKIP_INSTALL=1; shift 1 ;;
    --host) HOST="$2"; shift 2 ;;
    --demo) DEMO_MODE=true; shift 1 ;;
    --log-dir) LOG_DIR="$2"; LOG_DIR_EXPLICIT=1; shift 2 ;;
    -h|--help)
      echo "用法: $0 [--mode local|cloud] [--frontend-port PORT] [--backend-port PORT] [--only all|backend|frontend] [--skip-install] [--host HOST] [--demo] [--log-dir DIR]"
      echo ""
      echo "参数说明:"
      echo "  --mode           启动模式: local(默认) / cloud"
      echo "  --only           仅启动: all(默认) / backend / frontend"
      echo "  --skip-install   跳过依赖安装（云端更常用）"
      echo "  --host           监听地址（默认: 0.0.0.0）"
      echo "  --demo           启用 Demo 模式（设置 DEMO_MODE=true，默认: false 生产模式）"
      echo "  --frontend-port  前端端口 (默认: 3010；cloud 模式若存在环境变量 PORT 且未显式指定，将使用 PORT)"
      echo "  --backend-port   后端端口 (默认: 8010)"
      echo "  --log-dir        日志目录 (默认: ./logs)"
      echo ""
      echo "环境变量:"
      echo "  CLOUD_DOMAIN     云端模式的域名（默认: https://www.aniforce.cc）"
      echo "                   用于自动配置 .env 中的 FRONTEND_BASE_URL、BACKEND_BASE_URL 和 OAUTH_REDIRECT_BASE_URL"
      echo ""
      echo "使用场景:"
      echo "  • 本脚本用于开发调试，直接启动前后端服务（无 Nginx）"
      echo "  • 生产部署建议使用 deploy_server.sh（支持 Nginx + HTTPS）"
      echo "  • HTTPS 部署请使用: ./deploy_server.sh --mode cloud --ssl"
      echo ""
      echo "示例:"
      echo "  # 本地开发模式"
      echo "  $0 --mode local"
      echo ""
      echo "  # 云端生产模式（使用默认域名）"
      echo "  $0 --mode cloud --skip-install"
      echo ""
      echo "  # 云端模式（自定义域名）"
      echo "  CLOUD_DOMAIN=https://your-domain.com $0 --mode cloud"
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
info "环境配置: DEMO_MODE=$DEMO_MODE"
info "端口配置: 前端=$FRONTEND_PORT, 后端=$BACKEND_PORT"

# ---------- 项目根目录 ----------
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# ---------- 日志目录设置 ----------
# 转换为绝对路径
if [[ "$LOG_DIR" != /* ]]; then
  LOG_DIR="$ROOT_DIR/$LOG_DIR"
fi

# 创建日志目录
mkdir -p "$LOG_DIR"

# 生成日期标识
LOG_DATE=$(date +%Y%m%d)
LOG_ENV="$MODE"

# 日志文件路径
# 后端应用日志：使用 loguru 的时间占位符，支持自动按日期轮转
BACKEND_APP_LOG="$LOG_DIR/{time:YYYYMMDD}.${LOG_ENV}.backend.app.log"
# 后端 uvicorn 日志：使用启动时的日期
BACKEND_UVICORN_LOG="$LOG_DIR/${LOG_DATE}.${LOG_ENV}.backend.uvicorn.log"
# 前端日志：使用启动时的日期（Vite 不支持自动轮转）
FRONTEND_LOG="$LOG_DIR/${LOG_DATE}.${LOG_ENV}.frontend.vite.log"

info "日志配置: 目录=$LOG_DIR"
info "后端应用日志: $BACKEND_APP_LOG"
info "后端 Uvicorn 日志: $BACKEND_UVICORN_LOG"
info "前端日志: $FRONTEND_LOG"

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
  ok "已创建 .env"
fi

# 根据 --demo 参数设置 DEMO_MODE
if [ "$DEMO_MODE" = "true" ]; then
  info "设置 DEMO_MODE=true（Demo 模式）"
  if grep -q "^DEMO_MODE=" .env; then
    sed -i.bak 's/^DEMO_MODE=.*/DEMO_MODE=true/' .env && rm -f .env.bak
  else
    echo "DEMO_MODE=true" >> .env
  fi
  ok "Demo 模式已启用"
else
  info "设置 DEMO_MODE=false（生产模式）"
  if grep -q "^DEMO_MODE=" .env; then
    sed -i.bak 's/^DEMO_MODE=.*/DEMO_MODE=false/' .env && rm -f .env.bak
  else
    echo "DEMO_MODE=false" >> .env
  fi
  ok "生产模式已启用"
fi

# 根据 MODE 自动配置服务地址
if [ "$MODE" = "cloud" ]; then
  info "配置 Cloud 模式服务地址"
  # 使用生产域名（可通过环境变量 CLOUD_DOMAIN 指定，否则使用默认域名）
  CLOUD_DOMAIN=${CLOUD_DOMAIN:-https://www.aniforce.cc}
  
  # 更新 FRONTEND_BASE_URL（使用域名，不带端口）
  if grep -q "^FRONTEND_BASE_URL=" .env; then
    sed -i.bak "s|^FRONTEND_BASE_URL=.*|FRONTEND_BASE_URL=$CLOUD_DOMAIN|" .env && rm -f .env.bak
  else
    echo "FRONTEND_BASE_URL=$CLOUD_DOMAIN" >> .env
  fi
  
  # 更新 BACKEND_BASE_URL（使用域名，不带端口）
  if grep -q "^BACKEND_BASE_URL=" .env; then
    sed -i.bak "s|^BACKEND_BASE_URL=.*|BACKEND_BASE_URL=$CLOUD_DOMAIN|" .env && rm -f .env.bak
  else
    echo "BACKEND_BASE_URL=$CLOUD_DOMAIN" >> .env
  fi
  
  # 更新 OAUTH_REDIRECT_BASE_URL（使用域名，用于 OAuth 回调）
  if grep -q "^OAUTH_REDIRECT_BASE_URL=" .env; then
    sed -i.bak "s|^OAUTH_REDIRECT_BASE_URL=.*|OAUTH_REDIRECT_BASE_URL=$CLOUD_DOMAIN|" .env && rm -f .env.bak
  else
    echo "OAUTH_REDIRECT_BASE_URL=$CLOUD_DOMAIN" >> .env
  fi
  
  ok "Cloud 模式服务地址: 前端=$CLOUD_DOMAIN, 后端=$CLOUD_DOMAIN, OAuth回调=$CLOUD_DOMAIN"
else
  info "配置 Local 模式服务地址"
  
  # 更新 FRONTEND_BASE_URL
  if grep -q "^FRONTEND_BASE_URL=" .env; then
    sed -i.bak "s|^FRONTEND_BASE_URL=.*|FRONTEND_BASE_URL=http://localhost:$FRONTEND_PORT|" .env && rm -f .env.bak
  else
    echo "FRONTEND_BASE_URL=http://localhost:$FRONTEND_PORT" >> .env
  fi
  
  # 更新 BACKEND_BASE_URL
  if grep -q "^BACKEND_BASE_URL=" .env; then
    sed -i.bak "s|^BACKEND_BASE_URL=.*|BACKEND_BASE_URL=http://localhost:$BACKEND_PORT|" .env && rm -f .env.bak
  else
    echo "BACKEND_BASE_URL=http://localhost:$BACKEND_PORT" >> .env
  fi
  
  # 更新 OAUTH_REDIRECT_BASE_URL（本地开发时使用 localhost）
  if grep -q "^OAUTH_REDIRECT_BASE_URL=" .env; then
    sed -i.bak "s|^OAUTH_REDIRECT_BASE_URL=.*|OAUTH_REDIRECT_BASE_URL=http://localhost:$BACKEND_PORT|" .env && rm -f .env.bak
  else
    echo "OAUTH_REDIRECT_BASE_URL=http://localhost:$BACKEND_PORT" >> .env
  fi
  
  ok "Local 模式服务地址: 前端=http://localhost:$FRONTEND_PORT, 后端=http://localhost:$BACKEND_PORT, OAuth回调=http://localhost:$BACKEND_PORT"
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

  # 确保虚拟环境已激活并更新 Python 路径
  if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    PY="venv/bin/python"
  elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
    PY="venv/Scripts/python.exe"
  fi

  # 检查后端端口
if check_port_in_use $BACKEND_PORT; then
  warn "端口 $BACKEND_PORT 已被占用，尝试终止..."
  kill_port_process $BACKEND_PORT
  sleep 1
fi

  info "启动 FastAPI 后端 (http://localhost:$BACKEND_PORT)..."
  UVICORN_RELOAD_FLAG="--reload"
  UVICORN_WORKERS_FLAG=""
  if [ "$MODE" = "cloud" ]; then
    UVICORN_RELOAD_FLAG=""
    UVICORN_WORKERS_FLAG="--workers 2"
  fi

  # 启动后端并重定向日志
  # LOG_FILE: 应用日志（loguru 自动轮转）
  # >> redirect: uvicorn 服务器日志（shell 重定向）
  LOG_FILE="$BACKEND_APP_LOG" $PY -m uvicorn app.main:app --host "$HOST" --port "$BACKEND_PORT" $UVICORN_WORKERS_FLAG $UVICORN_RELOAD_FLAG >> "$BACKEND_UVICORN_LOG" 2>&1 &
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
if check_port_in_use $FRONTEND_PORT; then
  warn "端口 $FRONTEND_PORT 已被占用，尝试终止..."
  kill_port_process $FRONTEND_PORT
  sleep 1
fi

  info "启动 Vite 前端 (http://localhost:$FRONTEND_PORT)..."
  # 云端模式下使用 --host 0.0.0.0 以允许外部访问
  if [ "$MODE" = "cloud" ]; then
    VITE_BACKEND_HOST=${VITE_BACKEND_HOST:-0.0.0.0} VITE_FRONTEND_PORT=$FRONTEND_PORT VITE_BACKEND_PORT=$BACKEND_PORT pnpm dev --host 0.0.0.0 --port $FRONTEND_PORT >> "$FRONTEND_LOG" 2>&1 &
  else
    VITE_BACKEND_HOST=${VITE_BACKEND_HOST:-127.0.0.1} VITE_FRONTEND_PORT=$FRONTEND_PORT VITE_BACKEND_PORT=$BACKEND_PORT pnpm dev >> "$FRONTEND_LOG" 2>&1 &
  fi
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

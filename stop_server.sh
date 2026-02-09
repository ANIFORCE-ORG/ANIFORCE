#!/usr/bin/env bash
# ============================================================
#  ANIMAGUS 一键停止服务脚本
#  用法: ./stop_server.sh [--frontend-port 3010] [--backend-port 8010]
# ============================================================
set -euo pipefail

# ---------- 颜色 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT_DIR/.server_pids"
PORT_FILE="$ROOT_DIR/.server_ports"

# ---------- 默认端口 & 参数解析 ----------
FRONTEND_PORT=3010
BACKEND_PORT=8010

# 优先从 .server_ports 文件读取（与 run_server.sh 保持一致）
if [ -f "$PORT_FILE" ]; then
  source "$PORT_FILE"
fi

# 命令行参数可覆盖
while [[ $# -gt 0 ]]; do
  case "$1" in
    --frontend-port) FRONTEND_PORT="$2"; shift 2 ;;
    --backend-port)  BACKEND_PORT="$2";  shift 2 ;;
    -h|--help)
      echo "用法: $0 [--frontend-port PORT] [--backend-port PORT]"
      echo "  --frontend-port  前端端口 (默认: 3010)"
      echo "  --backend-port   后端端口 (默认: 8010)"
      echo "  若 run_server.sh 使用了自定义端口，脚本会自动读取"
      exit 0 ;;
    *) fail "未知参数: $1  (使用 --help 查看帮助)" ;;
  esac
done

KILLED=0

echo ""
info "========== 停止 ANIMAGUS 服务 (前端:$FRONTEND_PORT / 后端:$BACKEND_PORT) =========="

# ---------- 1. 通过 PID 文件清理 ----------
if [ -f "$PID_FILE" ]; then
  info "读取 PID 文件..."
  while IFS= read -r pid; do
    [ -z "$pid" ] && continue
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null
      ok "已停止进程 PID $pid"
      KILLED=$((KILLED + 1))
    fi
  done < "$PID_FILE"
  rm -f "$PID_FILE"
else
  warn "未找到 PID 文件，将通过端口扫描清理"
fi

# ---------- 2. 按端口清理残留进程 ----------
# 后端
if lsof -i :$BACKEND_PORT -sTCP:LISTEN &>/dev/null; then
  info "检测到端口 $BACKEND_PORT 上的进程，正在终止..."
  lsof -ti :$BACKEND_PORT | while read -r pid; do
    kill "$pid" 2>/dev/null && ok "已停止 :$BACKEND_PORT 进程 PID $pid" && KILLED=$((KILLED + 1)) || true
  done
  sleep 1
  if lsof -i :$BACKEND_PORT -sTCP:LISTEN &>/dev/null; then
    warn "端口 $BACKEND_PORT 仍被占用，强制终止..."
    lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null || true
  fi
fi

# 前端
if lsof -i :$FRONTEND_PORT -sTCP:LISTEN &>/dev/null; then
  info "检测到端口 $FRONTEND_PORT 上的进程，正在终止..."
  lsof -ti :$FRONTEND_PORT | while read -r pid; do
    kill "$pid" 2>/dev/null && ok "已停止 :$FRONTEND_PORT 进程 PID $pid" && KILLED=$((KILLED + 1)) || true
  done
  sleep 1
  if lsof -i :$FRONTEND_PORT -sTCP:LISTEN &>/dev/null; then
    warn "端口 $FRONTEND_PORT 仍被占用，强制终止..."
    lsof -ti :$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
  fi
fi

# ---------- 3. 按进程名清理（兜底） ----------
# uvicorn
if pgrep -f "uvicorn app.main:app" &>/dev/null; then
  info "检测到 uvicorn 残留进程，正在终止..."
  pkill -f "uvicorn app.main:app" 2>/dev/null && KILLED=$((KILLED + 1)) || true
fi

# vite (animagus 相关)
if pgrep -f "vite.*animagus\|vite.*main-app" &>/dev/null; then
  info "检测到 Vite 残留进程，正在终止..."
  pkill -f "vite.*animagus\|vite.*main-app" 2>/dev/null && KILLED=$((KILLED + 1)) || true
fi

# ---------- 4. 清理临时文件 ----------
rm -f "$PID_FILE" "$PORT_FILE"

# ---------- 5. 结果 ----------
echo ""
if [ "$KILLED" -gt 0 ]; then
  echo -e "${GREEN}============================================${NC}"
  echo -e "${GREEN}  所有 ANIMAGUS 服务已停止 ✓${NC}"
  echo -e "${GREEN}============================================${NC}"
else
  echo -e "${YELLOW}============================================${NC}"
  echo -e "${YELLOW}  未检测到正在运行的 ANIMAGUS 服务${NC}"
  echo -e "${YELLOW}============================================${NC}"
fi
echo ""

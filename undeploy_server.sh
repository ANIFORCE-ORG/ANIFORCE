#!/usr/bin/env bash
# ============================================================
#  ANIFORCE 统一停止脚本
#  用法: ./undeploy_server.sh [--only all|agent|backend|frontend|nginx]
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

# ---------- 默认参数 ----------
NGINX_PORT=80
FRONTEND_PORT=3010
BACKEND_PORT=8010
AGENT_PORT=8020
ONLY=all
USE_SSL=false

# 从配置文件读取
if [ -f "$DEPLOY_CONFIG" ]; then
  source "$DEPLOY_CONFIG"
  info "从配置文件读取: USE_SSL=$USE_SSL"
fi

# 命令行参数可覆盖
while [[ $# -gt 0 ]]; do
  case "$1" in
    --only) ONLY="$2"; shift 2 ;;
    --ssl) USE_SSL=true; shift 1 ;;
    --nginx-port) NGINX_PORT="$2"; shift 2 ;;
    --frontend-port) FRONTEND_PORT="$2"; shift 2 ;;
    --backend-port) BACKEND_PORT="$2"; shift 2 ;;
    --agent-port) AGENT_PORT="$2"; shift 2 ;;
    -h|--help)
      echo "用法: $0 [选项]"
      echo ""
      echo "选项:"
      echo "  --only           仅停止: all(默认) / agent / backend / frontend / nginx"
      echo "  --ssl            停止 HTTPS 模式的 Nginx"
      echo "  --nginx-port     Nginx 端口 (默认: 80)"
      echo "  --frontend-port  前端端口 (默认: 3010)"
      echo "  --backend-port   后端端口 (默认: 8010)"
      echo "  --agent-port     Agent 服务端口 (默认: 8020)"
      echo ""
      echo "示例:"
      echo "  # 停止所有服务"
      echo "  $0"
      echo ""
      echo "  # 仅停止 Nginx"
      echo "  $0 --only nginx"
      echo ""
      echo "  # 停止 HTTPS 模式"
      echo "  $0 --ssl"
      exit 0 ;;
    *) fail "未知参数: $1  (使用 --help 查看帮助)" ;;
  esac
done

STOPPED=0

echo ""
info "========== 停止 ANIFORCE 服务 (ONLY=$ONLY, USE_SSL=$USE_SSL) =========="

# ============================================================
#  1. 停止 Nginx
# ============================================================
if [ "$ONLY" = "agent" ] || [ "$ONLY" = "backend" ] || [ "$ONLY" = "frontend" ]; then
  warn "--only=$ONLY：跳过 Nginx 停止"
else
  info "========== 停止 Nginx =========="
  
  # 尝试优雅停止
  if command -v nginx &>/dev/null; then
    if [ "$USE_SSL" = "true" ]; then
      info "HTTPS 模式，使用 sudo 停止 Nginx..."
      if sudo nginx -s quit 2>/dev/null; then
        ok "Nginx 已优雅停止 (HTTPS 模式)"
        STOPPED=$((STOPPED + 1))
      else
        warn "无法优雅停止 Nginx，尝试强制停止..."
        sudo nginx -s stop 2>/dev/null || true
      fi
    else
      if nginx -s quit 2>/dev/null; then
        ok "Nginx 已优雅停止"
        STOPPED=$((STOPPED + 1))
      elif sudo nginx -s quit 2>/dev/null; then
        ok "Nginx 已优雅停止 (sudo)"
        STOPPED=$((STOPPED + 1))
      else
        warn "无法优雅停止 Nginx，尝试强制停止..."
        nginx -s stop 2>/dev/null || sudo nginx -s stop 2>/dev/null || true
      fi
    fi
  fi
  
  # 检查端口并强制清理
  # 如果是 HTTPS 模式，需要检查 80 和 443 端口
  PORTS_TO_CHECK="$NGINX_PORT"
  if [ "$USE_SSL" = "true" ]; then
    PORTS_TO_CHECK="80 443"
  fi
  
  for port in $PORTS_TO_CHECK; do
    if lsof -i :$port -sTCP:LISTEN &>/dev/null; then
      info "检测到端口 $port 上的进程，正在终止..."
      lsof -ti :$port | while read -r pid; do
        kill "$pid" 2>/dev/null && ok "已停止 Nginx 进程 PID $pid" && STOPPED=$((STOPPED + 1)) || true
      done
      sleep 1
      
      # 二次检查
      if lsof -i :$port -sTCP:LISTEN &>/dev/null; then
        warn "端口 $port 仍被占用，强制终止..."
        lsof -ti :$port | xargs kill -9 2>/dev/null || sudo lsof -ti :$port | xargs sudo kill -9 2>/dev/null || true
      fi
    fi
  done
  
  # 清理 Nginx 进程（兜底）
  if pgrep nginx &>/dev/null; then
    info "检测到 Nginx 残留进程，正在终止..."
    pkill nginx 2>/dev/null || sudo pkill nginx 2>/dev/null || true
    STOPPED=$((STOPPED + 1))
  fi
  
  # 清理运行时配置文件
  rm -f "$ROOT_DIR/.nginx_runtime.conf"
fi

# ============================================================
#  2. 停止后端服务
# ============================================================
if [ "$ONLY" = "agent" ] || [ "$ONLY" = "nginx" ] || [ "$ONLY" = "frontend" ]; then
  warn "--only=$ONLY：跳过后端停止"
else
  info "========== 停止后端服务 =========="
  
  # 通过端口清理
  if lsof -i :$BACKEND_PORT -sTCP:LISTEN &>/dev/null; then
    info "检测到端口 $BACKEND_PORT 上的进程，正在终止..."
    lsof -ti :$BACKEND_PORT | while read -r pid; do
      kill "$pid" 2>/dev/null && ok "已停止后端进程 PID $pid" && STOPPED=$((STOPPED + 1)) || true
    done
    sleep 1
    
    if lsof -i :$BACKEND_PORT -sTCP:LISTEN &>/dev/null; then
      warn "端口 $BACKEND_PORT 仍被占用，强制终止..."
      lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null || true
    fi
  fi
  
  # 通过进程名清理（兜底）
  if pgrep -f "uvicorn app.main:app" &>/dev/null; then
    info "检测到 uvicorn 残留进程，正在终止..."
    pkill -f "uvicorn app.main:app" 2>/dev/null && STOPPED=$((STOPPED + 1)) || true
  fi
fi

# ============================================================
#  3. 停止 Agent 服务
# ============================================================
if [ "$ONLY" = "nginx" ] || [ "$ONLY" = "backend" ] || [ "$ONLY" = "frontend" ]; then
  warn "--only=$ONLY：跳过 Agent 停止"
else
  info "========== 停止 Agent 服务 =========="

  if lsof -i :$AGENT_PORT -sTCP:LISTEN &>/dev/null; then
    info "检测到端口 $AGENT_PORT 上的进程，正在终止..."
    lsof -ti :$AGENT_PORT | while read -r pid; do
      kill "$pid" 2>/dev/null && ok "已停止 Agent 进程 PID $pid" && STOPPED=$((STOPPED + 1)) || true
    done
    sleep 1

    if lsof -i :$AGENT_PORT -sTCP:LISTEN &>/dev/null; then
      warn "端口 $AGENT_PORT 仍被占用，强制终止..."
      lsof -ti :$AGENT_PORT | xargs kill -9 2>/dev/null || true
    fi
  fi
fi

# ============================================================
#  4. 停止前端服务
# ============================================================
if [ "$ONLY" = "nginx" ] || [ "$ONLY" = "agent" ] || [ "$ONLY" = "backend" ]; then
  warn "--only=$ONLY：跳过前端停止"
else
  info "========== 停止前端服务 =========="
  
  # 通过端口清理
  if lsof -i :$FRONTEND_PORT -sTCP:LISTEN &>/dev/null; then
    info "检测到端口 $FRONTEND_PORT 上的进程，正在终止..."
    lsof -ti :$FRONTEND_PORT | while read -r pid; do
      kill "$pid" 2>/dev/null && ok "已停止前端进程 PID $pid" && STOPPED=$((STOPPED + 1)) || true
    done
    sleep 1
    
    if lsof -i :$FRONTEND_PORT -sTCP:LISTEN &>/dev/null; then
      warn "端口 $FRONTEND_PORT 仍被占用，强制终止..."
      lsof -ti :$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
    fi
  fi
  
  # 通过进程名清理（兜底）
  if pgrep -f "vite.*animagus\|vite.*main-app" &>/dev/null; then
    info "检测到 Vite 残留进程，正在终止..."
    pkill -f "vite.*animagus\|vite.*main-app" 2>/dev/null && STOPPED=$((STOPPED + 1)) || true
  fi
fi

# ============================================================
#  5. 清理 PID 文件
# ============================================================
info "清理临时文件..."
rm -f "$ROOT_DIR/.server_pids" "$ROOT_DIR/.server_ports"

# 仅在停止所有服务时清理部署配置
if [ "$ONLY" = "all" ]; then
  rm -f "$DEPLOY_CONFIG"
fi

# ============================================================
#  6. 结果
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

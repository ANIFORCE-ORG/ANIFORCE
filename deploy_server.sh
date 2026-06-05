#!/usr/bin/env bash
# ============================================================
#  ANIFORCE 统一部署脚本（通过 Nginx 反向代理）
#  用法:
#    ./deploy_server.sh [--mode local|cloud] [--nginx-port 80] 
#                       [--frontend-port 3010] [--backend-port 8010]
#                       [--only all|backend|frontend|nginx] [--skip-install]
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
NGINX_PORT=80
FRONTEND_PORT=3010
BACKEND_PORT=8010
DEMO_MODE=false
USE_SSL=false

# ---------- 日志配置 ----------
LOG_DIR="./logs"
LOG_DIR_EXPLICIT=0

# ---------- 参数解析 ----------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode) MODE="$2"; shift 2 ;;
    --nginx-port) NGINX_PORT="$2"; shift 2 ;;
    --frontend-port) FRONTEND_PORT="$2"; shift 2 ;;
    --backend-port) BACKEND_PORT="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --skip-install) SKIP_INSTALL=1; shift 1 ;;
    --demo) DEMO_MODE=true; shift 1 ;;
    --ssl) USE_SSL=true; shift 1 ;;
    --log-dir) LOG_DIR="$2"; LOG_DIR_EXPLICIT=1; shift 2 ;;
    -h|--help)
      echo "用法: $0 [选项]"
      echo ""
      echo "选项:"
      echo "  --mode           启动模式: local(默认) / cloud"
      echo "  --nginx-port     Nginx 端口 (默认: 80)"
      echo "  --frontend-port  前端端口 (默认: 3010)"
      echo "  --backend-port   后端端口 (默认: 8010)"
      echo "  --only           仅启动: all(默认) / backend / frontend / nginx"
      echo "  --skip-install   跳过依赖安装"
      echo "  --demo           启用 Demo 模式"
      echo "  --ssl            启用 HTTPS (使用 nginx-https.conf)"
      echo "  --log-dir        日志目录 (默认: ./logs)"
      echo ""
      echo "示例:"
      echo "  # 本地开发模式（完整部署）"
      echo "  $0 --mode local"
      echo ""
      echo "  # 仅启动 Nginx"
      echo "  $0 --only nginx"
      echo ""
      echo "  # 云端生产模式"
      echo "  $0 --mode cloud --skip-install"
      echo ""
      echo "  # 启用 HTTPS"
      echo "  $0 --ssl"
      exit 0 ;;
    *) fail "未知参数: $1  (使用 --help 查看帮助)" ;;
  esac
done

# ---------- 参数验证 ----------
if [ "$MODE" != "local" ] && [ "$MODE" != "cloud" ]; then
  fail "--mode 仅支持 local 或 cloud"
fi
if [ "$ONLY" != "all" ] && [ "$ONLY" != "backend" ] && [ "$ONLY" != "frontend" ] && [ "$ONLY" != "nginx" ]; then
  fail "--only 仅支持 all/backend/frontend/nginx"
fi

info "部署模式: MODE=$MODE, ONLY=$ONLY, DEMO_MODE=$DEMO_MODE, USE_SSL=$USE_SSL"
info "端口配置: Nginx=$NGINX_PORT, 前端=$FRONTEND_PORT, 后端=$BACKEND_PORT"

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

# 日志文件路径
BACKEND_APP_LOG="$LOG_DIR/backend_logs_{time:YYYYMMDD}.log"
BACKEND_UVICORN_LOG="$LOG_DIR/uvicorn_logs_${LOG_DATE}.log"
FRONTEND_LOG="$LOG_DIR/frontend_logs_${LOG_DATE}.log"
NGINX_ACCESS_LOG="$LOG_DIR/nginx_access_${LOG_DATE}.log"
NGINX_ERROR_LOG="$LOG_DIR/nginx_error_${LOG_DATE}.log"

info "日志配置: 目录=$LOG_DIR"
info "后端应用日志: $BACKEND_APP_LOG"
info "后端 Uvicorn 日志: $BACKEND_UVICORN_LOG"
info "前端日志: $FRONTEND_LOG"
info "Nginx访问日志: $NGINX_ACCESS_LOG"
info "Nginx错误日志: $NGINX_ERROR_LOG"

# ---------- 配置文件 ----------
DEPLOY_CONFIG="$ROOT_DIR/.deploy_config"
: > "$DEPLOY_CONFIG"
echo "NGINX_PORT=$NGINX_PORT" >> "$DEPLOY_CONFIG"
echo "FRONTEND_PORT=$FRONTEND_PORT" >> "$DEPLOY_CONFIG"
echo "BACKEND_PORT=$BACKEND_PORT" >> "$DEPLOY_CONFIG"
echo "MODE=$MODE" >> "$DEPLOY_CONFIG"
echo "ONLY=$ONLY" >> "$DEPLOY_CONFIG"
echo "USE_SSL=$USE_SSL" >> "$DEPLOY_CONFIG"

# ============================================================
#  1. 检查 Nginx
# ============================================================
if [ "$ONLY" != "backend" ] && [ "$ONLY" != "frontend" ]; then
  info "========== 检查 Nginx =========="
  
  if ! command -v nginx &>/dev/null; then
    warn "未检测到 Nginx，正在尝试安装..."
    if command -v brew &>/dev/null; then
      brew install nginx || fail "Nginx 安装失败"
      ok "Nginx 已通过 Homebrew 安装"
    elif command -v apt-get &>/dev/null; then
      sudo apt-get update && sudo apt-get install -y nginx || fail "Nginx 安装失败"
      ok "Nginx 已通过 apt-get 安装"
    elif command -v yum &>/dev/null; then
      sudo yum install -y nginx || fail "Nginx 安装失败"
      ok "Nginx 已通过 yum 安装"
    else
      fail "无法自动安装 Nginx，请手动安装后重试"
    fi
  else
    NGINX_VER=$(nginx -v 2>&1 | awk -F'/' '{print $2}')
    ok "Nginx $NGINX_VER"
  fi
fi

# ============================================================
#  2. 启动后端服务
# ============================================================
if [ "$ONLY" = "nginx" ]; then
  warn "--only=nginx：跳过后端启动"
elif [ "$ONLY" = "frontend" ]; then
  warn "--only=frontend：跳过后端启动"
else
  info "========== 启动后端服务 =========="
  
  # 清理后端端口占用
  if check_port_in_use $BACKEND_PORT; then
    warn "端口 $BACKEND_PORT 已被占用，正在清理..."
    kill_port_process $BACKEND_PORT
    sleep 1
  fi
  
  # 调用原有的 run_server.sh 启动后端
  BACKEND_ARGS="--mode $MODE --backend-port $BACKEND_PORT --only backend --log-dir $LOG_DIR"
  if [ "$SKIP_INSTALL" -eq 1 ]; then
    BACKEND_ARGS="$BACKEND_ARGS --skip-install"
  fi
  if [ "$DEMO_MODE" = "true" ]; then
    BACKEND_ARGS="$BACKEND_ARGS --demo"
  fi
  
  info "执行: ./run_server.sh $BACKEND_ARGS"
  bash "$ROOT_DIR/run_server.sh" $BACKEND_ARGS &
  BACKEND_SCRIPT_PID=$!
  
  # 等待后端启动
  sleep 10
  
  # 检查后端是否启动成功
  if check_port_in_use $BACKEND_PORT; then
    ok "后端服务已启动 (端口: $BACKEND_PORT)"
  else
    fail "后端服务启动失败 (端口: $BACKEND_PORT)"
  fi
fi

# ============================================================
#  3. 启动前端服务
# ============================================================
if [ "$ONLY" = "nginx" ]; then
  warn "--only=nginx：跳过前端启动"
elif [ "$ONLY" = "backend" ]; then
  warn "--only=backend：跳过前端启动"
else
  info "========== 启动前端服务 =========="
  
  # 清理前端端口占用
  if lsof -i :$FRONTEND_PORT -sTCP:LISTEN &>/dev/null; then
    warn "端口 $FRONTEND_PORT 已被占用，正在清理..."
    lsof -ti :$FRONTEND_PORT | xargs kill -9 2>/dev/null || true
    sleep 1
  fi
  
  # 调用原有的 run_server.sh 启动前端
  FRONTEND_ARGS="--mode $MODE --frontend-port $FRONTEND_PORT --only frontend --log-dir $LOG_DIR"
  if [ "$SKIP_INSTALL" -eq 1 ]; then
    FRONTEND_ARGS="$FRONTEND_ARGS --skip-install"
  fi
  
  info "执行: ./run_server.sh $FRONTEND_ARGS"
  bash "$ROOT_DIR/run_server.sh" $FRONTEND_ARGS &
  FRONTEND_SCRIPT_PID=$!
  
  # 等待前端启动
  sleep 8
  
  # 检查前端是否启动成功
  if check_port_in_use $FRONTEND_PORT; then
    ok "前端服务已启动 (端口: $FRONTEND_PORT)"
  else
    fail "前端服务启动失败"
  fi
fi

# ============================================================
#  4. 配置并启动 Nginx
# ============================================================
if [ "$ONLY" = "backend" ]; then
  warn "--only=backend：跳过 Nginx 启动"
elif [ "$ONLY" = "frontend" ]; then
  warn "--only=frontend：跳过 Nginx 启动"
else
  info "========== 配置 Nginx =========="
  
  # 根据 SSL 参数选择配置文件
  if [ "$USE_SSL" = "true" ]; then
    NGINX_CONF="$ROOT_DIR/nginx-https.conf"
    info "使用 HTTPS 配置: $NGINX_CONF"
    
    # 检查 SSL 证书是否存在
    if [ ! -f "/etc/letsencrypt/live/www.aniforce.cc/fullchain.pem" ]; then
      warn "SSL 证书未找到，请先运行: sudo ./scripts/ssl/setup_ssl.sh"
      warn "或者使用不带 --ssl 参数启动开发模式"
      fail "SSL 证书缺失"
    fi
  else
    NGINX_CONF="$ROOT_DIR/nginx.conf"
    info "使用 HTTP 配置: $NGINX_CONF"
  fi
  
  NGINX_RUNTIME_CONF="$ROOT_DIR/.nginx_runtime.conf"
  
  # 检测 mime.types 路径
  MIME_TYPES_PATH=""
  for path in /opt/homebrew/etc/nginx/mime.types /etc/nginx/mime.types /usr/local/etc/nginx/mime.types; do
    if [ -f "$path" ]; then
      MIME_TYPES_PATH="$path"
      break
    fi
  done
  
  if [ -z "$MIME_TYPES_PATH" ]; then
    warn "未找到 mime.types 文件，使用默认路径"
    MIME_TYPES_PATH="/etc/nginx/mime.types"
  fi
  
  # 根据配置类型生成运行时配置
  if [ "$USE_SSL" = "true" ]; then
    # HTTPS 配置：替换端口和日志路径
    sed "s/localhost:3010/localhost:$FRONTEND_PORT/g" "$NGINX_CONF" | \
    sed "s/localhost:8010/localhost:$BACKEND_PORT/g" | \
    sed "s|include /etc/nginx/mime.types;|include $MIME_TYPES_PATH;|g" | \
    sed "s|/var/log/nginx/aniforce_access.log|$NGINX_ACCESS_LOG|g" | \
    sed "s|/var/log/nginx/aniforce_error.log|$NGINX_ERROR_LOG|g" | \
    sed "s|error_log /var/log/nginx/aniforce_error.log;|error_log $NGINX_ERROR_LOG;|g" | \
    sed "s|access_log /var/log/nginx/aniforce_access.log main;|access_log $NGINX_ACCESS_LOG main;|g" > "$NGINX_RUNTIME_CONF"
  else
    # HTTP 配置：替换端口配置、mime.types 路径和日志路径
    sed "s/listen 80;/listen $NGINX_PORT;/g" "$NGINX_CONF" | \
    sed "s/127.0.0.1:8010/127.0.0.1:$BACKEND_PORT/g" | \
    sed "s/127.0.0.1:3010/127.0.0.1:$FRONTEND_PORT/g" | \
    sed "s|include /opt/homebrew/etc/nginx/mime.types;|include $MIME_TYPES_PATH;|g" | \
    sed "s|/tmp/aniforce_access.log|$NGINX_ACCESS_LOG|g" | \
    sed "s|/tmp/aniforce_error.log|$NGINX_ERROR_LOG|g" > "$NGINX_RUNTIME_CONF"
  fi
  
  ok "Nginx 配置已生成: $NGINX_RUNTIME_CONF"
  
  # 测试配置
  info "测试 Nginx 配置..."
  if [ "$USE_SSL" = "true" ]; then
    # HTTPS 配置需要 root 权限测试
    sudo nginx -t -c "$NGINX_RUNTIME_CONF" || fail "Nginx 配置测试失败"
  else
    nginx -t -c "$NGINX_RUNTIME_CONF" || fail "Nginx 配置测试失败"
  fi
  ok "Nginx 配置测试通过"
  
  # 检查端口占用
  if check_port_in_use $NGINX_PORT; then
    warn "端口 $NGINX_PORT 已被占用，尝试停止现有 Nginx..."
    nginx -s stop 2>/dev/null || sudo nginx -s stop 2>/dev/null || true
    sleep 2
  fi
  
  # 启动 Nginx
  if [ "$USE_SSL" = "true" ]; then
    info "启动 Nginx (HTTPS 模式，端口: 80/443)..."
    sudo nginx -c "$NGINX_RUNTIME_CONF" || fail "Nginx 启动失败"
  else
    info "启动 Nginx (HTTP 模式，端口: $NGINX_PORT)..."
    nginx -c "$NGINX_RUNTIME_CONF" || sudo nginx -c "$NGINX_RUNTIME_CONF" || fail "Nginx 启动失败"
  fi
  sleep 2
  
  if check_port_in_use $NGINX_PORT; then
    ok "Nginx 已启动 (端口: $NGINX_PORT)"
  else
    fail "Nginx 启动失败"
  fi
fi

# ============================================================
#  5. 完成
# ============================================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  ANIFORCE 服务部署完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""

if [ "$ONLY" = "all" ] || [ "$ONLY" = "nginx" ]; then
  if [ "$USE_SSL" = "true" ]; then
    echo -e "  访问地址:      ${CYAN}https://www.aniforce.cc${NC}"
    echo -e "  API 端点:      ${CYAN}https://www.aniforce.cc/api/${NC}"
    echo -e "  健康检查:      ${CYAN}https://www.aniforce.cc/health${NC}"
    echo -e "  HTTP 重定向:   ${CYAN}http://www.aniforce.cc${NC} → HTTPS"
  else
    echo -e "  访问地址:      ${CYAN}http://localhost:$NGINX_PORT${NC}"
    echo -e "  API 文档:      ${CYAN}http://localhost:$NGINX_PORT/docs${NC}"
    echo -e "  健康检查:      ${CYAN}http://localhost:$NGINX_PORT/health${NC}"
  fi
  echo ""
fi

if [ "$ONLY" != "nginx" ]; then
  echo -e "  后端直连:      ${CYAN}http://localhost:$BACKEND_PORT${NC}"
  echo -e "  前端直连:      ${CYAN}http://localhost:$FRONTEND_PORT${NC}"
  echo ""
fi

echo -e "  使用 ${YELLOW}./undeploy_server.sh${NC} 停止所有服务"
echo ""

# 自动打开浏览器（仅本地模式）
if [ "$MODE" = "local" ] && [ "$ONLY" = "all" ]; then
  if command -v open &>/dev/null; then
    open "http://localhost:$NGINX_PORT"
  elif command -v xdg-open &>/dev/null; then
    xdg-open "http://localhost:$NGINX_PORT"
  fi
fi

ok "部署完成"

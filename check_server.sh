#!/usr/bin/env bash
# ============================================================
#  ANIFORCE 服务状态检查脚本
#  检查前后端端口和 Nginx 服务的运行状态
# ============================================================
set -euo pipefail

# ---------- 颜色 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[✓]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[!]${NC}    $*"; }
fail()  { echo -e "${RED}[✗]${NC}    $*"; }
title() { echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BLUE}  $*${NC}"; echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

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
  
  return 1
}

# ---------- 获取端口进程信息 ----------
get_port_process_info() {
  local port=$1
  
  # 方法1: 使用 lsof
  if command -v lsof &>/dev/null; then
    local info=$(lsof -i :$port -sTCP:LISTEN 2>/dev/null | tail -n 1)
    if [ -n "$info" ]; then
      local pid=$(echo "$info" | awk '{print $2}')
      local cmd=$(echo "$info" | awk '{print $1}')
      echo "PID: $pid, 进程: $cmd"
      return 0
    fi
  fi
  
  # 方法2: 使用 ss
  if command -v ss &>/dev/null; then
    local info=$(ss -lptn 2>/dev/null | grep ":$port ")
    if [ -n "$info" ]; then
      local pid=$(echo "$info" | grep -oP 'pid=\K[0-9]+' | head -1)
      if [ -n "$pid" ]; then
        local cmd=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
        echo "PID: $pid, 进程: $cmd"
        return 0
      fi
    fi
  fi
  
  # 方法3: 使用 netstat + ps
  if command -v netstat &>/dev/null; then
    local pid=$(netstat -ltnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | head -1)
    if [ -n "$pid" ] && [ "$pid" != "-" ]; then
      local cmd=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
      echo "PID: $pid, 进程: $cmd"
      return 0
    fi
  fi
  
  echo "无法获取进程信息"
  return 1
}

# ---------- 检查 Nginx 状态 ----------
check_nginx_status() {
  # 检查 nginx 进程（不使用 -x 精确匹配，因为 nginx 进程名包含 "master process" 等）
  if pgrep nginx &>/dev/null; then
    local nginx_pids=$(pgrep nginx | tr '\n' ' ')
    echo "running|$nginx_pids"
    return 0
  fi
  
  # 备用方法：使用 ps + grep
  if ps aux | grep -v grep | grep -q nginx; then
    local nginx_pids=$(ps aux | grep -v grep | grep nginx | awk '{print $2}' | tr '\n' ' ')
    echo "running|$nginx_pids"
    return 0
  fi
  
  echo "stopped|"
  return 1
}

# ---------- 获取配置的端口 ----------
get_configured_ports() {
  local config_file=".deploy_config"
  
  if [ -f "$config_file" ]; then
    source "$config_file" 2>/dev/null || true
  fi
  
  # 使用默认值如果配置文件不存在
  NGINX_PORT=${NGINX_PORT:-80}
  FRONTEND_PORT=${FRONTEND_PORT:-3010}
  BACKEND_PORT=${BACKEND_PORT:-8010}
  AGENT_PORT=${AGENT_PORT:-8020}
  PHOENIX_PORT=${PHOENIX_PORT:-6006}
}

# ---------- 检查 HTTP 响应 ----------
check_http_response() {
  local url=$1
  local timeout=2
  
  if command -v curl &>/dev/null; then
    local status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout $timeout "$url" 2>/dev/null || echo "000")
    echo "$status"
  elif command -v wget &>/dev/null; then
    if wget -q --spider --timeout=$timeout "$url" 2>/dev/null; then
      echo "200"
    else
      echo "000"
    fi
  else
    echo "N/A"
  fi
}

# ---------- 主函数 ----------
main() {
  clear
  
  title "ANIFORCE 服务状态检查"
  echo ""
  
  # 获取配置的端口
  get_configured_ports
  
  info "配置的端口: Nginx=$NGINX_PORT, 前端=$FRONTEND_PORT, 后端=$BACKEND_PORT, Agent=$AGENT_PORT, Phoenix=$PHOENIX_PORT"
  echo ""
  
  # ========================================
  # 1. 检查后端服务
  # ========================================
  title "后端服务 (端口: $BACKEND_PORT)"
  
  if check_port_in_use $BACKEND_PORT; then
    ok "后端服务正在运行"
    
    # 获取进程信息
    local process_info=$(get_port_process_info $BACKEND_PORT)
    info "$process_info"
    
    # 检查 HTTP 响应
    local backend_url="http://localhost:$BACKEND_PORT/health"
    local http_status=$(check_http_response "$backend_url")
    
    if [ "$http_status" = "200" ]; then
      ok "健康检查通过 (HTTP $http_status)"
    elif [ "$http_status" = "N/A" ]; then
      warn "无法检查 HTTP 响应（curl/wget 不可用）"
    else
      warn "健康检查失败 (HTTP $http_status)"
    fi
  else
    fail "后端服务未运行"
  fi
  
  echo ""
  
  # ========================================
  # 2. 检查 Agent 服务
  # ========================================
  title "Agent 服务 (端口: $AGENT_PORT)"

  if check_port_in_use $AGENT_PORT; then
    ok "Agent 服务正在运行"

    local process_info=$(get_port_process_info $AGENT_PORT)
    info "$process_info"

    local agent_url="http://localhost:$AGENT_PORT/health"
    local http_status=$(check_http_response "$agent_url")

    if [ "$http_status" = "200" ]; then
      ok "健康检查通过 (HTTP $http_status)"
    elif [ "$http_status" = "N/A" ]; then
      warn "无法检查 HTTP 响应（curl/wget 不可用）"
    else
      warn "健康检查失败 (HTTP $http_status)"
    fi
  else
    fail "Agent 服务未运行"
  fi

  echo ""

  # ========================================
  # 3. 检查 Phoenix tracing
  # ========================================
  title "Phoenix tracing (端口: $PHOENIX_PORT)"

  if check_port_in_use $PHOENIX_PORT; then
    local phoenix_status=$(check_http_response "http://localhost:$PHOENIX_PORT/healthz")
    if [ "$phoenix_status" = "200" ]; then
      ok "Collector 与 UI 健康检查通过 (HTTP $phoenix_status)"
      info "http://localhost:$PHOENIX_PORT"
    else
      warn "Phoenix 端口已监听但健康检查失败 (HTTP $phoenix_status)"
    fi
  else
    warn "Phoenix tracing 未运行"
  fi

  echo ""

  # ========================================
  # 4. 检查后端到 Agent 网关
  # ========================================
  title "后端 Agent 网关 (/api/v1/agent/health)"

  if check_port_in_use $BACKEND_PORT; then
    local gateway_url="http://localhost:$BACKEND_PORT/api/v1/agent/health"
    local gateway_status=$(check_http_response "$gateway_url")
    if [ "$gateway_status" = "200" ]; then
      ok "后端到 Agent 链路正常 (HTTP $gateway_status)"
    else
      warn "后端到 Agent 链路异常 (HTTP $gateway_status)"
    fi
  else
    warn "后端未运行，跳过 Agent 网关检查"
  fi

  echo ""

  # ========================================
  # 4. 检查前端服务
  # ========================================
  title "前端服务 (端口: $FRONTEND_PORT)"
  
  if check_port_in_use $FRONTEND_PORT; then
    ok "前端服务正在运行"
    
    # 获取进程信息
    local process_info=$(get_port_process_info $FRONTEND_PORT)
    info "$process_info"
    
    # 检查 HTTP 响应
    local frontend_url="http://localhost:$FRONTEND_PORT"
    local http_status=$(check_http_response "$frontend_url")
    
    if [ "$http_status" = "200" ]; then
      ok "HTTP 响应正常 (HTTP $http_status)"
    elif [ "$http_status" = "N/A" ]; then
      warn "无法检查 HTTP 响应（curl/wget 不可用）"
    else
      warn "HTTP 响应异常 (HTTP $http_status)"
    fi
  else
    fail "前端服务未运行"
  fi
  
  echo ""
  
  # ========================================
  # 5. 检查 Nginx 服务
  # ========================================
  title "Nginx 服务 (端口: $NGINX_PORT)"
  
  local nginx_status=$(check_nginx_status)
  local status=$(echo "$nginx_status" | cut -d'|' -f1)
  local pids=$(echo "$nginx_status" | cut -d'|' -f2)
  
  if [ "$status" = "running" ]; then
    ok "Nginx 服务正在运行"
    info "进程 PID: $pids"
    
    # 检查端口
    if check_port_in_use $NGINX_PORT; then
      ok "Nginx 端口 $NGINX_PORT 正在监听"
      
      # 检查 HTTP 响应
      local nginx_url="http://localhost:$NGINX_PORT/health"
      local http_status=$(check_http_response "$nginx_url")
      
      if [ "$http_status" = "200" ]; then
        ok "HTTP 响应正常 (HTTP $http_status)"
      elif [ "$http_status" = "N/A" ]; then
        warn "无法检查 HTTP 响应（curl/wget 不可用）"
      else
        warn "HTTP 响应异常 (HTTP $http_status)"
      fi
    else
      warn "Nginx 进程运行中，但端口 $NGINX_PORT 未监听"
    fi
  else
    fail "Nginx 服务未运行"
  fi
  
  echo ""
  
  # ========================================
  # 6. 服务总览
  # ========================================
  title "服务总览"
  
  local backend_status="❌ 未运行"
  local agent_status="❌ 未运行"
  local frontend_status="❌ 未运行"
  local nginx_status_text="❌ 未运行"
  local phoenix_status_text="❌ 未运行"
  
  if check_port_in_use $BACKEND_PORT; then
    backend_status="✅ 运行中"
  fi
  
  if check_port_in_use $AGENT_PORT; then
    agent_status="✅ 运行中"
  fi

  if check_port_in_use $FRONTEND_PORT; then
    frontend_status="✅ 运行中"
  fi

  if [ "$(check_http_response "http://localhost:$PHOENIX_PORT/healthz")" = "200" ]; then
    phoenix_status_text="✅ 运行中"
  fi
  
  if [ "$status" = "running" ]; then
    nginx_status_text="✅ 运行中"
  fi
  
  echo ""
  printf "  %-20s %s\n" "后端服务:" "$backend_status"
  printf "  %-20s %s\n" "Agent 服务:" "$agent_status"
  printf "  %-20s %s\n" "前端服务:" "$frontend_status"
  printf "  %-20s %s\n" "Phoenix tracing:" "$phoenix_status_text"
  printf "  %-20s %s\n" "Nginx 服务:" "$nginx_status_text"
  echo ""
  
  # ========================================
  # 7. 访问地址
  # ========================================
  title "访问地址"
  
  echo ""
  if [ "$nginx_status_text" = "✅ 运行中" ]; then
    info "通过 Nginx 访问:"
    echo "  → http://localhost:$NGINX_PORT"
    echo ""
  fi
  
  if [ "$phoenix_status_text" = "✅ 运行中" ]; then
    info "Tracing UI:"
    echo "  → http://localhost:$PHOENIX_PORT"
    echo ""
  fi

  if [ "$agent_status" = "✅ 运行中" ]; then
    info "直接访问 Agent:"
    echo "  → http://localhost:$AGENT_PORT"
    echo "  → http://localhost:$AGENT_PORT/health"
    echo ""
  fi

  if [ "$backend_status" = "✅ 运行中" ]; then
    info "直接访问后端:"
    echo "  → http://localhost:$BACKEND_PORT"
    echo "  → http://localhost:$BACKEND_PORT/docs (API 文档)"
    echo ""
  fi
  
  if [ "$frontend_status" = "✅ 运行中" ]; then
    info "直接访问前端:"
    echo "  → http://localhost:$FRONTEND_PORT"
    echo ""
  fi
  
  # ========================================
  # 8. 日志文件
  # ========================================
  title "日志文件"
  
  echo ""
  local log_dir="./logs"
  local log_date=$(date +%Y%m%d)
  
  if [ -d "$log_dir" ]; then
    info "日志目录: $log_dir"
    echo ""
    
    # 后端日志
    if [ -f "$log_dir/backend_logs_${log_date}.log" ]; then
      local backend_log_size=$(du -h "$log_dir/backend_logs_${log_date}.log" | awk '{print $1}')
      printf "  %-30s %s\n" "后端应用日志:" "$backend_log_size"
    fi
    
    if [ -f "$log_dir/uvicorn_logs_${log_date}.log" ]; then
      local uvicorn_log_size=$(du -h "$log_dir/uvicorn_logs_${log_date}.log" | awk '{print $1}')
      printf "  %-30s %s\n" "Uvicorn 日志:" "$uvicorn_log_size"
    fi
    
    if [ -f "$log_dir/agent_uvicorn_logs_${log_date}.log" ]; then
      local agent_log_size=$(du -h "$log_dir/agent_uvicorn_logs_${log_date}.log" | awk '{print $1}')
      printf "  %-30s %s\n" "Agent 日志:" "$agent_log_size"
    fi

    # 前端日志
    if [ -f "$log_dir/frontend_logs_${log_date}.log" ]; then
      local frontend_log_size=$(du -h "$log_dir/frontend_logs_${log_date}.log" | awk '{print $1}')
      printf "  %-30s %s\n" "前端日志:" "$frontend_log_size"
    fi
    
    # Nginx 日志
    if [ -f "$log_dir/nginx_access_${log_date}.log" ]; then
      local nginx_access_log_size=$(du -h "$log_dir/nginx_access_${log_date}.log" | awk '{print $1}')
      printf "  %-30s %s\n" "Nginx 访问日志:" "$nginx_access_log_size"
    fi
    
    if [ -f "$log_dir/nginx_error_${log_date}.log" ]; then
      local nginx_error_log_size=$(du -h "$log_dir/nginx_error_${log_date}.log" | awk '{print $1}')
      printf "  %-30s %s\n" "Nginx 错误日志:" "$nginx_error_log_size"
    fi
    
    echo ""
  else
    warn "日志目录不存在: $log_dir"
    echo ""
  fi
  
  # ========================================
  # 7. 快捷命令
  # ========================================
  title "快捷命令"
  
  echo ""
  info "查看实时日志:"
  echo "  tail -f logs/backend_logs_\$(date +%Y%m%d).log"
  echo "  tail -f logs/frontend_logs_\$(date +%Y%m%d).log"
  echo "  tail -f logs/nginx_access_\$(date +%Y%m%d).log"
  echo ""
  
  info "重启服务:"
  echo "  ./undeploy_server.sh && ./deploy_server.sh"
  echo ""
  
  info "停止服务:"
  echo "  ./undeploy_server.sh"
  echo ""
  
  # ========================================
  # 8. 结束
  # ========================================
  title "检查完成"
  echo ""
}

# 运行主函数
main "$@"

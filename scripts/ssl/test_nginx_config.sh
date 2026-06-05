#!/usr/bin/env bash
# 测试 Nginx 配置文件的有效性

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info() { echo -e "${CYAN}[INFO]${NC} $*"; }
ok() { echo -e "${GREEN}[OK]${NC} $*"; }
fail() { echo -e "${RED}[FAIL]${NC} $*"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo ""
info "========== 测试 Nginx 配置文件 =========="
info "项目根目录: $ROOT_DIR"
echo ""

# 测试 HTTP 配置
info "1. 测试 HTTP 配置 (nginx.conf)"
if [ -f "$ROOT_DIR/nginx.conf" ]; then
    if nginx -t -c "$ROOT_DIR/nginx.conf" 2>&1 | grep -q "successful"; then
        ok "nginx.conf 配置有效"
    else
        fail "nginx.conf 配置无效"
        nginx -t -c "$ROOT_DIR/nginx.conf"
    fi
else
    fail "nginx.conf 文件不存在: $ROOT_DIR/nginx.conf"
fi

echo ""

# 测试 HTTPS 配置
info "2. 测试 HTTPS 配置 (nginx-https.conf)"
if [ -f "$ROOT_DIR/nginx-https.conf" ]; then
    if sudo nginx -t -c "$ROOT_DIR/nginx-https.conf" 2>&1 | grep -q "successful"; then
        ok "nginx-https.conf 配置有效"
    else
        fail "nginx-https.conf 配置无效"
        sudo nginx -t -c "$ROOT_DIR/nginx-https.conf"
    fi
else
    fail "nginx-https.conf 文件不存在: $ROOT_DIR/nginx-https.conf"
fi

echo ""
ok "所有配置文件测试完成"

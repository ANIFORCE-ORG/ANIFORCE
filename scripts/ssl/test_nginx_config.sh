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
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 默认参数
ENV_TYPE=""

# 参数解析
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      ENV_TYPE="$2"
      shift 2
      ;;
    -h|--help)
      echo "用法: $0 [选项]"
      echo ""
      echo "选项:"
      echo "  --env     操作系统类型: mac / linux"
      echo "  -h, --help  显示帮助信息"
      echo ""
      echo "示例:"
      echo "  # macOS 环境测试"
      echo "  $0 --env mac"
      echo ""
      echo "  # Linux 环境测试"
      echo "  $0 --env linux"
      echo ""
      echo "  # 自动检测环境"
      echo "  $0"
      exit 0
      ;;
    *)
      echo "未知参数: $1"
      echo "使用 --help 查看帮助"
      exit 1
      ;;
  esac
done

# 自动检测操作系统
if [ -z "$ENV_TYPE" ]; then
  if [[ "$OSTYPE" == "darwin"* ]]; then
    ENV_TYPE="mac"
    info "自动检测到 macOS 环境"
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    ENV_TYPE="linux"
    info "自动检测到 Linux 环境"
  else
    warn "无法自动检测操作系统，默认使用 linux 配置"
    ENV_TYPE="linux"
  fi
fi

# 验证环境类型
if [ "$ENV_TYPE" != "mac" ] && [ "$ENV_TYPE" != "linux" ]; then
  fail "--env 参数只支持 mac 或 linux"
  exit 1
fi

# 根据环境类型设置 mime.types 路径
if [ "$ENV_TYPE" = "mac" ]; then
  MIME_TYPES_PATH="/opt/homebrew/etc/nginx/mime.types"
  if [ ! -f "$MIME_TYPES_PATH" ]; then
    # 尝试旧版 Homebrew 路径
    MIME_TYPES_PATH="/usr/local/etc/nginx/mime.types"
  fi
else
  MIME_TYPES_PATH="/etc/nginx/mime.types"
fi

info "环境类型: $ENV_TYPE"
info "mime.types 路径: $MIME_TYPES_PATH"

echo ""
info "========== 测试 Nginx 配置文件 =========="
info "项目根目录: $ROOT_DIR"
echo ""

# 临时配置文件
TEMP_HTTP_CONF="/tmp/nginx_test_http_$$.conf"
TEMP_HTTPS_CONF="/tmp/nginx_test_https_$$.conf"

# 清理函数
cleanup() {
  rm -f "$TEMP_HTTP_CONF" "$TEMP_HTTPS_CONF"
}
trap cleanup EXIT

# 测试 HTTP 配置
info "1. 测试 HTTP 配置 (nginx.conf)"
if [ -f "$ROOT_DIR/nginx.conf" ]; then
    # 生成临时配置文件，替换所有可能的 mime.types 路径
    sed "s|include /opt/homebrew/etc/nginx/mime.types;|include $MIME_TYPES_PATH;|g" "$ROOT_DIR/nginx.conf" | \
    sed "s|include /usr/local/etc/nginx/mime.types;|include $MIME_TYPES_PATH;|g" | \
    sed "s|include /etc/nginx/mime.types;|include $MIME_TYPES_PATH;|g" > "$TEMP_HTTP_CONF"
    
    if nginx -t -c "$TEMP_HTTP_CONF" 2>&1 | grep -q "successful"; then
        ok "nginx.conf 配置有效"
    else
        fail "nginx.conf 配置无效"
        nginx -t -c "$TEMP_HTTP_CONF"
    fi
else
    fail "nginx.conf 文件不存在: $ROOT_DIR/nginx.conf"
fi

echo ""

# 测试 HTTPS 配置
info "2. 测试 HTTPS 配置 (nginx-https.conf)"
if [ -f "$ROOT_DIR/nginx-https.conf" ]; then
    # 生成临时配置文件，替换所有可能的 mime.types 路径
    sed "s|include /opt/homebrew/etc/nginx/mime.types;|include $MIME_TYPES_PATH;|g" "$ROOT_DIR/nginx-https.conf" | \
    sed "s|include /usr/local/etc/nginx/mime.types;|include $MIME_TYPES_PATH;|g" | \
    sed "s|include /etc/nginx/mime.types;|include $MIME_TYPES_PATH;|g" > "$TEMP_HTTPS_CONF"
    
    # 检查 SSL 证书是否存在
    if [ ! -f "/etc/letsencrypt/live/www.aniforce.cc/fullchain.pem" ]; then
        warn "SSL 证书未找到，跳过 HTTPS 配置测试"
        warn "如需测试 HTTPS 配置，请先运行: sudo ./setup_ssl.sh"
    else
        if sudo nginx -t -c "$TEMP_HTTPS_CONF" 2>&1 | grep -q "successful"; then
            ok "nginx-https.conf 配置有效"
        else
            fail "nginx-https.conf 配置无效"
            sudo nginx -t -c "$TEMP_HTTPS_CONF"
        fi
    fi
else
    fail "nginx-https.conf 文件不存在: $ROOT_DIR/nginx-https.conf"
fi

echo ""
ok "所有配置文件测试完成"

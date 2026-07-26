#!/bin/bash

# ANIFORCE SSL 证书获取和配置脚本
# 使用 Let's Encrypt 和 Certbot

set -e

CERTBOT_BIN=""

resolve_certbot() {
    if [ -x /snap/bin/certbot ]; then
        CERTBOT_BIN="/snap/bin/certbot"
        return 0
    fi
    if command -v certbot &> /dev/null; then
        CERTBOT_BIN="$(command -v certbot)"
        return 0
    fi
    return 1
}

print_certbot_compat_help() {
    echo "❌ Certbot 运行环境不兼容"
    echo "检测到 Certbot 可能依赖了已移除的 pyOpenSSL.crypto.X509Req API。"
    echo "建议使用官方 snap 版 Certbot 隔离 Python 依赖:"
    echo "  sudo apt remove -y certbot python3-certbot-nginx"
    echo "  sudo snap install core"
    echo "  sudo snap refresh core"
    echo "  sudo snap install --classic certbot"
    echo "  sudo ln -sf /snap/bin/certbot /usr/bin/certbot"
}

check_certbot_compat() {
    local output
    if ! resolve_certbot; then
        echo "错误: Certbot 未安装"
        return 1
    fi
    if ! output=$("$CERTBOT_BIN" --version 2>&1); then
        echo "$output"
        if echo "$output" | grep -Eq "OpenSSL\\.crypto|X509Req|pyOpenSSL"; then
            print_certbot_compat_help
        else
            echo "错误: Certbot 启动失败，请检查安装环境"
        fi
        return 1
    fi
    echo "✓ Certbot 可用: $CERTBOT_BIN"
    echo "  $output"
    return 0
}

install_certbot_with_snap() {
    if ! command -v snap &> /dev/null; then
        apt update
        apt install -y snapd
    fi
    snap install core || true
    snap refresh core
    if snap list certbot &> /dev/null; then
        snap refresh certbot
    else
        snap install --classic certbot
    fi
    ln -sf /snap/bin/certbot /usr/bin/certbot
}

echo "======================================"
echo "ANIFORCE SSL 证书配置脚本"
echo "======================================"
echo ""

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then 
    echo "错误: 请使用 sudo 运行此脚本"
    exit 1
fi

# 域名配置
DOMAIN="www.aniforce.cc"
DOMAIN_ALT="aniforce.cc"
EMAIL="support@aniforce.cc"

echo "配置信息:"
echo "  主域名: $DOMAIN"
echo "  备用域名: $DOMAIN_ALT"
echo "  联系邮箱: $EMAIL"
echo ""

# 检查 Nginx 是否已安装
if ! command -v nginx &> /dev/null; then
    echo "错误: Nginx 未安装，请先安装 Nginx"
    exit 1
fi

echo "✓ Nginx 已安装"

# 检测操作系统并安装 Certbot
echo ""
echo "步骤 1: 安装 Certbot"
echo "-------------------"

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    
    case $OS in
        ubuntu|debian)
            echo "检测到 Ubuntu/Debian 系统"
            install_certbot_with_snap
            ;;
        centos|rhel|fedora)
            echo "检测到 CentOS/RHEL/Fedora 系统"
            if [ "${VERSION_ID%%.*}" -ge 8 ]; then
                dnf install -y certbot python3-certbot-nginx
            else
                yum install -y certbot python3-certbot-nginx
            fi
            ;;
        *)
            echo "警告: 未识别的操作系统，请手动安装 Certbot"
            exit 1
            ;;
    esac
else
    echo "错误: 无法检测操作系统"
    exit 1
fi

echo "✓ Certbot 安装完成"
if ! check_certbot_compat; then
    exit 1
fi

# 创建 certbot 验证目录
echo ""
echo "步骤 2: 创建验证目录"
echo "-------------------"
mkdir -p /var/www/certbot
echo "✓ 验证目录已创建: /var/www/certbot"

# 获取 SSL 证书
echo ""
echo "步骤 3: 获取 SSL 证书"
echo "-------------------"
echo "选择获取证书的方式:"
echo "  1) 自动配置 (推荐) - Certbot 自动修改 Nginx 配置"
echo "  2) 手动配置 - 仅获取证书，手动配置 Nginx"
echo ""
read -p "请选择 [1/2]: " choice

case $choice in
    1)
        echo "使用自动配置模式..."
        "$CERTBOT_BIN" --nginx -d $DOMAIN -d $DOMAIN_ALT --email $EMAIL --agree-tos --non-interactive
        ;;
    2)
        echo "使用手动配置模式..."
        "$CERTBOT_BIN" certonly --nginx -d $DOMAIN -d $DOMAIN_ALT --email $EMAIL --agree-tos --non-interactive
        
        echo ""
        echo "证书已获取，位置:"
        echo "  证书: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
        echo "  私钥: /etc/letsencrypt/live/$DOMAIN/privkey.pem"
        echo ""
        echo "请手动配置 Nginx 使用这些证书"
        ;;
    *)
        echo "无效选择，退出"
        exit 1
        ;;
esac

echo "✓ SSL 证书获取完成"

# 配置 Nginx
if [ "$choice" = "2" ]; then
    echo ""
    echo "步骤 4: 配置 Nginx"
    echo "-------------------"
    
    NGINX_CONF="/etc/nginx/sites-available/aniforce-https.conf"
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SOURCE_CONF="$SCRIPT_DIR/../../nginx-https.conf"
    
    if [ -f "$SOURCE_CONF" ]; then
        echo "复制 Nginx 配置文件..."
        cp "$SOURCE_CONF" "$NGINX_CONF"
        
        # 创建软链接
        if [ ! -L /etc/nginx/sites-enabled/aniforce-https.conf ]; then
            ln -s "$NGINX_CONF" /etc/nginx/sites-enabled/aniforce-https.conf
            echo "✓ 已创建配置软链接"
        fi
        
        # 测试配置
        echo "测试 Nginx 配置..."
        if nginx -t; then
            echo "✓ Nginx 配置测试通过"
            
            # 重启 Nginx
            echo "重启 Nginx..."
            systemctl restart nginx
            echo "✓ Nginx 已重启"
        else
            echo "错误: Nginx 配置测试失败"
            exit 1
        fi
    else
        echo "警告: 未找到 Nginx 配置文件模板"
        echo "请手动配置 Nginx"
    fi
fi

# 配置自动续期
echo ""
echo "步骤 5: 配置自动续期"
echo "-------------------"

# 测试续期
echo "测试证书续期..."
if "$CERTBOT_BIN" renew --dry-run; then
    echo "✓ 证书续期测试成功"
else
    echo "警告: 证书续期测试失败，请检查配置"
fi

# 检查 systemd timer
if systemctl list-timers | grep -q certbot; then
    echo "✓ Certbot systemd timer 已配置"
else
    echo "警告: 未检测到 Certbot systemd timer"
    echo "添加 cron 任务进行自动续期..."
    
    CRON_CMD="0 2 * * * $CERTBOT_BIN renew --quiet --post-hook 'systemctl reload nginx'"
    (crontab -l 2>/dev/null | grep -v "certbot renew"; echo "$CRON_CMD") | crontab -
    echo "✓ 已添加 cron 任务（每天凌晨 2 点检查续期）"
fi

# 验证 HTTPS
echo ""
echo "步骤 6: 验证 HTTPS"
echo "-------------------"

echo "证书信息:"
"$CERTBOT_BIN" certificates

echo ""
echo "======================================"
echo "SSL 配置完成！"
echo "======================================"
echo ""
echo "下一步:"
echo "  1. 访问 https://$DOMAIN 验证 HTTPS 是否正常工作"
echo "  2. 使用 SSL Labs 测试证书质量:"
echo "     https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo "  3. 确保防火墙开放 80 和 443 端口"
echo ""
echo "证书有效期: 90 天"
echo "自动续期: 已配置"
echo ""

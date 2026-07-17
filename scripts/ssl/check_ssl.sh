#!/bin/bash

# ANIFORCE SSL 证书检查脚本
# 检查证书状态和有效期

set -e

DOMAIN="www.aniforce.cc"
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
        echo "❌ Certbot 未安装"
        return 1
    fi
    if ! output=$("$CERTBOT_BIN" --version 2>&1); then
        echo "$output"
        if echo "$output" | grep -Eq "OpenSSL\\.crypto|X509Req|pyOpenSSL"; then
            print_certbot_compat_help
        else
            echo "❌ Certbot 启动失败，请检查安装环境"
        fi
        return 1
    fi
    echo "✓ Certbot 可用: $CERTBOT_BIN"
    echo "  $output"
    return 0
}

echo "======================================"
echo "ANIFORCE SSL 证书状态检查"
echo "======================================"
echo ""

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then 
    echo "警告: 某些检查需要 root 权限"
    echo ""
fi

# 1. 检查证书文件
echo "1. 证书文件检查"
echo "-------------------"

if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "✓ 证书文件存在"
    
    # 显示证书有效期
    echo ""
    echo "证书有效期:"
    openssl x509 -in "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" -noout -dates
    
    # 计算剩余天数
    EXPIRY_DATE=$(openssl x509 -in "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" -noout -enddate | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$EXPIRY_DATE" +%s)
    CURRENT_EPOCH=$(date +%s)
    DAYS_LEFT=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))
    
    echo "剩余天数: $DAYS_LEFT 天"
    
    if [ $DAYS_LEFT -lt 30 ]; then
        echo "⚠️  警告: 证书将在 30 天内过期，建议尽快续期"
    elif [ $DAYS_LEFT -lt 7 ]; then
        echo "❌ 紧急: 证书将在 7 天内过期！"
    else
        echo "✓ 证书有效期充足"
    fi
else
    echo "❌ 证书文件不存在"
fi

# 2. Certbot 证书信息
echo ""
echo "2. Certbot 证书信息"
echo "-------------------"

if check_certbot_compat; then
    if [ "$EUID" -eq 0 ]; then
        "$CERTBOT_BIN" certificates
    else
        echo "需要 root 权限查看 Certbot 证书信息"
        echo "请使用: sudo $0"
    fi
fi

# 3. HTTPS 连接测试
echo ""
echo "3. HTTPS 连接测试"
echo "-------------------"

if command -v curl &> /dev/null; then
    echo "测试 HTTPS 连接到 https://$DOMAIN ..."
    
    if curl -I -s -o /dev/null -w "%{http_code}" "https://$DOMAIN" | grep -q "200\|301\|302"; then
        echo "✓ HTTPS 连接成功"
        
        # 显示 SSL 信息
        echo ""
        echo "SSL 协议信息:"
        curl -I -s -v "https://$DOMAIN" 2>&1 | grep -E "SSL|TLS"
    else
        echo "❌ HTTPS 连接失败"
    fi
else
    echo "curl 未安装，跳过连接测试"
fi

# 4. Nginx 配置检查
echo ""
echo "4. Nginx 配置检查"
echo "-------------------"

if command -v nginx &> /dev/null; then
    if nginx -t 2>&1 | grep -q "successful"; then
        echo "✓ Nginx 配置正确"
    else
        echo "❌ Nginx 配置有误"
        nginx -t
    fi
else
    echo "❌ Nginx 未安装"
fi

# 5. 自动续期检查
echo ""
echo "5. 自动续期配置检查"
echo "-------------------"

# 检查 systemd timer
if systemctl list-timers 2>/dev/null | grep -q certbot; then
    echo "✓ Certbot systemd timer 已配置"
    systemctl list-timers | grep certbot
else
    echo "⚠️  未检测到 Certbot systemd timer"
    
    # 检查 cron
    if [ "$EUID" -eq 0 ]; then
        if crontab -l 2>/dev/null | grep -q "certbot renew"; then
            echo "✓ Cron 任务已配置"
            crontab -l | grep "certbot renew"
        else
            echo "❌ 未配置自动续期"
        fi
    else
        echo "需要 root 权限检查 cron 配置"
    fi
fi

echo ""
echo "======================================"
echo "检查完成"
echo "======================================"
echo ""
echo "建议:"
echo "  - 定期运行此脚本检查证书状态"
echo "  - 使用 SSL Labs 进行深度测试:"
echo "    https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo ""

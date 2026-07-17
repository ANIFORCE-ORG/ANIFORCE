#!/bin/bash

# ANIFORCE SSL 证书续期脚本
# 用于手动触发证书续期或作为 cron 任务

set -e

LOG_FILE="/var/log/aniforce-ssl-renew.log"
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
    echo "❌ Certbot 运行环境不兼容" | tee -a "$LOG_FILE"
    echo "检测到 Certbot 可能依赖了已移除的 pyOpenSSL.crypto.X509Req API。" | tee -a "$LOG_FILE"
    echo "建议使用官方 snap 版 Certbot 隔离 Python 依赖:" | tee -a "$LOG_FILE"
    echo "  sudo apt remove -y certbot python3-certbot-nginx" | tee -a "$LOG_FILE"
    echo "  sudo snap install core" | tee -a "$LOG_FILE"
    echo "  sudo snap refresh core" | tee -a "$LOG_FILE"
    echo "  sudo snap install --classic certbot" | tee -a "$LOG_FILE"
    echo "  sudo ln -sf /snap/bin/certbot /usr/bin/certbot" | tee -a "$LOG_FILE"
}

check_certbot_compat() {
    local output
    if ! resolve_certbot; then
        echo "错误: Certbot 未安装" | tee -a "$LOG_FILE"
        return 1
    fi
    if ! output=$("$CERTBOT_BIN" --version 2>&1); then
        echo "$output" | tee -a "$LOG_FILE"
        if echo "$output" | grep -Eq "OpenSSL\\.crypto|X509Req|pyOpenSSL"; then
            print_certbot_compat_help
        else
            echo "错误: Certbot 启动失败，请检查安装环境" | tee -a "$LOG_FILE"
        fi
        return 1
    fi
    echo "✓ Certbot 可用: $CERTBOT_BIN" | tee -a "$LOG_FILE"
    echo "  $output" | tee -a "$LOG_FILE"
    return 0
}

echo "======================================"
echo "ANIFORCE SSL 证书续期"
echo "时间: $(date)"
echo "======================================"

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then 
    echo "错误: 请使用 sudo 运行此脚本" | tee -a "$LOG_FILE"
    exit 1
fi

# 续期证书
echo "检查证书续期..." | tee -a "$LOG_FILE"

if ! check_certbot_compat; then
    exit 1
fi

if "$CERTBOT_BIN" renew --quiet --post-hook "systemctl reload nginx" 2>&1 | tee -a "$LOG_FILE"; then
    echo "✓ 证书续期检查完成" | tee -a "$LOG_FILE"
    
    # 显示证书信息
    echo "" | tee -a "$LOG_FILE"
    echo "当前证书信息:" | tee -a "$LOG_FILE"
    "$CERTBOT_BIN" certificates 2>&1 | tee -a "$LOG_FILE"
else
    echo "错误: 证书续期失败" | tee -a "$LOG_FILE"
    exit 1
fi

echo "" | tee -a "$LOG_FILE"
echo "续期完成时间: $(date)" | tee -a "$LOG_FILE"
echo "======================================"

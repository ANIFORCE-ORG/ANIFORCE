#!/bin/bash

# ANIFORCE SSL 证书续期脚本
# 用于手动触发证书续期或作为 cron 任务

set -e

LOG_FILE="/var/log/aniforce-ssl-renew.log"

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

if certbot renew --quiet --post-hook "systemctl reload nginx" 2>&1 | tee -a "$LOG_FILE"; then
    echo "✓ 证书续期检查完成" | tee -a "$LOG_FILE"
    
    # 显示证书信息
    echo "" | tee -a "$LOG_FILE"
    echo "当前证书信息:" | tee -a "$LOG_FILE"
    certbot certificates 2>&1 | tee -a "$LOG_FILE"
else
    echo "错误: 证书续期失败" | tee -a "$LOG_FILE"
    exit 1
fi

echo "" | tee -a "$LOG_FILE"
echo "续期完成时间: $(date)" | tee -a "$LOG_FILE"
echo "======================================"

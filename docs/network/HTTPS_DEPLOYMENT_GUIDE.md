# HTTPS 接入部署方案

## 概述

本文档提供 ANIFORCE 项目的 HTTPS 接入完整方案，包括多种实施方案对比和详细部署步骤。

## 方案对比

| 方案 | 成本 | 难度 | 性能 | 自动续期 | CDN | 适用场景 |
|------|------|------|------|---------|-----|---------|
| Let's Encrypt | 免费 | 简单 | 好 | ✅ | ❌ | 所有场景 |
| Cloudflare | 免费 | 极简 | 优秀 | ✅ | ✅ | 需要全球加速 |
| 阿里云/腾讯云 | 免费 1年 | 简单 | 好 | ❌ | 可选 | 国内用户为主 |
| 自签名证书 | 免费 | 极简 | 好 | ❌ | ❌ | 仅开发测试 |

---

## 方案 1: Nginx + Let's Encrypt（推荐）

### 优势

- ✅ 完全免费的 SSL 证书
- ✅ 自动续期（90 天有效期，自动续期）
- ✅ 广泛使用，稳定可靠
- ✅ 支持通配符证书
- ✅ 无需依赖第三方服务

### 前置要求

1. 域名已解析到服务器 IP
2. 服务器开放 80 和 443 端口
3. 已安装 Nginx

### 部署步骤

#### 1. 安装 Certbot

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install certbot python3-certbot-nginx

# CentOS/RHEL 8+
sudo dnf install certbot python3-certbot-nginx

# CentOS/RHEL 7
sudo yum install certbot python3-certbot-nginx
```

#### 2. 获取 SSL 证书

**方式 A: 自动配置（推荐）**

```bash
# 自动获取证书
sudo certbot certonly --webroot -w /var/www/certbot -d www.aniforce.cc -d aniforce.cc

# 按提示输入邮箱和同意条款
```

**方式 B: 手动配置**

```bash
# 仅获取证书，不修改网关配置
sudo certbot certonly --webroot -w /var/www/certbot -d www.aniforce.cc -d aniforce.cc

# 证书位置：
# /etc/letsencrypt/live/www.aniforce.cc/fullchain.pem
# /etc/letsencrypt/live/www.aniforce.cc/privkey.pem
```

#### 3. 配置 Nginx

使用 UnionGateway 的配置模板：

`UnionGateway/nginx-https.conf` 会在运行时注入证书路径和端口。

#### 4. 启用配置

```bash
cd /path/to/UnionGateway
sudo ./deploy_gateway.sh --ssl --test-only
sudo ./deploy_gateway.sh --ssl
```

#### 5. 配置自动续期

```bash
# 测试续期（不会真正续期）
sudo certbot renew --dry-run

# 手动添加 cron
sudo crontab -e
# 添加以下行（每天凌晨 2 点检查续期）
0 2 * * * /path/to/UnionGateway/ssl/aniforce/renew_ssl.sh
```

#### 6. 验证 HTTPS

```bash
# 检查证书
sudo certbot certificates

# 测试 HTTPS 访问
curl -I https://www.aniforce.cc

# 使用 SSL Labs 测试（推荐）
# https://www.ssllabs.com/ssltest/analyze.html?d=www.aniforce.cc
```

---

## 方案 2: Cloudflare（推荐，最简单）

### 优势

- ✅ 完全免费
- ✅ 全球 CDN 加速
- ✅ DDoS 防护
- ✅ 自动 HTTPS 重定向
- ✅ 自动续期
- ✅ 配置极其简单
- ✅ 提供 Web 应用防火墙（WAF）

### 部署步骤

#### 1. 注册并添加域名

1. 访问 [Cloudflare](https://www.cloudflare.com/) 注册账号
2. 点击 "Add a Site"
3. 输入域名 `aniforce.cc`
4. 选择免费计划（Free Plan）

#### 2. 修改 DNS 服务器

Cloudflare 会提供两个 NS 服务器地址，例如：
```
ns1.cloudflare.com
ns2.cloudflare.com
```

到域名注册商（如阿里云、腾讯云）修改 DNS 服务器为 Cloudflare 提供的地址。

#### 3. 配置 DNS 记录

在 Cloudflare DNS 管理页面添加记录：

```
类型    名称    内容                代理状态
A       @       YOUR_SERVER_IP      已代理（橙色云朵）
A       www     YOUR_SERVER_IP      已代理（橙色云朵）
```

#### 4. 配置 SSL/TLS

在 Cloudflare SSL/TLS 设置中：

1. **SSL/TLS 加密模式**：选择 "Full" 或 "Full (strict)"
   - Full: Cloudflare 到源服务器使用任何 SSL 证书
   - Full (strict): 需要源服务器有有效的 SSL 证书（推荐配合 Let's Encrypt）

2. **Always Use HTTPS**：开启（强制 HTTPS）

3. **Automatic HTTPS Rewrites**：开启（自动重写 HTTP 链接）

4. **Minimum TLS Version**：选择 TLS 1.2

5. **TLS 1.3**：开启

#### 5. 配置页面规则（可选）

创建页面规则强制 HTTPS：

```
URL: http://*aniforce.cc/*
设置: Always Use HTTPS
```

#### 6. 源服务器配置

**选项 A: 仅 HTTP（简单）**

如果选择 SSL/TLS 模式为 "Flexible"，源服务器可以只使用 HTTP：

```nginx
server {
    listen 80;
    server_name www.aniforce.cc aniforce.cc;
    
    location / {
        proxy_pass http://localhost:3010;
        # ... 其他配置
    }
}
```

**选项 B: HTTPS（推荐，更安全）**

配合 Let's Encrypt，使用 "Full (strict)" 模式：

```bash
# 安装 Let's Encrypt 证书（参考方案 1）
sudo certbot certonly --webroot -w /var/www/certbot -d www.aniforce.cc

# Nginx 配置同方案 1
```

#### 7. 优化配置（可选）

在 Cloudflare 控制台：

1. **Speed → Optimization**
   - Auto Minify: 开启 JavaScript, CSS, HTML
   - Brotli: 开启

2. **Caching → Configuration**
   - Caching Level: Standard
   - Browser Cache TTL: 4 hours

3. **Network**
   - HTTP/2: 开启
   - HTTP/3 (with QUIC): 开启
   - WebSockets: 开启

---

## 方案 3: 阿里云/腾讯云 SSL 证书

### 优势

- ✅ 免费 1 年 DV 证书
- ✅ 国内访问速度快
- ✅ 可配合 CDN 使用
- ✅ 中文支持好

### 部署步骤

#### 1. 申请证书

**阿里云**：
1. 登录阿里云控制台
2. 产品与服务 → SSL 证书
3. 免费证书 → 立即购买
4. 选择 DV 单域名证书（免费版）
5. 填写域名 `www.aniforce.cc`

**腾讯云**：
1. 登录腾讯云控制台
2. SSL 证书管理
3. 申请免费证书
4. 填写域名信息

#### 2. 域名验证

选择验证方式：

**DNS 验证（推荐）**：
```
记录类型: TXT
主机记录: _dnsauth
记录值: 202406031234567890abcdef（证书商提供）
```

**文件验证**：
上传验证文件到网站根目录 `.well-known/pki-validation/`

#### 3. 下载证书

验证通过后，下载证书：
- 选择 Nginx 格式
- 下载得到 `.pem` 和 `.key` 文件

#### 4. 上传到服务器

```bash
# 创建证书目录
sudo mkdir -p /etc/nginx/ssl

# 上传证书文件
sudo scp your_cert.pem root@your_server:/etc/nginx/ssl/
sudo scp your_cert.key root@your_server:/etc/nginx/ssl/

# 设置权限
sudo chmod 600 /etc/nginx/ssl/*
sudo chown root:root /etc/nginx/ssl/*
```

#### 5. 配置 Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name www.aniforce.cc;
    
    # SSL 证书配置
    ssl_certificate /etc/nginx/ssl/your_cert.pem;
    ssl_certificate_key /etc/nginx/ssl/your_cert.key;
    
    # 其他配置同方案 1
}
```

#### 6. 续期提醒

免费证书 1 年到期，需要：
1. 提前 1-2 个月重新申请
2. 下载新证书
3. 替换服务器上的证书文件
4. 重启 Nginx

---

## 方案 4: 自签名证书（仅开发测试）

### 使用场景

- ⚠️ 仅用于本地开发和测试
- ⚠️ 浏览器会显示不安全警告
- ⚠️ 不适合生产环境

### 生成证书

```bash
# 生成私钥和证书（有效期 365 天）
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/selfsigned.key \
  -out /etc/nginx/ssl/selfsigned.crt \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=ANIFORCE/CN=localhost"

# 设置权限
sudo chmod 600 /etc/nginx/ssl/selfsigned.*
```

### 配置 Nginx

```nginx
server {
    listen 443 ssl http2;
    server_name localhost;
    
    ssl_certificate /etc/nginx/ssl/selfsigned.crt;
    ssl_certificate_key /etc/nginx/ssl/selfsigned.key;
    
    # 其他配置
}
```

---

## 推荐方案：Cloudflare + Let's Encrypt

### 架构

```
客户端 → Cloudflare CDN (HTTPS) → 源服务器 (HTTPS)
```

### 优势

- ✅ 双重 HTTPS 加密（最安全）
- ✅ 全球 CDN 加速
- ✅ DDoS 防护
- ✅ 完全免费
- ✅ 自动续期

### 部署步骤

1. **配置 Cloudflare**（参考方案 2）
   - SSL/TLS 模式选择 "Full (strict)"

2. **配置 Let's Encrypt**（参考方案 1）
   - 在源服务器安装 Let's Encrypt 证书

3. **验证**
   ```bash
   # 检查 Cloudflare 到客户端的 HTTPS
   curl -I https://www.aniforce.cc
   
   # 检查源服务器的 HTTPS
   curl -I https://YOUR_SERVER_IP --resolve www.aniforce.cc:443:YOUR_SERVER_IP
   ```

---

## ANIFORCE 项目配置更新

### 1. 更新环境变量

```bash
# backend/.env
FRONTEND_BASE_URL=https://www.aniforce.cc
BACKEND_BASE_URL=https://www.aniforce.cc
OAUTH_REDIRECT_BASE_URL=https://www.aniforce.cc
```

### 2. 更新 deploy_server.sh

在 `deploy_server.sh` 中添加 HTTPS 支持检测：

```bash
# 检测是否使用 HTTPS
if [[ "$BACKEND_BASE_URL" == https://* ]]; then
  info "检测到 HTTPS 配置，确保已配置 SSL 证书"
fi
```

### 3. 更新 Nginx 配置模板

修改 `deploy_server.sh` 中的 Nginx 配置生成逻辑，支持 HTTPS。

---

## 故障排查

### 问题 1: 证书获取失败

**症状**：`certbot` 报错 "Failed to obtain certificate"

**解决方案**：
```bash
# 检查域名解析
nslookup www.aniforce.cc

# 检查 80 端口是否开放
sudo netstat -tlnp | grep :80

# 检查防火墙
sudo ufw status
sudo firewall-cmd --list-all

# 手动测试 ACME 验证
curl http://www.aniforce.cc/.well-known/acme-challenge/test
```

### 问题 2: 证书续期失败

**症状**：证书过期，续期失败

**解决方案**：
```bash
# 查看续期日志
sudo journalctl -u certbot.timer

# 手动续期
sudo certbot renew --force-renewal

# 检查 Nginx 配置
sudo nginx -t
```

### 问题 3: Mixed Content 警告

**症状**：HTTPS 页面加载 HTTP 资源

**解决方案**：
```nginx
# 在 Nginx 配置中添加
add_header Content-Security-Policy "upgrade-insecure-requests" always;
```

### 问题 4: Cloudflare 重定向循环

**症状**：访问网站出现 "Too many redirects"

**解决方案**：
1. 检查 Cloudflare SSL 模式（应为 Full 或 Full strict）
2. 检查源服务器是否正确配置 HTTPS
3. 移除源服务器的 HTTP → HTTPS 重定向（由 Cloudflare 处理）

---

## 安全最佳实践

### 1. SSL 配置优化

```nginx
# 使用现代加密套件
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
ssl_prefer_server_ciphers off;

# 启用 OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/letsencrypt/live/www.aniforce.cc/chain.pem;
```

### 2. 安全头配置

```nginx
# HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# 防止点击劫持
add_header X-Frame-Options "SAMEORIGIN" always;

# 防止 MIME 类型嗅探
add_header X-Content-Type-Options "nosniff" always;

# XSS 保护
add_header X-XSS-Protection "1; mode=block" always;

# CSP
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;
```

### 3. 定期检查

```bash
# 使用 SSL Labs 测试
# https://www.ssllabs.com/ssltest/

# 检查证书有效期
sudo certbot certificates

# 检查 Nginx 配置
sudo nginx -t
```

---

## 监控和告警

### 1. 证书过期监控

```bash
# 创建监控脚本
cat > /usr/local/bin/check_ssl_expiry.sh << 'EOF'
#!/bin/bash
DOMAIN="www.aniforce.cc"
DAYS_WARNING=30

EXPIRY_DATE=$(echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

if [ $DAYS_LEFT -lt $DAYS_WARNING ]; then
  echo "WARNING: SSL certificate for $DOMAIN expires in $DAYS_LEFT days"
  # 发送告警邮件或通知
fi
EOF

chmod +x /usr/local/bin/check_ssl_expiry.sh

# 添加到 cron
echo "0 9 * * * /usr/local/bin/check_ssl_expiry.sh" | sudo crontab -
```

### 2. HTTPS 可用性监控

使用外部监控服务：
- UptimeRobot (免费)
- Pingdom
- StatusCake

---

## 参考资料

- [Let's Encrypt 官方文档](https://letsencrypt.org/docs/)
- [Certbot 用户指南](https://certbot.eff.org/docs/)
- [Cloudflare SSL/TLS 文档](https://developers.cloudflare.com/ssl/)
- [Mozilla SSL 配置生成器](https://ssl-config.mozilla.org/)
- [SSL Labs 测试工具](https://www.ssllabs.com/ssltest/)

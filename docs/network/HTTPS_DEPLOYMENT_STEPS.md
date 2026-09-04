# ANIFORCE HTTPS 部署实施步骤

本文档提供 ANIFORCE 项目 HTTPS 部署的详细步骤，采用 **Nginx + Let's Encrypt** 方案。

## 📋 前置要求

在开始部署前，请确保满足以下条件：

- ✅ 域名 `www.aniforce.cc` 和 `aniforce.cc` 已解析到服务器 IP
- ✅ 服务器已开放 80 和 443 端口
- ✅ 服务器已安装 Nginx
- ✅ 具有 root 或 sudo 权限
- ✅ 前端服务运行在 `localhost:3010`
- ✅ 后端 API 服务运行在 `localhost:8010`

## 🚀 快速部署

### 方式一：使用自动化脚本（推荐）

1. **赋予脚本执行权限**

```bash
cd /path/to/UnionGateway/ssl/aniforce
chmod +x setup_ssl.sh renew_ssl.sh check_ssl.sh test_nginx_config.sh
```

2. **运行 SSL 配置脚本**

```bash
sudo ./setup_ssl.sh
```

脚本会自动完成：
   - 检测操作系统并安装 Certbot
   - 创建验证目录
   - 获取 SSL 证书
   - 校验并重载 UnionGateway
   - 设置自动续期

3. **验证部署**

```bash
sudo ./check_ssl.sh
```

### 方式二：手动部署

如果自动化脚本遇到问题，可以按以下步骤手动部署。

## 📝 手动部署详细步骤

### 步骤 1: 安装 Certbot

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

**CentOS/RHEL 8+:**
```bash
sudo dnf install -y certbot python3-certbot-nginx
```

**CentOS/RHEL 7:**
```bash
sudo yum install -y certbot python3-certbot-nginx
```

### 步骤 2: 创建验证目录

```bash
sudo mkdir -p /var/www/certbot
```

### 步骤 3: 获取 SSL 证书

**选项 A: 自动配置（推荐）**

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d www.aniforce.cc -d aniforce.cc \
  --email support@aniforce.cc \
  --agree-tos \
  --non-interactive
```

**选项 B: 手动配置**

```bash
sudo certbot certonly --webroot -w /var/www/certbot -d www.aniforce.cc -d aniforce.cc \
  --email support@aniforce.cc \
  --agree-tos \
  --non-interactive
```

证书将保存在：
- 证书: `/etc/letsencrypt/live/www.aniforce.cc/fullchain.pem`
- 私钥: `/etc/letsencrypt/live/www.aniforce.cc/privkey.pem`

### 步骤 4: 部署 UnionGateway Nginx

```bash
cd /path/to/UnionGateway
sudo ./deploy_gateway.sh --ssl --test-only
sudo ./deploy_gateway.sh --ssl
```

### 步骤 5: 配置自动续期

Let's Encrypt 证书有效期为 90 天，需要配置自动续期。

**检查 systemd timer（推荐）:**

```bash
sudo systemctl list-timers | grep certbot
```

如果已配置，会显示 certbot 的定时任务。

**手动配置 cron（备选）:**

```bash
sudo crontab -e
```

添加以下行：
```
0 2 * * * /path/to/UnionGateway/ssl/aniforce/renew_ssl.sh
```

**测试续期:**

```bash
sudo certbot renew --dry-run
```

### 步骤 6: 验证 HTTPS

1. **检查证书信息**

```bash
sudo certbot certificates
```

2. **测试 HTTPS 访问**

```bash
curl -I https://www.aniforce.cc
```

3. **使用浏览器访问**

访问 `https://www.aniforce.cc`，检查：
- 地址栏显示锁图标
- 证书有效
- HTTP 自动重定向到 HTTPS

4. **SSL Labs 深度测试**

访问 [SSL Labs](https://www.ssllabs.com/ssltest/analyze.html?d=www.aniforce.cc) 进行全面的 SSL 配置测试。

## 🔧 日常维护

### 检查证书状态

```bash
sudo /path/to/UnionGateway/ssl/aniforce/check_ssl.sh
```

### 手动续期证书

```bash
sudo /path/to/UnionGateway/ssl/aniforce/renew_ssl.sh
```

### 查看 Nginx 日志

```bash
# 访问日志
sudo tail -f /path/to/UnionGateway/logs/gateway_access_*.log

# 错误日志
sudo tail -f /path/to/UnionGateway/logs/gateway_error_*.log
```

### 查看续期日志

```bash
sudo tail -f /var/log/aniforce-ssl-renew.log
```

## 🔒 安全配置说明

配置文件已包含以下安全措施：

1. **TLS 版本**: 仅支持 TLSv1.2 和 TLSv1.3
2. **加密套件**: 使用现代安全的加密算法
3. **HSTS**: 强制浏览器使用 HTTPS（有效期 1 年）
4. **安全头**: 
   - `X-Frame-Options`: 防止点击劫持
   - `X-Content-Type-Options`: 防止 MIME 类型嗅探
   - `X-XSS-Protection`: XSS 保护

## 🐛 常见问题

### 1. 证书获取失败

**问题**: Certbot 无法验证域名

**解决方案**:
- 确认域名 DNS 解析正确：`dig www.aniforce.cc`
- 确认防火墙开放 80 端口
- 检查 UnionGateway 是否正在运行

### 2. Nginx 配置测试失败

**问题**: `nginx -t` 报错

**解决方案**:
- 检查配置文件语法
- 确认证书文件路径正确
- 查看详细错误信息

### 3. 自动续期不工作

**问题**: 证书过期未自动续期

**解决方案**:
- 检查 systemd timer: `sudo systemctl status certbot.timer`
- 检查 cron 任务: `sudo crontab -l`
- 手动测试续期: `sudo certbot renew --dry-run`

### 4. HTTP 未重定向到 HTTPS

**问题**: 访问 HTTP 不自动跳转

**解决方案**:
- 确认 Nginx 配置中的重定向规则
- 重载网关: `cd /path/to/UnionGateway && sudo ./deploy_gateway.sh --ssl`
- 清除浏览器缓存

## 📞 支持

如遇到问题，请：

1. 查看日志文件
2. 运行 `check_ssl.sh` 脚本诊断
3. 联系系统管理员

## 📚 相关文档

- [Let's Encrypt 官方文档](https://letsencrypt.org/docs/)
- [Certbot 文档](https://certbot.eff.org/docs/)
- [Nginx SSL 配置指南](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [SSL Labs 测试工具](https://www.ssllabs.com/ssltest/)

---

**最后更新**: 2026-06-03
**维护者**: ANIFORCE DevOps Team

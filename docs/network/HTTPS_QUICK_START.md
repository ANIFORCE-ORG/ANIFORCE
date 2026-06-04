# ANIFORCE HTTPS 快速部署指南

本指南帮助您快速为 ANIFORCE 项目配置 HTTPS（采用方案1: Nginx + Let's Encrypt）。

## ⚡ 一键部署

```bash
# 1. 进入 SSL 脚本目录
cd scripts/ssl

# 2. 赋予执行权限
chmod +x setup_ssl.sh renew_ssl.sh check_ssl.sh

# 3. 运行自动配置脚本
sudo ./setup_ssl.sh

# 4. 验证部署
sudo ./check_ssl.sh
```

完成！您的网站现在已支持 HTTPS。

## 📋 前置检查清单

在运行部署脚本前，请确认：

- [ ] 域名 `www.aniforce.cc` 和 `aniforce.cc` 已解析到服务器 IP
- [ ] 服务器已开放 80 和 443 端口
- [ ] 服务器已安装 Nginx
- [ ] 前端服务运行在 `localhost:3010`
- [ ] 后端 API 服务运行在 `localhost:8010`
- [ ] 具有 root 或 sudo 权限

## 📁 已创建的文件

### 配置文件
- `nginx-https.conf` - Nginx HTTPS 配置

### 脚本文件
- `scripts/ssl/setup_ssl.sh` - SSL 自动配置脚本
- `scripts/ssl/renew_ssl.sh` - SSL 证书续期脚本
- `scripts/ssl/check_ssl.sh` - SSL 状态检查脚本

### 文档文件
- `docs/HTTPS_DEPLOYMENT_STEPS.md` - 详细部署步骤
- `HTTPS_QUICK_START.md` - 快速开始指南（本文件）

## 🔧 常用命令

### 检查证书状态
```bash
sudo ./scripts/ssl/check_ssl.sh
```

### 手动续期证书
```bash
sudo ./scripts/ssl/renew_ssl.sh
```

### 查看 Nginx 日志
```bash
# 访问日志
sudo tail -f /var/log/nginx/aniforce_access.log

# 错误日志
sudo tail -f /var/log/nginx/aniforce_error.log
```

### 重启 Nginx
```bash
sudo systemctl restart nginx
```

## 🎯 部署后验证

1. **浏览器访问**: `https://www.aniforce.cc`
   - 检查地址栏是否显示锁图标
   - 确认证书有效

2. **命令行测试**:
   ```bash
   curl -I https://www.aniforce.cc
   ```

3. **SSL Labs 测试**:
   访问 https://www.ssllabs.com/ssltest/analyze.html?d=www.aniforce.cc

## 📚 详细文档

如需了解更多细节或遇到问题，请查看：

- [HTTPS 部署详细步骤](docs/HTTPS_DEPLOYMENT_STEPS.md)
- [HTTPS 部署完整指南](docs/network/HTTPS_DEPLOYMENT_GUIDE.md)

## 🔒 安全特性

已配置的安全特性：

- ✅ 自动 HTTP 到 HTTPS 重定向
- ✅ TLSv1.2 和 TLSv1.3 支持
- ✅ HSTS（强制 HTTPS）
- ✅ 安全响应头（X-Frame-Options, X-Content-Type-Options 等）
- ✅ 90 天自动续期

## 💡 提示

- 证书有效期为 90 天，已配置自动续期
- 建议定期运行 `check_ssl.sh` 检查证书状态
- 首次部署后，浏览器可能需要清除缓存才能看到 HTTPS

---

**维护者**: ANIFORCE DevOps Team  
**最后更新**: 2026-06-03

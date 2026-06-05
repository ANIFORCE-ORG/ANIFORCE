# ANIFORCE SSL 部署使用指南

本文档说明如何使用 `deploy_server.sh` 和 `undeploy_server.sh` 脚本的 `--ssl` 参数来管理 HTTPS 服务。

## 📋 前提条件

在使用 `--ssl` 参数前，必须先完成 SSL 证书配置：

```bash
# 1. 进入 SSL 脚本目录
cd scripts/ssl

# 2. 运行 SSL 配置脚本
sudo ./setup_ssl.sh

# 3. 验证证书安装
sudo ./check_ssl.sh
```

## 🚀 使用 --ssl 参数部署

### 基本用法

```bash
# 启用 HTTPS 模式部署
./deploy_server.sh --ssl
```

### 完整示例

```bash
# 生产环境 HTTPS 部署
./deploy_server.sh --mode cloud --ssl --skip-install

# 仅启动 Nginx (HTTPS)
./deploy_server.sh --only nginx --ssl

# 自定义端口 + HTTPS
./deploy_server.sh --ssl --frontend-port 3010 --backend-port 8010
```

## 🛑 停止 HTTPS 服务

### 基本用法

```bash
# 停止所有服务（自动检测 SSL 模式）
./undeploy_server.sh

# 明确指定停止 HTTPS 模式
./undeploy_server.sh --ssl
```

### 完整示例

```bash
# 仅停止 Nginx (HTTPS)
./undeploy_server.sh --only nginx --ssl

# 停止所有 HTTPS 服务
./undeploy_server.sh --ssl
```

## 🔄 工作流程

### 开发环境（HTTP）

```bash
# 1. 启动开发服务（不使用 SSL）
./deploy_server.sh

# 2. 访问应用
open http://localhost

# 3. 停止服务
./undeploy_server.sh
```

### 生产环境（HTTPS）

```bash
# 1. 首次部署：配置 SSL 证书
cd scripts/ssl
sudo ./setup_ssl.sh
cd ../..

# 2. 启动 HTTPS 服务
./deploy_server.sh --ssl --mode cloud --skip-install

# 3. 访问应用
# https://www.aniforce.cc

# 4. 停止服务
./undeploy_server.sh --ssl
```

## 📊 参数对比

| 参数 | HTTP 模式 | HTTPS 模式 (--ssl) |
|------|----------|-------------------|
| **Nginx 配置** | `nginx.conf` | `nginx-https.conf` |
| **监听端口** | 自定义（默认 80） | 80 (HTTP) + 443 (HTTPS) |
| **域名** | localhost | www.aniforce.cc |
| **SSL 证书** | 不需要 | 必需 |
| **启动权限** | 普通用户 | sudo (root) |
| **访问方式** | http://localhost | https://www.aniforce.cc |

## 🔍 --ssl 参数的作用

### deploy_server.sh --ssl

1. **选择配置文件**：使用 `nginx-https.conf` 而不是 `nginx.conf`
2. **检查 SSL 证书**：验证 Let's Encrypt 证书是否存在
3. **生成运行时配置**：替换端口和日志路径
4. **使用 sudo 启动**：HTTPS 需要 root 权限绑定 443 端口
5. **显示 HTTPS 地址**：输出 https:// 访问地址

### undeploy_server.sh --ssl

1. **读取部署配置**：从 `.deploy_config` 读取 SSL 状态
2. **使用 sudo 停止**：HTTPS 模式需要 root 权限
3. **清理多个端口**：同时清理 80 和 443 端口
4. **强制清理进程**：确保 Nginx 完全停止

## ⚙️ 配置文件自动检测

脚本会自动从 `.deploy_config` 文件读取部署配置：

```bash
# 部署时自动保存配置
./deploy_server.sh --ssl
# 创建 .deploy_config 文件，包含 USE_SSL=true

# 停止时自动读取配置
./undeploy_server.sh
# 自动检测到 USE_SSL=true，使用 HTTPS 模式停止
```

## 🔒 安全注意事项

1. **证书验证**：`--ssl` 参数会检查 SSL 证书是否存在
2. **权限要求**：HTTPS 模式需要 sudo 权限
3. **端口占用**：确保 80 和 443 端口未被其他服务占用
4. **防火墙配置**：确保服务器防火墙开放 80 和 443 端口

## 🐛 故障排除

### 问题 1: SSL 证书未找到

```
错误: SSL 证书未找到，请先运行: sudo ./scripts/ssl/setup_ssl.sh
```

**解决方案**：
```bash
cd scripts/ssl
sudo ./setup_ssl.sh
```

### 问题 2: 权限不足

```
错误: Nginx 启动失败
```

**解决方案**：
```bash
# HTTPS 模式需要 sudo
sudo ./deploy_server.sh --ssl
```

### 问题 3: 端口被占用

```
警告: 端口 443 已被占用
```

**解决方案**：
```bash
# 停止现有服务
./undeploy_server.sh --ssl

# 或手动清理
sudo lsof -ti :443 | xargs sudo kill -9
```

### 问题 4: 无法访问 HTTPS

**检查清单**：
1. DNS 解析是否正确：`dig www.aniforce.cc`
2. 防火墙是否开放：`sudo ufw status`
3. Nginx 是否运行：`sudo systemctl status nginx`
4. 证书是否有效：`sudo ./scripts/ssl/check_ssl.sh`

## 📚 相关文档

- [HTTPS 快速部署指南](../docs/network/HTTPS_QUICK_START.md)
- [HTTPS 详细部署步骤](HTTPS_DEPLOYMENT_STEPS.md)
- [HTTPS 部署完整指南](network/HTTPS_DEPLOYMENT_GUIDE.md)
- [SSL 脚本使用说明](../scripts/README.md)

## 💡 最佳实践

1. **开发环境**：使用 HTTP 模式（不带 `--ssl`）
   ```bash
   ./deploy_server.sh
   ```

2. **生产环境**：使用 HTTPS 模式（带 `--ssl`）
   ```bash
   ./deploy_server.sh --ssl --mode cloud
   ```

3. **证书续期**：定期检查证书状态
   ```bash
   sudo ./scripts/ssl/check_ssl.sh
   ```

4. **自动续期**：已配置 cron 任务，无需手动操作

---

**维护者**: ANIFORCE DevOps Team  
**最后更新**: 2026-06-04

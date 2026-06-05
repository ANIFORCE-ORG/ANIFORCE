# Scripts 目录说明

本目录包含 ANIFORCE 项目的服务器管理和维护脚本。

## 📁 目录结构

```
scripts/
├── ssl/                    # SSL 证书管理脚本
│   ├── setup_ssl.sh       # SSL 自动配置
│   ├── renew_ssl.sh       # SSL 证书续期
│   ├── check_ssl.sh       # SSL 状态检查
│   └── test_nginx_config.sh  # Nginx 配置测试
├── logger/                 # 日志管理脚本
│   └── rotate_logs.sh     # 日志轮转
├── crontab.example         # Crontab 配置示例
└── README.md               # 本说明文件
```

## 📂 子目录说明

### 🔒 ssl/ - SSL 证书管理

SSL 证书相关的自动化脚本，用于 HTTPS 部署和维护。

#### `ssl/setup_ssl.sh`
SSL 证书自动配置脚本，用于首次部署 HTTPS。

**功能**：
- 自动检测操作系统并安装 Certbot
- 获取 Let's Encrypt SSL 证书
- 配置 Nginx HTTPS
- 设置自动续期

**使用方法**：
```bash
cd scripts/ssl
chmod +x setup_ssl.sh
sudo ./setup_ssl.sh
```

#### `ssl/renew_ssl.sh`
SSL 证书手动续期脚本。

**功能**：
- 手动触发证书续期
- 自动重载 Nginx 配置
- 记录续期日志到 `/var/log/aniforce-ssl-renew.log`

**使用方法**：
```bash
cd scripts/ssl
sudo ./renew_ssl.sh
```

#### `ssl/check_ssl.sh`
SSL 证书状态检查脚本。

**功能**：
- 检查证书文件和有效期
- 计算证书剩余天数
- 测试 HTTPS 连接
- 验证 Nginx 配置
- 检查自动续期配置

**使用方法**：
```bash
cd scripts/ssl
sudo ./check_ssl.sh
```

#### `ssl/test_nginx_config.sh`
Nginx 配置文件测试脚本。

**功能**：
- 测试 HTTP 配置文件（nginx.conf）
- 测试 HTTPS 配置文件（nginx-https.conf）
- 验证配置文件语法正确性
- 快速诊断配置问题
- 支持 macOS 和 Linux 环境
- 自动检测操作系统类型

**使用方法**：
```bash
cd scripts/ssl

# 自动检测环境
./test_nginx_config.sh

# 指定 macOS 环境
./test_nginx_config.sh --env mac

# 指定 Linux 环境
./test_nginx_config.sh --env linux
```

**参数说明**：
- `--env mac` - 使用 macOS 的 mime.types 路径（/opt/homebrew/etc/nginx/mime.types）
- `--env linux` - 使用 Linux 的 mime.types 路径（/etc/nginx/mime.types）
- 不指定参数时自动检测操作系统

### 📊 logger/ - 日志管理

日志文件管理和轮转相关脚本。

#### `logger/rotate_logs.sh`
日志轮转脚本，用于管理应用日志文件。

**功能**：
- 自动归档旧日志
- 压缩历史日志文件
- 清理过期日志

**使用方法**：
```bash
cd scripts/logger
./rotate_logs.sh
```

## 📄 配置文件

### `crontab.example`
Crontab 配置示例文件，包含推荐的定时任务配置。

**使用方法**：
```bash
# 查看示例
cat crontab.example

# 编辑 crontab
crontab -e
# 然后将示例内容复制进去
```

## 📚 相关文档

- [HTTPS 快速部署指南](../HTTPS_QUICK_START.md)
- [HTTPS 详细部署步骤](../docs/HTTPS_DEPLOYMENT_STEPS.md)
- [HTTPS 部署完整指南](../docs/network/HTTPS_DEPLOYMENT_GUIDE.md)

## 🔧 使用规范

1. **执行权限**
   - 所有 `.sh` 脚本需要执行权限
   - 使用 `chmod +x script_name.sh` 赋予权限

2. **Root 权限**
   - SSL 相关脚本需要 root 权限
   - 使用 `sudo` 执行

3. **日志记录**
   - SSL 续期日志: `/var/log/aniforce-ssl-renew.log`
   - Nginx 日志: `/var/log/nginx/aniforce_*.log`

---

**维护者**: ANIFORCE DevOps Team  
**最后更新**: 2026-06-03

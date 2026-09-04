# Scripts 目录说明

本目录包含 ANIFORCE 项目的服务器管理和维护脚本。SSL 脚本已迁移到 `../UnionGateway/ssl/aniforce/`。

## 📁 目录结构

```
scripts/
├── logger/                 # 日志管理脚本
│   └── rotate_logs.sh     # 日志轮转
├── crontab.example         # Crontab 配置示例
└── README.md               # 本说明文件
```

## 📂 子目录说明

### 🔒 ssl/ - SSL 证书管理

SSL 相关脚本已迁移到 `../UnionGateway/ssl/aniforce/`，用于管理 ANIFORCE 站点证书、续期和 Nginx 校验。

**使用方法**：
```bash
cd ../UnionGateway/ssl/aniforce
chmod +x setup_ssl.sh renew_ssl.sh check_ssl.sh test_nginx_config.sh
sudo ./setup_ssl.sh
sudo ./check_ssl.sh
```

**常用脚本**：
- `setup_ssl.sh` - 首次配置证书
- `renew_ssl.sh` - 手动续期
- `check_ssl.sh` - 证书状态检查
- `test_nginx_config.sh` - Nginx 配置测试

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

- [HTTPS 快速部署指南](../docs/network/HTTPS_QUICK_START.md)
- [HTTPS 详细部署步骤](../docs/network/HTTPS_DEPLOYMENT_STEPS.md)
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
   - 网关日志: `../../UnionGateway/logs/gateway_*.log`

---

**维护者**: ANIFORCE DevOps Team  
**最后更新**: 2026-06-03

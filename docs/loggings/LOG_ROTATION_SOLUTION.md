# 跨天日志轮转解决方案

## 问题描述

当服务跨天运行时，如何确保日志文件按日期正确分离？

### 场景示例

```
6月3日 23:50 启动服务
  ↓
写入 backend_logs_20260603.log
  ↓
6月4日 00:00 （跨天）
  ↓
期望：写入 backend_logs_20260604.log
实际：？
```

## 解决方案总览

ANIFORCE 采用**分层轮转策略**，针对不同组件使用不同的轮转机制：

| 组件 | 轮转机制 | 跨天支持 | 说明 |
|------|---------|---------|------|
| **后端** | loguru 自动轮转 | ✅ 完全支持 | 每天午夜自动切换文件 |
| **前端** | 启动时确定 + Cron | ⚠️ 需配置 | 通过 cron 定期清理 |
| **Nginx** | 启动时确定 + Cron | ⚠️ 需配置 | 通过 cron 定期清理 |

## 详细方案

### 方案 1: 后端日志（自动轮转）✅

#### 实现原理

后端使用 **loguru** 库的时间占位符和自动轮转功能：

```python
# backend/app/config/logging.py
logger.add(
    "logs/backend_logs_{time:YYYYMMDD}.log",
    rotation="00:00",  # 每天午夜轮转
    retention="30 days",
    compression="zip"
)
```

#### 文件名模板

```bash
# run_server.sh 中的配置
BACKEND_LOG="$LOG_DIR/backend_logs_{time:YYYYMMDD}.log"
```

注意 `{time:YYYYMMDD}` 是 loguru 的占位符，会在运行时自动替换。

#### 跨天行为

```
6月3日 23:50 启动
  ↓
loguru 创建: backend_logs_20260603.log
  ↓
6月4日 00:00 （午夜）
  ↓
loguru 自动切换: backend_logs_20260604.log ✅
  ↓
旧文件自动压缩: backend_logs_20260603.log.zip
```

#### 优点

- ✅ 完全自动化，无需人工干预
- ✅ 支持自动压缩旧日志
- ✅ 可配置保留天数
- ✅ 跨天无缝切换

#### 验证方法

```bash
# 启动后端
./run_server.sh --only backend

# 查看日志文件（会看到 {time:YYYYMMDD} 被替换为实际日期）
ls -lh logs/backend_logs_*.log

# 等待跨天后检查
# 应该会看到新的日期文件
```

### 方案 2: 前端和 Nginx 日志（Cron 轮转）⚠️

#### 问题说明

Vite 和 Nginx 不支持自动日志轮转，文件名在启动时确定：

```bash
# 启动时确定
FRONTEND_LOG="$LOG_DIR/frontend_logs_20260603.log"
NGINX_ACCESS_LOG="$LOG_DIR/nginx_access_20260603.log"

# 跨天后仍写入同一文件
# 6月4日的日志 → frontend_logs_20260603.log ❌
```

#### 解决方案：使用 Cron + 日志轮转脚本

##### 步骤 1: 使用日志轮转脚本

```bash
# 手动运行（测试）
./scripts/rotate_logs.sh --compress --retention 7

# 查看帮助
./scripts/rotate_logs.sh --help
```

##### 步骤 2: 配置 Cron 定时任务

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天午夜运行）
0 0 * * * /path/to/aniforce/scripts/rotate_logs.sh --log-dir /path/to/aniforce/logs --compress --retention 30 >> /var/log/aniforce_cron.log 2>&1
```

##### 步骤 3: 验证 Cron 配置

```bash
# macOS: 查看 cron 日志
log show --predicate 'process == "cron"' --last 1h

# Linux: 查看 cron 日志
tail -f /var/log/cron
# 或
tail -f /var/log/syslog | grep CRON

# 查看轮转脚本的输出
tail -f /var/log/aniforce_cron.log
```

#### Cron 工作流程

```
每天 00:00
  ↓
Cron 触发 rotate_logs.sh
  ↓
脚本执行:
  1. 删除 30 天前的日志
  2. 压缩 1 天前的日志
  3. 生成统计报告
  ↓
完成
```

#### 优点

- ✅ 适用于任何不支持自动轮转的服务
- ✅ 可配置保留天数和压缩策略
- ✅ 提供详细的统计信息
- ✅ 一次配置，长期有效

#### 缺点

- ⚠️ 需要配置 cron（一次性工作）
- ⚠️ 跨天时日志仍在旧文件中（但会被定期清理）

### 方案 3: 定期重启服务（不推荐）

#### 说明

通过定期重启服务来触发新的日志文件创建。

```bash
# 每天午夜重启服务
0 0 * * * /path/to/aniforce/undeploy_server.sh && /path/to/aniforce/deploy_server.sh
```

#### 优点

- ✅ 简单直接
- ✅ 确保日志文件按日期分离

#### 缺点

- ❌ 服务中断（虽然很短暂）
- ❌ 可能影响正在进行的请求
- ❌ 不适合生产环境

## 推荐配置

### 开发环境

```bash
# 直接使用默认配置
./run_server.sh

# 后端日志自动轮转
# 前端和 Nginx 日志手动清理即可
```

### 生产环境

```bash
# 1. 配置 Cron 定时任务
crontab -e

# 2. 添加日志轮转任务（每天午夜）
0 0 * * * /path/to/aniforce/scripts/rotate_logs.sh --log-dir /var/log/aniforce --compress --retention 30 >> /var/log/aniforce_cron.log 2>&1

# 3. 启动服务
./deploy_server.sh --log-dir /var/log/aniforce

# 4. 验证配置
# 等待一天后检查日志目录
ls -lh /var/log/aniforce/
```

## 最佳实践

### 1. 日志目录规划

```bash
# 开发环境：使用项目目录
./run_server.sh --log-dir ./logs

# 生产环境：使用系统日志目录
./deploy_server.sh --log-dir /var/log/aniforce
```

### 2. 保留策略

```bash
# 开发环境：保留 7 天
./scripts/rotate_logs.sh --retention 7

# 生产环境：保留 30 天
./scripts/rotate_logs.sh --retention 30

# 审计需求：保留 90 天
./scripts/rotate_logs.sh --retention 90
```

### 3. 压缩策略

```bash
# 节省磁盘空间：启用压缩
./scripts/rotate_logs.sh --compress

# 快速访问：不压缩
./scripts/rotate_logs.sh
```

### 4. 监控告警

```bash
# 监控日志目录大小
du -sh /var/log/aniforce

# 设置告警（当目录超过 10GB）
if [ $(du -s /var/log/aniforce | awk '{print $1}') -gt 10485760 ]; then
  echo "日志目录超过 10GB，请检查" | mail -s "ANIFORCE 日志告警" admin@example.com
fi
```

## 故障排查

### 问题 1: 后端日志未按日期轮转

**症状**: 跨天后仍写入旧日期的日志文件

**检查**:
```bash
# 1. 确认日志文件名包含 {time:YYYYMMDD}
grep "BACKEND_LOG" run_server.sh
# 应该看到: backend_logs_{time:YYYYMMDD}.log

# 2. 确认 loguru 配置正确
grep "rotation" backend/app/config/logging.py
# 应该看到: rotation="00:00"

# 3. 查看后端日志中的错误
tail -100 logs/backend_logs_*.log | grep -i error
```

**解决**:
```bash
# 重启后端服务
./undeploy_server.sh --only backend
./deploy_server.sh --only backend
```

### 问题 2: Cron 任务未执行

**症状**: 旧日志未被清理或压缩

**检查**:
```bash
# 1. 确认 cron 服务运行
# macOS
sudo launchctl list | grep cron

# Linux
systemctl status cron

# 2. 查看 crontab 配置
crontab -l

# 3. 检查脚本权限
ls -l scripts/rotate_logs.sh
# 应该有执行权限: -rwxr-xr-x

# 4. 手动运行测试
./scripts/rotate_logs.sh --log-dir ./logs --compress
```

**解决**:
```bash
# 添加执行权限
chmod +x scripts/rotate_logs.sh

# 重新配置 cron
crontab -e

# macOS: 授予 cron 完全磁盘访问权限
# 系统偏好设置 > 安全性与隐私 > 完全磁盘访问权限
```

### 问题 3: 日志文件权限错误

**症状**: 无法写入日志文件

**检查**:
```bash
# 检查日志目录权限
ls -ld logs/

# 检查日志文件权限
ls -l logs/*.log
```

**解决**:
```bash
# 修复目录权限
chmod 755 logs/

# 修复文件权限
chmod 644 logs/*.log
```

## 总结

### 核心要点

1. **后端日志**: 使用 loguru 自动轮转，完全自动化 ✅
2. **前端/Nginx 日志**: 使用 Cron + 轮转脚本，一次配置长期有效 ⚠️
3. **生产环境**: 必须配置 Cron 定时任务
4. **开发环境**: 后端自动轮转，其他手动清理即可

### 快速开始

```bash
# 1. 启动服务（后端日志自动轮转）
./deploy_server.sh

# 2. 配置 Cron（处理前端和 Nginx 日志）
crontab -e
# 添加: 0 0 * * * /path/to/aniforce/scripts/rotate_logs.sh --log-dir /path/to/logs --compress

# 3. 验证
# 等待一天后检查日志目录
ls -lh logs/
```

### 相关文档

- `LOGGING.md` - 完整的日志管理文档
- `scripts/rotate_logs.sh` - 日志轮转脚本
- `scripts/crontab.example` - Cron 配置示例
- `backend/app/config/logging.py` - 后端日志配置

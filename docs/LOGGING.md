# ANIFORCE 日志管理说明

本文档介绍 ANIFORCE 项目的统一日志管理系统。

## 日志架构

### 日志目录结构

```
./logs/
├── backend_logs_20260603.log      # 后端应用日志（按日期自动轮转）
├── uvicorn_logs_20260603.log      # Uvicorn 服务器日志（按日期）
├── frontend_logs_20260603.log     # 前端日志（按日期）
├── nginx_access_20260603.log      # Nginx 访问日志（按日期）
└── nginx_error_20260603.log       # Nginx 错误日志（按日期）
```

### 日志命名规范

- **后端应用日志**: `backend_logs_YYYYMMDD.log` （业务逻辑日志，自动轮转）
- **Uvicorn 日志**: `uvicorn_logs_YYYYMMDD.log` （HTTP 服务器日志）
- **前端日志**: `frontend_logs_YYYYMMDD.log`
- **Nginx 访问日志**: `nginx_access_YYYYMMDD.log`
- **Nginx 错误日志**: `nginx_error_YYYYMMDD.log`

日志文件按日期自动分离，每天生成新的日志文件。

## 配置说明

### 默认配置

- **日志目录**: `./logs/` （项目根目录下）
- **日志格式**: 按日期命名，自动轮转
- **日志级别**: 
  - 后端: INFO（可在后端配置中调整）
  - 前端: 所有 Vite 输出
  - Nginx: 标准访问日志和错误日志

### 自定义日志目录

两个启动脚本都支持通过 `--log-dir` 参数自定义日志目录：

#### run_server.sh

```bash
# 使用默认日志目录 ./logs/
./run_server.sh

# 自定义日志目录（相对路径）
./run_server.sh --log-dir ./my-logs

# 自定义日志目录（绝对路径）
./run_server.sh --log-dir /var/log/aniforce
```

#### deploy_server.sh

```bash
# 使用默认日志目录 ./logs/
./deploy_server.sh

# 自定义日志目录
./deploy_server.sh --log-dir ./production-logs

# 结合其他参数
./deploy_server.sh --mode cloud --log-dir /var/log/aniforce
```

## 日志查看

### 实时查看日志

```bash
# 查看后端应用日志（业务逻辑）
tail -f logs/backend_logs_$(date +%Y%m%d).log

# 查看 Uvicorn 日志（HTTP 请求）
tail -f logs/uvicorn_logs_$(date +%Y%m%d).log

# 查看前端日志
tail -f logs/frontend_logs_$(date +%Y%m%d).log

# 查看 Nginx 访问日志
tail -f logs/nginx_access_$(date +%Y%m%d).log

# 查看 Nginx 错误日志
tail -f logs/nginx_error_$(date +%Y%m%d).log

# 同时查看所有日志
tail -f logs/*_$(date +%Y%m%d).log
```

### 查看历史日志

```bash
# 查看指定日期的后端日志
cat logs/backend_logs_20260603.log

# 搜索错误信息
grep -i error logs/backend_logs_*.log

# 搜索特定时间段的日志
grep "2026-06-03 17:" logs/backend_logs_20260603.log
```

### 日志分析

```bash
# 统计错误数量
grep -c ERROR logs/backend_logs_$(date +%Y%m%d).log

# 查看最近的错误
grep ERROR logs/backend_logs_$(date +%Y%m%d).log | tail -20

# 分析 Nginx 访问日志（按状态码统计）
awk '{print $9}' logs/nginx_access_$(date +%Y%m%d).log | sort | uniq -c | sort -rn

# 查看访问最多的 IP
awk '{print $1}' logs/nginx_access_$(date +%Y%m%d).log | sort | uniq -c | sort -rn | head -10
```

## 日志轮转

### 自动轮转机制

ANIFORCE 使用多层日志轮转机制，确保跨天运行时日志正确分离：

#### 后端日志（自动按日期轮转）✅

后端日志分为两个文件：

**1. 应用日志（backend_logs）- 自动轮转** ✅

使用 **loguru** 库的自动轮转功能：

- **文件名模板**: `backend_logs_{time:YYYYMMDD}.log`
- **内容**: 业务逻辑日志、错误信息、调试信息
- **轮转时间**: 每天午夜 00:00 自动轮转
- **跨天处理**: 
  - 6月3日 23:50 启动 → 写入 `backend_logs_20260603.log`
  - 6月4日 00:00 自动切换 → 写入 `backend_logs_20260604.log` ✅
- **保留策略**: 保留 30 天
- **压缩策略**: 自动压缩旧日志为 .zip 格式

**2. Uvicorn 日志（uvicorn_logs）- 启动时确定** ⚠️

- **文件名**: `uvicorn_logs_YYYYMMDD.log`（启动时确定）
- **内容**: HTTP 服务器日志、请求访问日志
- **跨天处理**: 与前端相同，需要 cron 或重启

#### 前端日志（启动时确定）⚠️

前端使用 Vite，不支持自动轮转：

- **文件名**: `frontend_logs_YYYYMMDD.log`（启动时确定）
- **跨天处理**: 
  - 6月3日 23:50 启动 → 写入 `frontend_logs_20260603.log`
  - 6月4日 00:00 后 → 仍写入 `frontend_logs_20260603.log` ⚠️
- **解决方案**: 使用 cron 定时任务或手动重启服务

#### Nginx 日志（启动时确定）⚠️

Nginx 日志路径在启动时确定：

- **文件名**: `nginx_access_YYYYMMDD.log`, `nginx_error_YYYYMMDD.log`
- **跨天处理**: 与前端相同，需要重启或使用日志轮转工具
- **解决方案**: 使用系统 logrotate 或自定义轮转脚本

### 使用日志轮转脚本（推荐）

ANIFORCE 提供了专用的日志轮转脚本 `scripts/rotate_logs.sh`：

```bash
# 基本用法（清理 30 天前的日志）
./scripts/rotate_logs.sh

# 压缩旧日志并保留 7 天
./scripts/rotate_logs.sh --compress --retention 7

# 指定日志目录
./scripts/rotate_logs.sh --log-dir /var/log/aniforce --compress
```

**功能特性**：
- 自动清理过期日志
- 可选压缩旧日志（gzip）
- 可配置保留天数
- 提供详细的统计信息

### 配置 Cron 定时任务

为了处理前端和 Nginx 日志的跨天问题，建议配置 cron 定时任务：

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天午夜运行）
0 0 * * * /path/to/aniforce/scripts/rotate_logs.sh --log-dir /path/to/aniforce/logs --compress
```

详细的 cron 配置示例见 `scripts/crontab.example`。

**注意**: 配置 cron 后，即使服务跨天运行，日志也会被正确管理。

### 手动清理

```bash
# 删除 7 天前的日志
find logs/ -name "*.log" -mtime +7 -delete

# 删除 30 天前的日志
find logs/ -name "*.log" -mtime +30 -delete

# 压缩旧日志
find logs/ -name "*.log" -mtime +7 -exec gzip {} \;
```

### 使用 logrotate（推荐生产环境）

创建 `/etc/logrotate.d/aniforce` 配置文件：

```
/path/to/aniforce/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
    create 0644 user group
}
```

## 日志级别配置

### 后端日志级别

后端日志级别在 `backend/app/config/logging.py` 中配置：

```python
# 开发环境
LOG_LEVEL = "DEBUG"

# 生产环境
LOG_LEVEL = "INFO"

# 仅错误
LOG_LEVEL = "ERROR"
```

### 前端日志

前端日志包含所有 Vite 开发服务器的输出，包括：
- 模块热更新（HMR）信息
- 编译警告和错误
- 网络请求日志
- 构建信息

## 故障排查

### 后端启动失败

```bash
# 查看后端日志最后 50 行
tail -50 logs/backend_logs_$(date +%Y%m%d).log

# 搜索错误信息
grep -i "error\|exception\|traceback" logs/backend_logs_$(date +%Y%m%d).log
```

### 前端启动失败

```bash
# 查看前端日志
tail -100 logs/frontend_logs_$(date +%Y%m%d).log

# 搜索编译错误
grep -i "error\|failed" logs/frontend_logs_$(date +%Y%m%d).log
```

### Nginx 问题

```bash
# 查看 Nginx 错误日志
tail -50 logs/nginx_error_$(date +%Y%m%d).log

# 查看 502/503 错误
grep "502\|503" logs/nginx_access_$(date +%Y%m%d).log

# 查看上游服务器错误
grep "upstream" logs/nginx_error_$(date +%Y%m%d).log
```

### 日志文件未生成

检查以下几点：

1. **日志目录权限**
   ```bash
   ls -ld logs/
   # 确保有写权限
   chmod 755 logs/
   ```

2. **磁盘空间**
   ```bash
   df -h
   # 确保有足够空间
   ```

3. **进程是否正常运行**
   ```bash
   ps aux | grep uvicorn
   ps aux | grep vite
   ps aux | grep nginx
   ```

## 日志监控

### 使用 multitail 同时监控多个日志

```bash
# 安装 multitail
brew install multitail  # macOS
apt-get install multitail  # Ubuntu

# 同时监控所有日志
multitail logs/backend_logs_$(date +%Y%m%d).log \
          logs/frontend_logs_$(date +%Y%m%d).log \
          logs/nginx_access_$(date +%Y%m%d).log \
          logs/nginx_error_$(date +%Y%m%d).log
```

### 使用 lnav 日志分析工具

```bash
# 安装 lnav
brew install lnav  # macOS
apt-get install lnav  # Ubuntu

# 分析所有日志
lnav logs/
```

## 生产环境建议

### 1. 日志目录配置

```bash
# 使用专门的日志目录
./deploy_server.sh --log-dir /var/log/aniforce
```

### 2. 日志轮转

配置 logrotate 自动清理旧日志，避免磁盘空间耗尽。

### 3. 日志监控

- 使用 ELK Stack（Elasticsearch + Logstash + Kibana）
- 使用 Grafana Loki
- 使用云服务日志管理（如 AWS CloudWatch）

### 4. 告警配置

```bash
# 监控错误日志并发送告警
watch -n 60 'grep ERROR logs/backend_logs_$(date +%Y%m%d).log | tail -10'
```

### 5. 日志备份

```bash
# 定期备份日志到远程服务器
rsync -avz logs/ backup-server:/backup/aniforce/logs/
```

## 常见问题

**Q: 日志文件太大怎么办？**

A: 
1. 配置日志轮转（logrotate）
2. 调整日志级别（减少 DEBUG 日志）
3. 定期清理旧日志

**Q: 如何搜索跨多天的日志？**

A:
```bash
grep "关键词" logs/backend_logs_*.log
```

**Q: 日志中文乱码怎么办？**

A: 确保终端和日志文件都使用 UTF-8 编码：
```bash
export LANG=zh_CN.UTF-8
```

**Q: 如何导出特定时间段的日志？**

A:
```bash
# 导出今天 17:00-18:00 的日志
grep "2026-06-03 17:" logs/backend_logs_20260603.log > export.log
```

## 相关文件

- `run_server.sh` - 开发环境启动脚本（支持 --log-dir）
- `deploy_server.sh` - 生产环境部署脚本（支持 --log-dir）
- `backend/app/config/logging.py` - 后端日志配置
- `.gitignore` - 日志目录已被忽略，不会提交到 Git

## 支持

如有日志相关问题，请查看：
- 项目 README.md
- DEPLOYMENT.md（部署文档）
- 或联系技术支持

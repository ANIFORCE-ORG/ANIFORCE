# 后端日志文件名说明

## 问题：为什么看到 `backend_logs_{time:YYYYMMDD}.log`？

### 原因分析

`{time:YYYYMMDD}` 是 **loguru** 库的时间占位符，不是 shell 变量。

#### Shell vs Python

```bash
# Shell 脚本中（run_server.sh）
BACKEND_APP_LOG="$LOG_DIR/backend_logs_{time:YYYYMMDD}.log"
# 这只是一个字符串，{time:YYYYMMDD} 不会被 shell 替换

# Python 代码中（loguru）
logger.add("logs/backend_logs_{time:YYYYMMDD}.log")
# loguru 会在运行时将 {time:YYYYMMDD} 替换为实际日期
# 例如：backend_logs_20260603.log
```

### 工作原理

1. **Shell 脚本设置环境变量**
   ```bash
   # run_server.sh
   LOG_FILE="$LOG_DIR/backend_logs_{time:YYYYMMDD}.log"
   ```

2. **传递给 Python 应用**
   ```bash
   LOG_FILE="$BACKEND_APP_LOG" python -m uvicorn app.main:app
   ```

3. **Python 读取环境变量**
   ```python
   # backend/app/config/settings.py
   LOG_FILE: str = ""  # 从环境变量读取
   ```

4. **loguru 处理占位符**
   ```python
   # backend/app/config/logging.py
   logger.add(
       log_file,  # "logs/backend_logs_{time:YYYYMMDD}.log"
       rotation="00:00"
   )
   # loguru 自动将 {time:YYYYMMDD} 替换为当前日期
   # 创建文件：backend_logs_20260603.log
   ```

5. **跨天自动轮转**
   ```
   6月3日 23:50 → backend_logs_20260603.log
   6月4日 00:00 → backend_logs_20260604.log（自动切换）
   ```

## 实际文件名

虽然在脚本中看到 `{time:YYYYMMDD}`，但实际创建的文件名是：

```
logs/
├── backend_logs_20260603.log      ✅ 实际文件
├── backend_logs_20260604.log      ✅ 实际文件
└── backend_logs_{time:YYYYMMDD}.log  ❌ 不会创建此文件
```

## 验证方法

### 1. 启动服务

```bash
./run_server.sh --only backend
```

### 2. 查看日志目录

```bash
ls -lh logs/
```

**预期输出**：
```
-rw-r--r--  1 user  staff   1.2K  6  3 17:30 backend_logs_20260603.log
-rw-r--r--  1 user  staff   856B  6  3 17:30 uvicorn_logs_20260603.log
```

**不会看到**：
```
backend_logs_{time:YYYYMMDD}.log  ❌
```

### 3. 查看日志内容

```bash
tail -f logs/backend_logs_$(date +%Y%m%d).log
```

应该能看到后端应用的日志输出。

## 两个后端日志文件

### backend_logs_YYYYMMDD.log（应用日志）

- **来源**: Python 应用代码（通过 loguru）
- **内容**: 
  - 业务逻辑日志
  - 错误和异常信息
  - 调试信息
  - 自定义日志
- **轮转**: 每天午夜自动轮转 ✅
- **示例**:
  ```
  2026-06-03 17:30:15.123 | INFO     | app.main:health_check:52 | Health check called
  2026-06-03 17:30:20.456 | ERROR    | app.api.v1.chat:create_chat:45 | Failed to create chat
  ```

### uvicorn_logs_YYYYMMDD.log（服务器日志）

- **来源**: Uvicorn HTTP 服务器（通过 shell 重定向）
- **内容**:
  - HTTP 请求日志
  - 服务器启动信息
  - 连接信息
  - 性能指标
- **轮转**: 启动时确定，需要 cron 或重启 ⚠️
- **示例**:
  ```
  INFO:     Started server process [12345]
  INFO:     Waiting for application startup.
  INFO:     Application startup complete.
  INFO:     127.0.0.1:54321 - "GET /health HTTP/1.1" 200 OK
  ```

## 为什么分开两个文件？

### 优势

1. **职责分离**
   - 应用日志：业务逻辑和错误
   - 服务器日志：HTTP 请求和性能

2. **不同的轮转策略**
   - 应用日志：loguru 自动轮转（跨天无缝切换）
   - 服务器日志：shell 重定向（简单直接）

3. **便于分析**
   - 查看业务问题 → backend_logs
   - 查看请求问题 → uvicorn_logs

4. **灵活配置**
   - 应用日志可以配置级别、格式、压缩
   - 服务器日志保持原始格式

### 示例场景

**场景 1：调试业务逻辑错误**
```bash
# 只看应用日志
grep ERROR logs/backend_logs_$(date +%Y%m%d).log
```

**场景 2：分析 HTTP 请求**
```bash
# 只看服务器日志
grep "GET /api" logs/uvicorn_logs_$(date +%Y%m%d).log
```

**场景 3：查看完整请求链路**
```bash
# 同时查看两个日志
tail -f logs/backend_logs_$(date +%Y%m%d).log logs/uvicorn_logs_$(date +%Y%m%d).log
```

## 常见问题

### Q1: 为什么不直接用日期变量？

**不推荐**：
```bash
# 这样做会在启动时确定日期，跨天后不会切换
BACKEND_LOG="$LOG_DIR/backend_logs_$(date +%Y%m%d).log"
```

**推荐**：
```bash
# 使用 loguru 占位符，自动按日期轮转
BACKEND_LOG="$LOG_DIR/backend_logs_{time:YYYYMMDD}.log"
```

### Q2: 如果看到文件名就是 `{time:YYYYMMDD}`？

这说明 loguru 没有正确处理占位符，可能的原因：

1. **LOG_FILE 环境变量未传递**
   ```bash
   # 检查环境变量
   echo $LOG_FILE
   ```

2. **loguru 配置错误**
   ```python
   # 检查 backend/app/config/logging.py
   # 确保有 if "{time" in log_file: 的判断
   ```

3. **Python 版本或 loguru 版本问题**
   ```bash
   pip show loguru
   ```

### Q3: 如何禁用自动轮转？

如果不需要自动轮转，可以使用固定文件名：

```python
# backend/app/config/logging.py
logger.add(
    "logs/backend.log",  # 固定文件名
    rotation="100 MB"    # 按大小轮转
)
```

## 总结

- ✅ `{time:YYYYMMDD}` 是 loguru 的占位符，不是错误
- ✅ 实际文件名会是 `backend_logs_20260603.log`
- ✅ 支持跨天自动轮转
- ✅ 应用日志和服务器日志分离，便于管理
- ✅ 无需手动干预，完全自动化

## 相关文档

- `docs/LOGGING.md` - 完整日志管理文档
- `docs/LOG_ROTATION_SOLUTION.md` - 跨天日志轮转解决方案
- `backend/app/config/logging.py` - 日志配置代码

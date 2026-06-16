# ANIFORCE Agent 服务部署指南

## 架构概述

```
前端 (CopilotKit) 
    ↓ HTTPS + SSE
Nginx (统一入口)
    ↓ JWT Auth
Agent 服务 (FastAPI) ←→ 后端服务 (FastAPI)
    ↓ SQLite              ↓ PostgreSQL
独立数据存储              业务数据
```

## 环境要求

- **Python**: 3.11
- **uv**: 最新版本（包管理工具）
- **系统依赖**: 无特殊要求（SQLite 为系统内置）

## 快速启动（开发环境）

### 1. 安装依赖

```bash
cd aniforce-agent

# 创建虚拟环境
UV_CACHE_DIR=./uv_cache uv venv --python 3.11

# 安装依赖
UV_CACHE_DIR=./uv_cache uv pip install --python .venv/bin/python -r requirements.txt

# 安装 Claude Agent SDK（从本地路径）
UV_CACHE_DIR=./uv_cache uv pip install --python .venv/bin/python -e ../resources/claude-agent-sdk-python
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# 服务配置
DEBUG=true
PORT=8020

# 数据库路径（SQLite）
TASK_DB_PATH=runtime/agent/tasks.db
SESSION_DB_PATH=runtime/agent/sessions.db

# JWT 配置（与后端服务共享）
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# 后端服务地址（用于 HTTP MCP 调用）
BACKEND_URL=http://localhost:8010
INTERNAL_TOKEN=your-internal-token-here

# Claude API
ANTHROPIC_API_KEY=sk-ant-xxxxx

# CORS 配置
CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:5173

# 运行时目录
RUNTIME_DIR=runtime/sessions
SKILL_SOURCE_DIR=app/skills
```

### 3. 初始化数据库

```bash
# 数据库会在首次启动时自动创建
mkdir -p runtime/agent runtime/sessions
```

### 4. 启动服务

```bash
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8020 \
    --reload
```

服务启动后访问：
- 健康检查: http://localhost:8020/health
- API 文档: http://localhost:8020/docs
- CopilotKit Info: http://localhost:8020/api/agent/copilotkit/info

## 运行测试

```bash
# 运行所有测试
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python pytest tests/ -v

# 运行特定测试
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python pytest tests/test_e2e.py -v

# 生成覆盖率报告
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python pytest tests/ --cov=app --cov-report=html
```

## API 端点

### CopilotKit 标准接口（前端调用）

#### 1. 获取 Agent 信息

```bash
GET /api/agent/copilotkit/info
```

响应示例：
```json
{
  "agents": [
    {
      "name": "default",
      "description": "ANIFORCE AI Agent - 智能广告投放助手",
      "capabilities": [
        "project_management",
        "campaign_management",
        "material_management",
        "platform_authorization"
      ]
    }
  ]
}
```

#### 2. 运行 Agent（流式对话）

```bash
POST /api/agent/copilotkit/agent/default/run
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "创建一个新项目"}
  ],
  "threadId": "session_abc123"
}
```

响应：SSE 流式事件
```
event: TEXT_MESSAGE_START
data: {"id":"msg_001","runId":"task_123"}

event: TEXT_MESSAGE_CONTENT
data: {"id":"msg_001","content":"正在创建项目..."}

event: TOOL_CALL_START
data: {"id":"tool_001","name":"create_project"}

event: TOOL_CALL_RESULT
data: {"id":"tool_001","result":"项目创建成功"}

event: TEXT_MESSAGE_END
data: {"id":"msg_001"}

event: RUN_FINISHED
data: {"runId":"task_123"}
```

### 任务管理接口（内部调用）

#### 1. 创建任务

```bash
POST /api/agent/tasks
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json

{
  "task_type": "conversation",
  "title": "创建新项目",
  "input_data": {"prompt": "创建一个新项目"},
  "session_id": "session_abc123"
}
```

#### 2. 查询任务列表

```bash
GET /api/agent/tasks?task_type=conversation&limit=10
Authorization: Bearer <JWT_TOKEN>
```

#### 3. 获取任务详情

```bash
GET /api/agent/tasks/{task_id}
Authorization: Bearer <JWT_TOKEN>
```

#### 4. 获取事件流（断点续传）

```bash
GET /api/agent/tasks/{task_id}/events?after_sequence=5
Authorization: Bearer <JWT_TOKEN>
```

#### 5. 取消任务

```bash
DELETE /api/agent/tasks/{task_id}
Authorization: Bearer <JWT_TOKEN>
```

## 生产部署

### Docker 部署

#### 1. 构建镜像

创建 `Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装 uv
RUN pip install uv

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN uv venv --python 3.11 && \
    uv pip install --python .venv/bin/python -r requirements.txt

# 复制 Claude SDK（本地路径）
COPY ../resources/claude-agent-sdk-python /tmp/claude-agent-sdk-python
RUN uv pip install --python .venv/bin/python -e /tmp/claude-agent-sdk-python

# 复制应用代码
COPY app app/
COPY runtime runtime/

# 创建运行时目录
RUN mkdir -p runtime/agent runtime/sessions

# 暴露端口
EXPOSE 8020

# 启动命令
CMD [".venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8020"]
```

构建镜像：
```bash
docker build -t aniforce-agent:latest .
```

#### 2. Docker Compose 部署

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  agent:
    image: aniforce-agent:latest
    container_name: aniforce-agent
    environment:
      - DEBUG=false
      - PORT=8020
      - TASK_DB_PATH=/app/runtime/agent/tasks.db
      - SESSION_DB_PATH=/app/runtime/agent/sessions.db
      - JWT_SECRET=${JWT_SECRET}
      - BACKEND_URL=http://backend:8010
      - INTERNAL_TOKEN=${INTERNAL_TOKEN}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - CORS_ALLOW_ORIGINS=${CORS_ALLOW_ORIGINS}
    ports:
      - "8020:8020"
    volumes:
      - agent_data:/app/runtime
    restart: unless-stopped
    networks:
      - aniforce-network

volumes:
  agent_data:

networks:
  aniforce-network:
    external: true
```

启动服务：
```bash
docker-compose up -d
```

### 性能优化

#### 1. Gunicorn + Uvicorn Workers

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8020 \
  --timeout 120 \
  --keep-alive 5
```

#### 2. Nginx 配置

```nginx
upstream agent_backend {
    server 127.0.0.1:8020;
}

server {
    listen 443 ssl http2;
    server_name agent.aniforce.com;

    # SSL 配置
    ssl_certificate /etc/ssl/certs/aniforce.crt;
    ssl_certificate_key /etc/ssl/private/aniforce.key;

    # Agent API
    location /api/agent/ {
        proxy_pass http://agent_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # SSE 支持
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

## 监控与日志

### 日志配置

日志输出到 `logs/` 目录：

```python
# app/config/logging.py
from loguru import logger
import sys

logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
)
logger.add(
    "logs/agent_{time:YYYYMMDD}.log",
    rotation="00:00",
    retention="30 days",
    level="INFO"
)
```

### 健康检查

```bash
# 基础健康检查
curl http://localhost:8020/health

# 完整检查（包含数据库连接）
curl http://localhost:8020/api/agent/copilotkit/info
```

## 故障排查

### 1. 数据库初始化失败

**症状**: 启动时报错 `no such table: tasks`

**解决**: 
```bash
# 删除旧数据库
rm runtime/agent/*.db*

# 重启服务，自动创建新数据库
UV_CACHE_DIR=./uv_cache uv run --python .venv/bin/python -m uvicorn app.main:app --reload
```

### 2. JWT 认证失败

**症状**: API 返回 401 或 403

**检查**:
- JWT_SECRET 是否与后端服务一致
- Token 是否过期
- Authorization header 格式是否正确（`Bearer <token>`）

### 3. Claude SDK 连接失败

**症状**: 任务执行时报错 `Connection error`

**检查**:
- ANTHROPIC_API_KEY 是否配置正确
- 网络是否可访问 api.anthropic.com
- 查看日志中的详细错误信息

### 4. HTTP MCP 调用失败

**症状**: Agent 无法调用后端工具

**检查**:
- BACKEND_URL 是否正确
- INTERNAL_TOKEN 是否与后端服务一致
- 后端服务是否正常运行
- 查看后端服务日志

## 数据备份

### 备份 SQLite 数据库

```bash
# 备份任务数据库
sqlite3 runtime/agent/tasks.db ".backup runtime/agent/tasks_backup.db"

# 备份会话数据库
sqlite3 runtime/agent/sessions.db ".backup runtime/agent/sessions_backup.db"
```

### 定时备份脚本

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

sqlite3 runtime/agent/tasks.db ".backup $BACKUP_DIR/tasks.db"
sqlite3 runtime/agent/sessions.db ".backup $BACKUP_DIR/sessions.db"

# 保留最近 30 天的备份
find backups/ -type d -mtime +30 -exec rm -rf {} \;
```

## 安全建议

1. **生产环境必须配置**:
   - 强随机 JWT_SECRET（32+ 字符）
   - 强随机 INTERNAL_TOKEN（32+ 字符）
   - 有效的 ANTHROPIC_API_KEY

2. **网络隔离**:
   - Agent 服务与后端服务通过内网通信
   - 不直接暴露 Agent 服务到公网
   - 通过 Nginx 统一入口

3. **日志脱敏**:
   - 不记录完整 API Key
   - 不记录用户敏感数据
   - 定期清理过期日志

4. **数据库权限**:
   - SQLite 文件权限设置为 600
   - 定期备份数据库文件

## 性能指标

### 预期性能（单实例）

- **并发请求**: 50-100 QPS
- **响应延迟**: 
  - API 调用: < 100ms
  - Agent 执行: 2-10s（取决于模型和工具调用）
- **内存占用**: 200-500MB（无负载）/ 1-2GB（高负载）
- **磁盘占用**: 
  - SQLite 数据库: 10MB / 1000 任务
  - Session 数据: 50MB / 1000 会话

### 扩展建议

- 单实例可支持 100-200 并发用户
- 需要更高并发时，使用负载均衡 + 多实例部署
- Session 数据共享可通过挂载共享存储（NFS/Ceph）实现

## 后续优化方向

1. **性能优化**:
   - [ ] Session 数据库连接池优化
   - [ ] Claude SDK 客户端实例复用
   - [ ] 批量事件写入优化

2. **功能扩展**:
   - [ ] Sub-Agent 编排（专家系统）
   - [ ] 多模型支持（Opus/Sonnet/Haiku）
   - [ ] 工具权限管理（租户级配置）

3. **运维增强**:
   - [ ] Prometheus 指标暴露
   - [ ] 分布式链路追踪
   - [ ] 实时任务监控面板

## 相关文档

- [迁移方案](../docs/migration-plan.md)
- [架构设计](../docs/architecture.md)
- [API 文档](http://localhost:8020/docs)
- [Claude SDK 文档](../resources/claude-agent-sdk-python/README.md)

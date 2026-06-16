# ANIFORCE Agent Service

基于 Claude Agent SDK 的智能 Agent 服务，独立部署，为 ANIFORCE 提供 AI 能力。

## 功能特性

- ✅ **独立服务**：与后端服务解耦，独立部署和扩展
- ✅ **Claude SDK**：基于 Anthropic Claude Agent SDK (Python)
- ✅ **SQLite 存储**：轻量级本地数据库，零配置
- ✅ **JWT 认证**：与后端服务共享认证体系
- ✅ **HTTP MCP**：调用后端业务能力
- ✅ **Skill 系统**：动态注入领域知识
- ✅ **CopilotKit**：支持前端对话组件

## 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Claude Agent SDK（本地）
pip install -e ../resources/claude-agent-sdk-python
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置必要的环境变量
```

### 3. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8020 --reload
```

## 目录结构

```
aniforce-agent/
├── app/                    # 应用代码
│   ├── config/            # 配置管理
│   ├── core/              # 核心功能（认证、上下文）
│   ├── agent/             # Agent Runtime
│   ├── mcp/               # MCP 工具
│   ├── models/            # 数据模型
│   ├── repositories/      # 数据访问层
│   ├── services/          # 业务逻辑
│   ├── api/               # API 路由
│   ├── skills/            # Skill 文件
│   └── middleware/        # 中间件
├── runtime/               # 运行时数据
│   ├── sessions/          # 会话工作目录
│   └── logs/              # 日志
└── tests/                 # 测试
```

## 开发

### 运行测试

```bash
pytest tests/ -v
```

### 代码检查

```bash
# Linting
ruff check app/

# Type checking
mypy app/
```

## 部署

### Docker

```bash
docker build -t aniforce-agent .
docker run -p 8020:8020 --env-file .env aniforce-agent
```

### Docker Compose

```bash
docker-compose up -d
```

## API 文档

启动服务后访问：

- Swagger UI: http://localhost:8020/docs
- ReDoc: http://localhost:8020/redoc

## License

Proprietary

# ANIMAGUS Demo — Game Marketing Pro

> AI 驱动的游戏全球营销一站式平台 Demo

## 技术架构

采用 **三层解耦** 设计，前端 DAL 层与后端 Repository 层通过接口抽象实现 Demo/生产模式零侵入切换。

```
┌─────────────────────────────────────────────────────┐
│                    前端（Vue3）                       │
│  Pages → Composables → DAL（MockClient / HttpClient）│
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────────────┐
│                  后端（FastAPI）                      │
│  API Routes → Service（纯业务） → Repository Protocol │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│                    数据层                             │
│  MockRepository（Demo） / PgRepo + MongoRepo（生产）  │
└─────────────────────────────────────────────────────┘
```

### 核心技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| **前端框架** | Vue 3.4 + TypeScript | 主应用壳工程 |
| **构建工具** | Vite 5 + pnpm monorepo | 快速开发与模块化 |
| **样式方案** | TailwindCSS 3.4 | 原子化 CSS |
| **状态管理** | Pinia | Vue3 官方推荐 |
| **后端框架** | FastAPI + Uvicorn | 高性能异步 Python |
| **数据验证** | Pydantic v2 | 请求/响应模型 |
| **认证方案** | JWT（python-jose） | 无状态认证 |
| **依赖注入** | FastAPI Depends | Repository → Service 链式注入 |

### Demo 模式

通过环境变量控制，**Service 层代码在 Demo 和生产模式下完全相同**：

- **前端** `VITE_DEMO_MODE=true` → DAL 工厂返回 `MockClient`（纯前端离线演示）
- **后端** `DEMO_MODE=true` → Repository 工厂返回 `MockRepository`（内存 Mock 数据）

---

## 代码目录结构

```
ANIMAGUS-DEMO/
├── README.md
├── doc/                              # 项目文档
│   └── 06-技术框架规划文档-详细版.md
├── html/                             # HTML 原型稿
│
├── frontend/                         # 前端 monorepo
│   ├── package.json                  # 根 package（scripts 入口）
│   ├── pnpm-workspace.yaml           # pnpm workspace 配置
│   └── packages/
│       ├── main-app/                 # Vue3 主应用（端口 3000）
│       │   ├── index.html
│       │   ├── vite.config.ts
│       │   ├── tailwind.config.js
│       │   ├── tsconfig.json
│       │   ├── .env.development      # VITE_DEMO_MODE=true
│       │   └── src/
│       │       ├── main.ts           # 应用入口 + DAL 初始化
│       │       ├── App.vue           # 根组件（Header + RouterView + Footer）
│       │       ├── router/index.ts   # 路由配置
│       │       ├── styles/global.css # TailwindCSS 全局样式
│       │       ├── pages/
│       │       │   ├── Home.vue      # 首页（AI 分析交互）
│       │       │   └── Login.vue     # 登录页
│       │       └── components/
│       │           └── layout/
│       │               ├── AppHeader.vue
│       │               └── AppFooter.vue
│       └── shared/                   # 跨应用共享包
│           ├── index.ts              # 统一导出
│           ├── types/index.ts        # 类型定义
│           ├── utils/constants.ts    # 常量
│           └── dal/                  # 数据访问层（三层解耦核心）
│               ├── interfaces.ts     # 接口定义（IChatClient 等）
│               ├── mock-client.ts    # Demo 模式 Mock 实现
│               ├── http-client.ts    # 生产模式 HTTP 实现
│               └── factory.ts        # 工厂（根据环境变量切换）
│
└── backend/                          # 后端 FastAPI 服务
    ├── requirements.txt              # Python 依赖
    ├── .env                          # 环境变量（DEMO_MODE=true）
    └── app/
        ├── __init__.py
        ├── main.py                   # FastAPI 入口 + CORS + 异常处理
        ├── config/
        │   └── settings.py           # Pydantic Settings 配置
        ├── schemas/                  # Pydantic 请求/响应模型
        │   ├── base.py               # ResponseBase / ErrorResponse
        │   ├── auth.py               # 认证相关 Schema
        │   └── chat.py               # 对话相关 Schema
        ├── api/
        │   ├── deps.py               # 公共依赖（认证中间件）
        │   └── v1/
        │       ├── router.py         # 路由聚合
        │       ├── auth.py           # POST /auth/login, /auth/register
        │       └── chat.py           # POST /chat/analyze, /{id}/message
        ├── services/                 # 纯业务逻辑（零 if/else）
        │   ├── chat_service.py
        │   ├── material_service.py
        │   ├── campaign_service.py
        │   └── monitor_service.py
        └── repositories/             # 数据访问层
            ├── protocols.py          # Protocol 抽象接口
            ├── factory.py            # 工厂（DEMO_MODE 切换）
            └── mock/                 # Mock 实现（内存数据）
                ├── mock_chat_repo.py
                ├── mock_material_repo.py
                ├── mock_campaign_repo.py
                └── mock_metric_repo.py
```

---

## 快速启动

### 环境要求

- **Node.js** >= 20.0.0
- **pnpm** >= 9.0.0（若未安装：`npm install -g pnpm`）
- **Python** >= 3.12

### 前端启动

> 前端依赖详情见 [`frontend/dependencies.md`](frontend/dependencies.md)

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖（等同于 pip install -r requirements.txt）
pnpm install

# 3. 启动开发服务器（默认端口 3000）
pnpm dev
```

访问 http://localhost:3000 查看首页。

### 后端启动

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境并激活
python3 -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动开发服务器（默认端口 8000）
uvicorn app.main:app --reload --port 8000
```

### 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 登录接口（Demo 模式下任意账号可登录）
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"123456"}'

# AI 分析接口
curl -X POST http://localhost:8000/api/v1/chat/analyze \
  -H "Content-Type: application/json" \
  -d '{"game_description":"一款RPG冒险游戏","game_type":"RPG"}'
```

### API 文档

后端启动后（`DEBUG=true` 时），访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 环境变量

### 前端 (`frontend/packages/main-app/.env.development`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_DEMO_MODE` | `true` | 是否启用前端 Demo 模式 |
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | 后端 API 地址 |

### 后端 (`backend/.env`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEMO_MODE` | `true` | 是否启用后端 Demo 模式 |
| `DEBUG` | `true` | 是否开启调试（Swagger 文档） |
| `JWT_SECRET` | `dev-secret-key-...` | JWT 签名密钥 |
| `JWT_EXPIRE_MINUTES` | `1440` | Token 过期时间（分钟） |

### 环境变量安全规范

> **`.env` 文件不提交到 Git**，已通过 `.gitignore` 忽略。

| 文件 | 是否提交 | 说明 |
|------|----------|------|
| `backend/.env` | **否** | 含 JWT 密钥等敏感信息，仅本地使用 |
| `backend/.env.example` | **是** | 模板文件，不含真实密钥，供团队参考 |
| `frontend/.env.development` | **是** | 仅含 `VITE_` 前缀变量，会暴露到浏览器端，本身无敏感信息 |
| `frontend/.env.local` | **否** | 本地覆盖配置，已被 gitignore 忽略 |

**新成员加入项目时：**

```bash
cp backend/.env.example backend/.env
# 修改 JWT_SECRET 等配置为自己的本地值
```

**为什么不提交 `.env`：**
- `JWT_SECRET` 泄露后任何人可伪造 Token
- 生产环境会配置数据库密码、第三方 API Key 等敏感凭证
- Git 历史永久保留，即使后续删除也需要 `git filter-branch` 才能彻底清除
- 每位开发者的本地配置不同，提交会导致频繁合并冲突

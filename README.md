# ANIMAGUS — Game Marketing Pro

> AI 驱动的游戏全球营销一站式平台

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
ANIMAGUS/
├── README.md
├── doc/                              # 项目文档
│   └── 06-技术框架规划文档-详细版.md
├── html/                             # HTML 原型稿
│
├── frontend/                         # 前端 monorepo
│   ├── package.json                  # 根 package（scripts 入口）
│   ├── pnpm-workspace.yaml           # pnpm workspace 配置
│   └── packages/
│       ├── main-app/                 # Vue3 主应用（默认端口 3010）
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
- **Python** >= 3.10

### 一键启动（推荐）

项目提供了一键部署脚本，自动完成环境检测、依赖安装和服务启动：

```bash
# 默认端口启动（前端:3010 / 后端:8010）
./run_server.sh

# 自定义端口启动
./run_server.sh --frontend-port 4000 --backend-port 9000

# 查看帮助
./run_server.sh --help
```

脚本会自动：
1. 检测 Python、Node.js、pnpm 版本
2. 创建 Python 虚拟环境并安装后端依赖
3. 安装前端依赖（pnpm install）
4. 启动后端 FastAPI 服务和前端 Vite 开发服务器
5. 在浏览器中打开前端页面

### 一键停止

```bash
# 停止服务（自动读取启动时的端口配置）
./stop_server.sh

# 指定端口停止
./stop_server.sh --frontend-port 4000 --backend-port 9000
```

> 在 `run_server.sh` 运行期间，也可以直接按 `Ctrl+C` 停止所有服务。

---

## 云端部署

### 云端启动命令

```bash
# 云端模式启动（全部服务）
./run_server.sh --mode cloud

# 云端模式 + 跳过依赖安装（适合已安装依赖的环境）
./run_server.sh --mode cloud --skip-install

# 仅启动后端
./run_server.sh --mode cloud --only backend --skip-install

# 仅启动前端
./run_server.sh --mode cloud --only frontend --skip-install

# 自定义端口
./run_server.sh --mode cloud --frontend-port 80 --backend-port 8000
```

### 启动参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode local\|cloud` | 启动模式：`local`（本地开发）/ `cloud`（云端部署） | `local` |
| `--only all\|backend\|frontend` | 仅启动指定服务 | `all` |
| `--skip-install` | 跳过依赖安装（云端常用） | 否 |
| `--host HOST` | 监听地址 | `0.0.0.0` |
| `--frontend-port PORT` | 前端端口 | `3010` |
| `--backend-port PORT` | 后端端口 | `8010` |

**云端模式与本地模式的区别**：
- 云端模式不自动打开浏览器
- 云端模式后端不启用 `--reload`，启用 `--workers 2`
- 云端模式若存在环境变量 `PORT` 且未显式指定 `--frontend-port`，将使用 `PORT` 作为前端端口

### 云端环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `CORS_ALLOW_ORIGINS` | 后端 CORS 允许的来源（逗号分隔） | `https://your-domain.com,http://your-domain.com` |
| `VITE_BACKEND_HOST` | 前端代理的后端地址（默认 `127.0.0.1`） | `10.0.0.5` |
| `PORT` | 云平台注入的端口（cloud 模式下自动用于前端） | `8080` |

**示例：云端启动并配置 CORS**

```bash
CORS_ALLOW_ORIGINS="https://your-domain.com" ./run_server.sh --mode cloud --skip-install
```

### 云平台端口暴露

不同云平台需要确保端口正确暴露：

| 平台类型 | 操作 |
|----------|------|
| **VM/裸机** | 安全组/防火墙放通 `3010`（前端）和 `8010`（后端） |
| **Docker** | `-p 3010:3010 -p 8010:8010` 或使用 `--network host` |
| **平台托管（Render/Fly/Heroku）** | 设置环境变量 `PORT`，脚本会自动使用 |
| **K8s/Ingress** | 配置 Service 暴露端口，Ingress 路由 `/api` 到后端 |

### 单端口部署（Nginx 反代）

如果云平台只允许暴露一个端口，可以用 Nginx 统一入口：

```nginx
server {
    listen 80;

    location / {
        proxy_pass http://127.0.0.1:3010;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8010;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

### 手动启动

如需分别启动前后端，可按以下步骤操作：

#### 前端

> 前端依赖详情见 [`frontend/dependencies.md`](frontend/dependencies.md)

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
pnpm install

# 3. 启动开发服务器（默认端口 3010）
pnpm dev

# 自定义端口
VITE_FRONTEND_PORT=4000 VITE_BACKEND_PORT=9000 pnpm dev
```

访问 http://localhost:3010 查看首页。

#### 后端

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境并激活
python3 -m venv venv
source venv/bin/activate    # macOS/Linux
# venv\Scripts\activate     # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动开发服务器（默认端口 8010）
uvicorn app.main:app --reload --port 8010
```

### 验证服务

```bash
# 健康检查
curl http://localhost:8010/health

# 登录接口（Demo 模式下任意账号可登录）
curl -X POST http://localhost:8010/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"123456"}'

# AI 分析接口
curl -X POST http://localhost:8010/api/v1/chat/analyze \
  -H "Content-Type: application/json" \
  -d '{"game_description":"一款RPG冒险游戏","game_type":"RPG"}'
```

### API 文档

后端启动后（`DEBUG=true` 时），访问：
- **Swagger UI**: http://localhost:8010/docs
- **ReDoc**: http://localhost:8010/redoc

---

## 环境变量

### 前端 (`frontend/packages/main-app/.env.development`)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_DEMO_MODE` | `true` | 是否启用前端 Demo 模式 |
| `VITE_API_BASE_URL` | `http://localhost:8010/api/v1` | 后端 API 地址 |
| `VITE_FRONTEND_PORT` | `3010` | 前端开发服务器端口 |
| `VITE_BACKEND_PORT` | `8010` | 后端 API 代理目标端口 |

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

---

## 🔌 广告平台 API 对接

### 已完成平台

#### ✅ Meta (Facebook) Ads API
- **状态**: 完全验证通过
- **功能**:
  - OAuth 2.0 认证
  - 广告账户管理
  - Campaign/AdSet/Ad 创建
  - 素材上传（图片/视频）
  - 数据洞察获取
  - 预算和状态管理
- **测试结果**: 成功连接 2 个广告账户
- **文档**: [Meta API 测试报告](backend/META_API_SUCCESS.md)

#### ⏳ Google Ads API
- **状态**: 代码完成，等待 Developer Token 激活
- **功能**:
  - OAuth 2.0 认证
  - Campaign/AdGroup 管理
  - 广告创建
  - GAQL 查询支持
  - 数据洞察获取
- **文档**: [Google API 测试报告](backend/GOOGLE_API_TEST_RESULT.md)

### API 端点

**平台认证**
```
POST   /api/v1/platform/connect          # 获取 OAuth URL
POST   /api/v1/platform/callback         # OAuth 回调处理
GET    /api/v1/platform/accounts         # 获取已连接账号
POST   /api/v1/platform/accounts/test    # 添加测试账号
DELETE /api/v1/platform/accounts/{id}    # 断开账号连接
```

**广告管理**
```
POST   /api/v1/campaigns                 # 创建广告系列
GET    /api/v1/campaigns                 # 获取广告列表
PUT    /api/v1/campaigns/{id}            # 更新广告
GET    /api/v1/campaigns/{id}/insights   # 获取数据洞察
```

**素材管理**
```
POST   /api/v1/materials/upload          # 上传素材
GET    /api/v1/materials                 # 获取素材列表
```

### 测试工具

```bash
cd backend
source venv/bin/activate

# 快速测试（推荐）
python3 scripts/quick_test.py

# 完整测试
python3 scripts/test_platform_api.py
```

### 配置凭证

详细的凭证获取指南：[API 测试指南](backend/API_TEST_GUIDE.md)

**Meta (Facebook)**
- App ID 和 App Secret
- Access Token（包含 ads_management 权限）

**Google Ads**
- Client ID 和 Client Secret
- Developer Token（需要经理账号）
- Customer ID

### 测试报告

- [API 测试指南](backend/API_TEST_GUIDE.md) - 如何获取凭证和测试
- [后端 API 测试报告](backend/TEST_REPORT.md) - 后端框架验证
- [Meta API 成功报告](backend/META_API_SUCCESS.md) - Meta 平台完整测试
- [Google API 测试结果](backend/GOOGLE_API_TEST_RESULT.md) - Google 平台测试
- [最终测试报告](backend/FINAL_API_TEST_REPORT.md) - 完整测试总结

---

## 📝 更新日志

### 2026-04-27 - 广告平台 API 对接
- ✅ 完成 Meta (Facebook) Ads API 对接和测试
- ✅ 完成 Google Ads API 代码实现
- ✅ 创建 API 测试工具和完整文档
- ✅ 验证后端 API 框架正常运行
- ✅ 成功连接 Meta 广告账户（2个账户）

---

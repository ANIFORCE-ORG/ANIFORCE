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
├── docs/                             # 项目文档
│   ├── database/                     # 数据库设计文档
│   ├── materials/                    # 素材相关文档
│   └── pages/                        # 页面原型文档
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
│       │   ├── .env.development      # 开发环境配置
│       │   ├── .env.example          # 环境变量模板
│       │   └── src/
│       │       ├── main.ts           # 应用入口
│       │       ├── App.vue           # 根组件
│       │       ├── router/index.ts   # 路由配置
│       │       ├── store/            # Pinia 状态管理
│       │       │   └── auth.ts       # 认证状态
│       │       ├── config/           # 配置文件
│       │       │   ├── agent.ts      # AD Agent API 配置
│       │       │   └── navigation.ts # 导航配置
│       │       ├── api/              # API 客户端
│       │       │   └── http.ts       # HTTP 客户端封装
│       │       ├── services/         # 业务服务层
│       │       │   └── agentService.ts  # AD Agent 服务
│       │       ├── styles/           # 样式文件
│       │       │   └── global.css    # TailwindCSS 全局样式
│       │       ├── pages/            # 页面组件（模块化组织）
│       │       │   ├── settings/     # 设置相关页面
│       │       │   │   ├── Settings.vue          # 设置主页（卡片入口）
│       │       │   │   ├── AccountConfig.vue     # 账号配置
│       │       │   │   ├── AIUsageConfig.vue     # AI 使用量
│       │       │   │   └── PlatformConnections.vue  # 平台连接
│       │       │   ├── projects/     # 项目相关页面
│       │       │   │   ├── Projects.vue          # 项目列表
│       │       │   │   └── ProjectDetail.vue     # 项目详情
│       │       │   ├── campaigns/    # 广告系列相关页面
│       │       │   │   ├── Campaign.vue          # 广告系列列表
│       │       │   │   ├── CampaignDetail.vue    # 广告系列详情
│       │       │   │   └── CreateCampaign.vue    # 创建广告系列
│       │       │   ├── creatives/    # 素材相关页面
│       │       │   │   └── Material.vue          # 素材管理
│       │       │   ├── starting/     # 启动相关页面
│       │       │   │   ├── GetStart.vue          # 欢迎页
│       │       │   │   ├── Login.vue             # 登录页
│       │       │   │   └── Register.vue          # 注册页
│       │       │   ├── Home.vue      # 首页（AI 对话交互）
│       │       │   ├── Monitor.vue   # 实时监控
│       │       │   ├── Dashboard.vue # 数据看板
│       │       │   └── MarketAnalysis.vue  # 市场分析
│       │       ├── composables/      # Vue3 Composables
│       │       │   └── useToast.ts           # Toast 提示管理
│       │       └── components/       # 可复用组件
│       │           ├── layout/       # 布局组件
│       │           │   ├── SidebarNav.vue    # 侧边栏导航
│       │           │   ├── AppHeader.vue     # 顶部导航
│       │           │   └── AppFooter.vue     # 页脚
│       │           ├── toasts/       # Toast 提示组件
│       │           │   ├── ToastContainer.vue  # Toast 容器（支持多个平铺）
│       │           │   └── Toast.vue         # 单个 Toast 组件（已弃用）
│       │           ├── settings/     # 设置相关组件
│       │           │   └── MetaConfigDialog.vue  # Meta 配置弹窗
│       │           ├── projects/     # 项目相关组件
│       │           │   └── CreateProjectModal.vue
│       │           └── chat/         # 对话相关组件
│       │               ├── ChatPanel.vue
│       │               └── MessageBubble.vue
│       └── shared/                   # 跨应用共享包
│           ├── index.ts              # 统一导出
│           ├── types/index.ts        # 类型定义
│           └── utils/constants.ts    # 常量
│
└── backend/                          # 后端 FastAPI 服务
    ├── alembic/                      # 数据库迁移
    │   └── versions/                 # 迁移脚本
    ├── requirements.txt              # Python 依赖
    ├── .env.example                  # 环境变量模板
    └── app/
        ├── __init__.py
        ├── main.py                   # FastAPI 入口 + CORS + 异常处理
        ├── config/
        │   └── settings.py           # Pydantic Settings 配置
        ├── database/                 # 数据库配置
        │   ├── postgres.py           # PostgreSQL 连接
        │   └── mongodb.py            # MongoDB 连接
        ├── models/                   # SQLAlchemy 模型
        │   ├── user.py               # 用户模型
        │   ├── project.py            # 项目模型
        │   └── campaign.py           # 广告系列模型
        ├── schemas/                  # Pydantic 请求/响应模型
        │   ├── base.py               # ResponseBase / ErrorResponse
        │   ├── auth.py               # 认证相关 Schema
        │   └── chat.py               # 对话相关 Schema
        ├── api/                      # API 路由
        │   ├── deps.py               # 公共依赖（认证中间件）
        │   └── v1/
        │       ├── router.py         # 路由聚合
        │       ├── auth.py           # 认证接口
        │       ├── users.py          # 用户管理
        │       ├── projects.py       # 项目管理
        │       └── campaigns.py      # 广告系列管理
        └── services/                 # 纯业务逻辑
            ├── auth_service.py
            ├── user_service.py
            ├── project_service.py
            └── campaign_service.py
```

### 目录组织原则

**前端页面模块化**：
- `pages/settings/` - 设置相关页面集中管理
- `pages/projects/` - 项目相关页面集中管理
- `pages/campaigns/` - 广告系列相关页面集中管理
- 提高代码可维护性和可扩展性

**组件复用**：
- `components/settings/` - 设置相关可复用组件
- `components/projects/` - 项目相关可复用组件
- `components/layout/` - 布局组件
- 遵循单一职责原则，便于测试和维护

**配置集中管理**：
- `config/agent.ts` - AD Agent API 配置（环境变量驱动）
- `config/navigation.ts` - 导航配置
- 统一管理，易于修改和部署

---

## 快速启动

### 环境要求

- **Node.js** >= 20.0.0
- **pnpm** >= 9.0.0（若未安装：`npm install -g pnpm`）
- **Python** >= 3.10

### 一键启动（推荐）

项目提供了一键部署脚本，自动完成环境检测、依赖安装和服务启动：

```bash
# 本地开发模式（默认）
./run_server.sh

# 云端生产模式
./run_server.sh --mode cloud

# 云端模式 + 跳过依赖安装
./run_server.sh --mode cloud --skip-install

# 自定义端口启动
./run_server.sh --frontend-port 4000 --backend-port 9000

# 云端模式 + 自定义 IP
CLOUD_IP=your-server-ip ./run_server.sh --mode cloud

# 查看完整帮助
./run_server.sh --help
```

脚本会自动：
1. 检测 Python、Node.js、pnpm 版本
2. 创建 Python 虚拟环境并安装后端依赖
3. 安装前端依赖（pnpm install）
4. **根据启动模式自动配置 `.env` 文件中的服务地址**
5. 启动后端 FastAPI 服务和前端 Vite 开发服务器
6. 在浏览器中打开前端页面（仅 local 模式）

### 一键停止

```bash
# 停止服务（自动读取启动时的端口配置）
./stop_server.sh

# 指定端口停止
./stop_server.sh --frontend-port 4000 --backend-port 9000
```

> 在 `run_server.sh` 运行期间，也可以直接按 `Ctrl+C` 停止所有服务。

---

## 启动模式说明

### Local vs Cloud 模式配置对比

| 配置项 | **Local 模式** | **Cloud 模式** | 说明 |
|--------|---------------|---------------|------|
| **后端启动参数** | | | |
| `--reload` | ✅ 启用 | ❌ 禁用 | 热重载，代码修改自动重启 |
| `--workers` | ❌ 单进程 | ✅ `--workers 2` | 多进程提高并发性能 |
| **前端启动参数** | | | |
| `--host` | 默认（仅本地） | `--host 0.0.0.0` | 允许外部访问 |
| `VITE_BACKEND_HOST` | `127.0.0.1` | `0.0.0.0` | 前端连接后端的地址 |
| **自动配置 .env** | | | |
| `FRONTEND_BASE_URL` | `http://localhost:3010` | `http://8.148.151.36:3010` | 前端服务地址 |
| `BACKEND_BASE_URL` | `http://localhost:8010` | `https://8.148.151.36:8010` | 后端服务地址 |
| **其他行为** | | | |
| 自动打开浏览器 | ✅ 是 | ❌ 否 | local 模式自动打开 localhost |
| 端口配置 | 固定 `3010/8010` | 支持环境变量 `PORT` | cloud 优先使用 `$PORT` |
| **适用场景** | 本地开发调试 | 云端生产部署 | |

### 启动参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--mode local\|cloud` | 启动模式：`local`（本地开发）/ `cloud`（云端部署） | `local` |
| `--only all\|backend\|frontend` | 仅启动指定服务 | `all` |
| `--skip-install` | 跳过依赖安装（云端常用） | 否 |
| `--host HOST` | 监听地址 | `0.0.0.0` |
| `--demo` | 启用 Demo 模式（设置 `DEMO_MODE=true`） | 否（生产模式） |
| `--frontend-port PORT` | 前端端口 | `3010` |
| `--backend-port PORT` | 后端端口 | `8010` |

### 环境变量

| 变量 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `CLOUD_IP` | 云端模式的 IP 地址 | `8.148.151.36` | `CLOUD_IP=your-server-ip` |
| `PORT` | 云平台注入的端口（cloud 模式自动用于前端） | - | `PORT=8080` |
| `CORS_ALLOW_ORIGINS` | 后端 CORS 允许的来源（逗号分隔） | - | `https://your-domain.com` |
| `VITE_BACKEND_HOST` | 前端代理的后端地址 | `127.0.0.1` (local) / `0.0.0.0` (cloud) | `10.0.0.5` |

---

## 云端部署

### 云端启动命令

```bash
# 云端模式启动（全部服务，使用默认 IP）
./run_server.sh --mode cloud

# 云端模式 + 自定义 IP
CLOUD_IP=your-server-ip ./run_server.sh --mode cloud

# 云端模式 + 跳过依赖安装（适合已安装依赖的环境）
./run_server.sh --mode cloud --skip-install

# 仅启动后端
./run_server.sh --mode cloud --only backend --skip-install

# 仅启动前端
./run_server.sh --mode cloud --only frontend --skip-install

# 自定义端口
./run_server.sh --mode cloud --frontend-port 80 --backend-port 8000
```

### 自动配置说明

脚本会根据启动模式**自动配置** `backend/.env` 文件中的服务地址：

**Local 模式**：
```bash
FRONTEND_BASE_URL=http://localhost:3010
BACKEND_BASE_URL=http://localhost:8010
```

**Cloud 模式**（使用默认 IP `8.148.151.36`）：
```bash
FRONTEND_BASE_URL=http://8.148.151.36:3010
BACKEND_BASE_URL=https://8.148.151.36:8010
```

**Cloud 模式**（使用自定义 IP）：
```bash
CLOUD_IP=192.168.1.100 ./run_server.sh --mode cloud
# 自动配置为：
# FRONTEND_BASE_URL=http://192.168.1.100:3010
# BACKEND_BASE_URL=https://192.168.1.100:8010
```

> 💡 **提示**：无需手动修改 `.env` 文件，只需切换启动模式即可自动适配！

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

## 最新功能更新

### 🎉 Toast 通用提示组件系统（2026-05-16）

**功能特性**：
- ✅ 支持多个 Toast 同时显示（最多 3 个平铺展示）
- ✅ 4 种提示类型：`success`、`error`、`warning`、`info`
- ✅ 自动关闭（默认 3 秒）+ 手动关闭
- ✅ 优雅的进出场动画
- ✅ 完美支持深色模式
- ✅ 非阻塞式用户体验

**使用方式**：
```vue
<script setup>
import ToastContainer from '@/components/toasts/ToastContainer.vue'
import { useToast } from '@/composables/useToast'

const { success, error, warning, info } = useToast()

// 显示提示
success('操作成功')
error('操作失败')
warning('警告信息')
info('提示信息')
</script>

<template>
  <!-- 你的内容 -->
  <ToastContainer />
</template>
```

**已应用页面**：
- `AccountConfig.vue` - 用户名/密码修改提示
- `Login.vue` - 功能开发中提示
- `Material.vue` - 素材上传提示

### 🔐 登录错误处理优化（2026-05-16）

**优化内容**：
- 后端区分"邮箱未注册"（404）和"密码错误"（401）
- 前端根据 HTTP 状态码显示精确错误信息
- 提升用户体验和错误提示准确性

**错误提示**：
- 邮箱未注册 → "该邮箱尚未注册"
- 密码错误 → "密码错误"
- 网络错误 → "网络错误，请稍后重试"

### 📁 素材管理页面重构（2026-05-16）

**目录结构优化**：
- 创建 `pages/creatives/` 目录
- 移动 `Material.vue` 到新目录
- 创建 `pages/starting/` 目录（登录/注册页面）
- 提升代码组织和可维护性

**路由配置**：
- 路径：`/material`
- 组件：`@/pages/creatives/Material.vue`
- 导航菜单：创意素材

### 📤 素材上传功能优化（2026-05-16）

**已实现功能**：
- ✅ 文件选择（支持多选）
- ✅ 拖拽上传
- ✅ 文件类型验证（JPG/PNG/GIF/MP4/MOV）
- ✅ 文件大小限制（最大 100MB）
- ✅ Toast 提示替代 alert
- ✅ 上传进度显示框架
- ✅ 自动刷新素材列表

**待开发功能**：
- ⏳ 后端 API 对接
- ⏳ 实时上传进度显示
- ⏳ 批量上传优化

**当前状态**：
点击"完成上传"按钮会显示友好提示："上传功能待开发完善！"

---

## 开发规范

### 页面组织规范

**模块化目录结构**：
- `pages/settings/` - 设置相关页面
- `pages/projects/` - 项目管理页面
- `pages/campaigns/` - 广告系列页面
- `pages/creatives/` - 素材管理页面
- `pages/starting/` - 启动流程页面（登录/注册/欢迎）

**组件复用原则**：
- `components/layout/` - 布局组件
- `components/toasts/` - Toast 提示组件
- `components/settings/` - 设置相关组件
- `components/projects/` - 项目相关组件
- 遵循单一职责原则，便于测试和维护

### Toast 使用规范

**推荐使用场景**：
- ✅ 操作成功/失败反馈
- ✅ 表单验证错误提示
- ✅ 功能开发中提示
- ✅ 网络请求错误提示

**不推荐使用场景**：
- ❌ 需要用户确认的操作（使用 Modal）
- ❌ 复杂的错误信息（使用专门的错误页面）
- ❌ 长时间显示的信息（使用 Banner）

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

**提交 PR 前请确保**：
1. 代码符合项目规范
2. 添加必要的注释
3. 更新相关文档
4. 通过所有测试

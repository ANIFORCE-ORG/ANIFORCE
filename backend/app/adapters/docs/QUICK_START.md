# Meta 广告授权 - 快速开始

## 5分钟快速上手

### 1. 配置环境 (1分钟)

编辑 `/backend/.env` 文件：

```bash
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret
OAUTH_REDIRECT_URI=http://localhost:3010/auth-callback
```

### 2. 安装依赖 (1分钟)

```bash
cd /Users/micolin/Documents/MProjects/ANIFORCE/ANIMAGUS/backend
pip install -r requirements.txt
```

### 3. 启动服务 (30秒)

```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 4. 测试接口 (2分钟)

#### 方式 1: 使用 curl

```bash
# 获取授权 URL
curl -X POST http://localhost:8000/api/v1/platform-auth/meta/connect
```

#### 方式 2: 使用 Python 脚本

```bash
# 运行单元测试
python scripts/test_meta_adapter.py

# 运行 OAuth 流程演示
python scripts/demo_oauth_flow.py
```

#### 方式 3: 前端集成

```javascript
// 连接 Meta 平台
const response = await fetch('http://localhost:8000/api/v1/platform-auth/meta/connect', {
  method: 'POST'
});
const { auth_url } = await response.json();
window.open(auth_url, 'oauth', 'width=600,height=700');
```

### 5. 查看文档 (30秒)

- **架构设计**: `README.md`
- **使用指南**: `USAGE.md`
- **实现总结**: `IMPLEMENTATION_SUMMARY.md`

## API 端点速查

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/platform-auth/meta/connect` | POST | 获取授权 URL |
| `/api/v1/platform-auth/callback` | POST | 换取 Token |
| `/api/v1/platform-auth/meta/accounts` | GET | 获取账户列表 |

## 常用命令

```bash
# 启动开发服务器
python -m uvicorn app.main:app --reload --port 8000

# 运行测试
python scripts/test_meta_adapter.py

# 查看 API 文档
open http://localhost:8000/docs

# 查看健康检查
curl http://localhost:8000/health
```

## 目录结构

```
backend/
├── app/
│   ├── adapters/          # 广告平台适配器
│   │   ├── base.py       # 基类
│   │   ├── meta_ads.py   # Meta 实现
│   │   └── *.md          # 文档
│   ├── api/v1/
│   │   └── platform_auth.py  # 授权 API
│   └── config/
│       └── settings.py   # 配置
└── scripts/
    ├── test_meta_adapter.py      # 单元测试
    └── demo_oauth_flow.py        # 演示脚本
```

## 下一步

1. 配置真实的 Meta App ID 和 Secret
2. 在前端集成授权流程
3. 实现 Token 数据库存储
4. 添加其他平台支持（Google Ads、TikTok Ads）

## 获取帮助

- 查看 `USAGE.md` 了解详细使用方法
- 查看 `README.md` 了解架构设计
- 运行 `python scripts/demo_oauth_flow.py` 查看演示

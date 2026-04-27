# 广告平台 API 对接测试指南

## 📋 测试概览

本指南帮助你验证 Google Ads 和 Meta (Facebook) 广告平台的 API 对接是否成功。

## 🚀 快速开始

### 1. 启动后端服务

```bash
cd /Users/PJlai/Desktop/ANIMAGUS_remote/backend
source venv/bin/activate  # 激活虚拟环境
uvicorn app.main:app --reload --port 8000
```

### 2. 运行测试脚本

在新的终端窗口中：

```bash
cd /Users/PJlai/Desktop/ANIMAGUS_remote/backend
source venv/bin/activate
python3 scripts/quick_test.py
```

## 🔑 获取 API 凭证

### Meta (Facebook) 广告平台

#### 步骤 1: 创建 Facebook 应用
1. 访问 [Facebook Developers](https://developers.facebook.com/apps/)
2. 点击 "Create App" → 选择 "Business" 类型
3. 填写应用名称和联系邮箱

#### 步骤 2: 添加 Marketing API
1. 在应用控制台，点击 "Add Product"
2. 找到 "Marketing API"，点击 "Set Up"

#### 步骤 3: 获取 Access Token
1. 进入 Tools → [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. 选择你的应用
3. 点击 "Generate Access Token"
4. 勾选权限：
   - `ads_management`
   - `ads_read`
   - `business_management`
5. 复制生成的 Access Token

#### 步骤 4: 获取长期 Token（可选）
短期 Token 只有 1-2 小时有效期，建议换成长期 Token（60天）：

```bash
curl -X GET "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
```

### Google Ads 平台

#### 步骤 1: 创建 Google Cloud 项目
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目

#### 步骤 2: 启用 Google Ads API
1. 在项目中，进入 "APIs & Services" → "Library"
2. 搜索 "Google Ads API"
3. 点击 "Enable"

#### 步骤 3: 创建 OAuth 2.0 凭证
1. 进入 "APIs & Services" → "Credentials"
2. 点击 "Create Credentials" → "OAuth 2.0 Client ID"
3. 应用类型选择 "Web application"
4. 添加授权重定向 URI: `http://localhost:3013/auth-callback`
5. 保存 Client ID 和 Client Secret

#### 步骤 4: 申请 Developer Token
1. 访问 [Google Ads API Center](https://ads.google.com/aw/apicenter)
2. 申请 Developer Token（测试环境可以立即使用）
3. 生产环境需要等待审核（通常 1-2 天）

#### 步骤 5: 获取 Access Token
使用 [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)：
1. 点击右上角设置图标
2. 勾选 "Use your own OAuth credentials"
3. 输入你的 Client ID 和 Client Secret
4. 在左侧选择 "Google Ads API v15"
5. 点击 "Authorize APIs"
6. 完成授权后，点击 "Exchange authorization code for tokens"
7. 复制 Access Token 和 Refresh Token

## 🧪 测试方法

### 方法 1: 使用快速测试脚本（推荐）

```bash
python3 scripts/quick_test.py
```

选择测试类型：
- **选项 1**: 测试 Meta API（需要 Access Token）
- **选项 2**: 测试 Google Ads API（需要 Access Token、Customer ID、Developer Token）
- **选项 3**: 测试后端 API 服务
- **选项 4**: 测试所有

### 方法 2: 使用完整测试脚本

```bash
python3 scripts/test_platform_api.py
```

这个脚本提供更详细的测试，包括：
- OAuth 流程测试
- 账户列表获取
- 后端 API 端点测试

### 方法 3: 使用 curl 直接测试

#### 测试 Meta API
```bash
curl "https://graph.facebook.com/v19.0/me/adaccounts?access_token=YOUR_ACCESS_TOKEN&fields=id,name,account_status,currency"
```

#### 测试 Google Ads API
```bash
curl -X POST "https://googleads.googleapis.com/v15/customers/YOUR_CUSTOMER_ID/googleAds:search" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "developer-token: YOUR_DEVELOPER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT customer.id, customer.descriptive_name FROM customer LIMIT 1"}'
```

#### 测试后端 API
```bash
# 获取 Meta OAuth URL
curl -X POST "http://localhost:8000/api/v1/platform/connect?platform=meta"

# 获取 Google OAuth URL
curl -X POST "http://localhost:8000/api/v1/platform/connect?platform=google"

# 添加测试账号
curl -X POST "http://localhost:8000/api/v1/platform/accounts/test?platform=meta"

# 获取已连接账号
curl "http://localhost:8000/api/v1/platform/accounts"
```

## ✅ 验证清单

### Meta (Facebook) API
- [ ] 成功创建 Facebook 应用
- [ ] 获取 App ID 和 App Secret
- [ ] 生成 Access Token（包含必要权限）
- [ ] 能够获取广告账户列表
- [ ] 后端能生成正确的 OAuth URL

### Google Ads API
- [ ] 创建 Google Cloud 项目
- [ ] 启用 Google Ads API
- [ ] 获取 OAuth 2.0 凭证（Client ID、Client Secret）
- [ ] 申请 Developer Token
- [ ] 获取 Access Token 和 Refresh Token
- [ ] 能够查询客户信息
- [ ] 后端能生成正确的 OAuth URL

### 后端 API
- [ ] 后端服务成功启动（端口 8000）
- [ ] `/api/v1/platform/connect` 端点正常
- [ ] `/api/v1/platform/accounts` 端点正常
- [ ] 能够添加测试账号

## 🔧 常见问题

### 1. Meta API 返回 "Invalid OAuth access token"
- 检查 Access Token 是否过期
- 确认 Token 包含必要的权限
- 尝试重新生成 Token

### 2. Google Ads API 返回 "UNAUTHENTICATED"
- 检查 Access Token 是否有效
- 确认 Developer Token 正确
- 验证 Customer ID 格式（移除连字符）

### 3. 后端服务无法启动
```bash
# 检查端口是否被占用
lsof -ti:8000

# 如果被占用，杀死进程
kill -9 $(lsof -ti:8000)

# 重新启动
uvicorn app.main:app --reload --port 8000
```

### 4. 找不到 Customer ID (Google Ads)
1. 登录 [Google Ads](https://ads.google.com/)
2. 右上角查看客户 ID（格式: 123-456-7890）

## 📊 测试结果示例

### 成功的 Meta API 测试
```
✅ Meta API 连接成功！
   找到 2 个广告账户:
   - My Business Account (ID: act_123456789)
     状态: 1, 货币: USD
   - Test Account (ID: act_987654321)
     状态: 1, 货币: USD
```

### 成功的 Google Ads API 测试
```
✅ Google Ads API 连接成功！
   客户 ID: 1234567890
   客户名称: My Company
```

## 📝 下一步

测试成功后，你可以：

1. **配置生产环境凭证**
   - 将测试凭证替换为生产凭证
   - 使用环境变量或配置文件管理敏感信息

2. **实现完整的 OAuth 流程**
   - 在前端添加"连接账号"按钮
   - 处理 OAuth 回调
   - 存储 Token 到数据库

3. **测试广告创建功能**
   - 使用 adapter 创建测试广告系列
   - 验证广告组和广告创建
   - 测试数据获取功能

## 🔗 相关文档

- [Meta Marketing API 文档](https://developers.facebook.com/docs/marketing-apis)
- [Google Ads API 文档](https://developers.google.com/google-ads/api/docs/start)
- [项目 API 适配器代码](./app/connectors/)

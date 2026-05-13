# Meta 广告授权接口使用指南

## 快速开始

### 1. 配置环境变量

在 `/backend/.env` 文件中添加 Meta 平台凭证：

```bash
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret
OAUTH_REDIRECT_URI=http://localhost:3010/auth-callback
```

### 2. 安装依赖

```bash
cd /Users/micolin/Documents/MProjects/ANIFORCE/ANIMAGUS/backend
pip install -r requirements.txt
```

### 3. 启动后端服务

```bash
python -m uvicorn app.main:app --reload --port 8000
```

## API 接口说明

### 基础 URL
```
http://localhost:8000/api/v1/platform-auth
```

### 接口列表

#### 1. 获取 OAuth 授权 URL

**请求**:
```http
POST /api/v1/platform-auth/meta/connect
Content-Type: application/json
```

**响应**:
```json
{
  "auth_url": "https://www.facebook.com/v19.0/dialog/oauth?client_id=...",
  "state": "random_state_string"
}
```

**前端调用示例**:
```javascript
const response = await fetch('http://localhost:8000/api/v1/platform-auth/meta/connect', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' }
});

const { auth_url, state } = await response.json();

// 打开授权窗口
window.open(auth_url, 'oauth_meta', 'width=600,height=700');
```

#### 2. OAuth 回调处理

**请求**:
```http
POST /api/v1/platform-auth/callback
Content-Type: application/json

{
  "platform": "meta",
  "code": "authorization_code_from_facebook",
  "redirect_uri": "http://localhost:3010/auth-callback",
  "state": "random_state_string"
}
```

**响应**:
```json
{
  "access_token": "EAAxxxxxxxx",
  "token_type": "bearer",
  "expires_in": 5183944,
  "refresh_token": null
}
```

**前端调用示例**:
```javascript
const response = await fetch('http://localhost:8000/api/v1/platform-auth/callback', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    platform: 'meta',
    code: authCode,
    redirect_uri: 'http://localhost:3010/auth-callback',
    state: stateParam
  })
});

const tokenData = await response.json();
// 保存 access_token 到 localStorage 或状态管理
localStorage.setItem('meta_access_token', tokenData.access_token);
```

#### 3. 获取广告账户列表

**请求**:
```http
GET /api/v1/platform-auth/meta/accounts?access_token=EAAxxxxxxxx
```

**响应**:
```json
[
  {
    "id": "act_123456789",
    "name": "My Ad Account",
    "account_status": 1,
    "currency": "USD",
    "timezone_name": "America/Los_Angeles",
    "amount_spent": "1000.00"
  }
]
```

**前端调用示例**:
```javascript
const accessToken = localStorage.getItem('meta_access_token');
const response = await fetch(
  `http://localhost:8000/api/v1/platform-auth/meta/accounts?access_token=${accessToken}`
);

const accounts = await response.json();
console.log('广告账户列表:', accounts);
```

## 完整前端集成示例

### 1. 连接 Meta 平台

```javascript
class MetaAuthService {
  constructor() {
    this.baseURL = 'http://localhost:8000/api/v1/platform-auth';
  }

  async connect() {
    // 1. 获取授权 URL
    const response = await fetch(`${this.baseURL}/meta/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });

    const { auth_url, state } = await response.json();

    // 保存 state 用于验证
    sessionStorage.setItem('oauth_state', state);

    // 2. 打开授权窗口
    const authWindow = window.open(
      auth_url,
      'oauth_meta',
      'width=600,height=700,left=100,top=100'
    );

    // 3. 监听回调
    return new Promise((resolve, reject) => {
      window.addEventListener('message', async (event) => {
        if (event.data.type === 'oauth_callback' && event.data.code) {
          try {
            // 验证 state
            const savedState = sessionStorage.getItem('oauth_state');
            if (event.data.state !== savedState) {
              throw new Error('State mismatch');
            }

            // 用 code 换取 token
            const tokenData = await this.exchangeToken(event.data.code);
            resolve(tokenData);
          } catch (error) {
            reject(error);
          }
        }
      });
    });
  }

  async exchangeToken(code) {
    const response = await fetch(`${this.baseURL}/callback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        platform: 'meta',
        code: code,
        redirect_uri: 'http://localhost:3010/auth-callback'
      })
    });

    if (!response.ok) {
      throw new Error('Token exchange failed');
    }

    const tokenData = await response.json();
    
    // 保存 token
    localStorage.setItem('meta_access_token', tokenData.access_token);
    localStorage.setItem('meta_token_expires', Date.now() + tokenData.expires_in * 1000);
    
    return tokenData;
  }

  async getAdAccounts() {
    const accessToken = localStorage.getItem('meta_access_token');
    if (!accessToken) {
      throw new Error('Not authenticated');
    }

    const response = await fetch(
      `${this.baseURL}/meta/accounts?access_token=${accessToken}`
    );

    if (!response.ok) {
      throw new Error('Failed to get ad accounts');
    }

    return await response.json();
  }

  isAuthenticated() {
    const token = localStorage.getItem('meta_access_token');
    const expires = localStorage.getItem('meta_token_expires');
    
    if (!token || !expires) {
      return false;
    }

    return Date.now() < parseInt(expires);
  }

  disconnect() {
    localStorage.removeItem('meta_access_token');
    localStorage.removeItem('meta_token_expires');
  }
}

// 使用示例
const metaAuth = new MetaAuthService();

// 连接按钮点击事件
document.getElementById('connectMetaBtn').addEventListener('click', async () => {
  try {
    const tokenData = await metaAuth.connect();
    console.log('连接成功!', tokenData);
    
    // 获取广告账户
    const accounts = await metaAuth.getAdAccounts();
    console.log('广告账户:', accounts);
    
    // 更新 UI
    updateUIAfterConnect(accounts);
  } catch (error) {
    console.error('连接失败:', error);
    alert('连接失败: ' + error.message);
  }
});
```

### 2. OAuth 回调页面 (`/auth-callback.html`)

```html
<!DOCTYPE html>
<html>
<head>
  <title>授权回调</title>
</head>
<body>
  <script>
    // 从 URL 获取参数
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    const error = urlParams.get('error');
    const errorDescription = urlParams.get('error_description');

    if (code) {
      // 成功获取授权码，发送给父窗口
      window.opener.postMessage({
        type: 'oauth_callback',
        platform: 'meta',
        code: code,
        state: state
      }, window.location.origin);
      
      // 显示成功消息
      document.body.innerHTML = '<h2>授权成功！正在处理...</h2>';
      
      // 3秒后关闭窗口
      setTimeout(() => window.close(), 3000);
    } else if (error) {
      // 授权失败
      window.opener.postMessage({
        type: 'oauth_error',
        platform: 'meta',
        error: error,
        error_description: errorDescription
      }, window.location.origin);
      
      document.body.innerHTML = `<h2>授权失败</h2><p>${errorDescription || error}</p>`;
      setTimeout(() => window.close(), 5000);
    }
  </script>
</body>
</html>
```

## 测试

### 运行单元测试

```bash
cd /Users/micolin/Documents/MProjects/ANIFORCE/ANIMAGUS/backend
python scripts/test_meta_adapter.py
```

### 使用 Postman 测试

1. **获取授权 URL**:
   ```
   POST http://localhost:8000/api/v1/platform-auth/meta/connect
   ```

2. **在浏览器中访问返回的 `auth_url`**

3. **授权后获取 code，调用回调接口**:
   ```
   POST http://localhost:8000/api/v1/platform-auth/callback
   Body: {
     "platform": "meta",
     "code": "从 URL 获取的 code",
     "redirect_uri": "http://localhost:3010/auth-callback"
   }
   ```

4. **使用返回的 access_token 获取广告账户**:
   ```
   GET http://localhost:8000/api/v1/platform-auth/meta/accounts?access_token=YOUR_TOKEN
   ```

## 常见问题

### 1. 如何获取 Meta App ID 和 App Secret？

1. 访问 [Facebook Developers](https://developers.facebook.com/)
2. 创建应用 → 选择"商务"类型
3. 在应用设置中找到 App ID 和 App Secret
4. 添加 Marketing API 产品
5. 配置 OAuth 重定向 URI: `http://localhost:3010/auth-callback`

### 2. Token 过期怎么办？

Meta 长期 token 有效期为 60 天。建议：
- 在数据库中记录 token 过期时间
- 实现自动刷新机制
- 过期前提醒用户重新授权

### 3. 如何处理多个广告账户？

```javascript
const accounts = await metaAuth.getAdAccounts();

// 让用户选择账户
const selectedAccount = accounts[0];

// 保存选中的账户 ID
localStorage.setItem('meta_ad_account_id', selectedAccount.id);
```

### 4. 生产环境部署注意事项

1. 使用 HTTPS
2. 配置正确的 OAuth 回调域名
3. 加密存储 access_token
4. 实现 token 刷新机制
5. 添加请求速率限制
6. 记录详细的审计日志

## 架构优势

1. **统一接口**: 所有平台适配器继承自 `BaseAdapter`，接口一致
2. **易于扩展**: 添加新平台只需实现适配器类
3. **类型安全**: 使用 Pydantic 模型验证请求/响应
4. **错误处理**: 完善的异常处理和日志记录
5. **可测试**: 提供完整的单元测试套件

## 下一步

- [ ] 实现 Google Ads 适配器
- [ ] 实现 TikTok Ads 适配器
- [ ] 添加 Token 数据库存储
- [ ] 实现 Token 自动刷新
- [ ] 添加 API 速率限制
- [ ] 实现 Webhook 事件处理

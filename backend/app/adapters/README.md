# 广告平台适配器架构

## 概述

本模块提供了多渠道广告平台的统一接口封装，支持 Meta (Facebook/Instagram)、Google Ads、TikTok Ads 等平台的 OAuth 授权和广告管理功能。

## 架构设计

### 基类 `BaseAdapter`

所有平台适配器继承自 `BaseAdapter`，定义了统一的接口规范：

- **认证模块**: OAuth 授权、Token 管理、账户获取
- **Campaign 管理**: 创建、更新、状态管理、预算管理
- **AdSet 管理**: 创建广告组、定向设置
- **Creative 管理**: 素材上传、创意创建、广告创建
- **数据获取**: 广告数据洞察、性能指标

### 平台适配器

#### MetaAdsAdapter

Meta (Facebook/Instagram) 广告平台适配器，基于 Meta Marketing API v19.0。

**配置参数**:
```python
config = {
    'api_version': 'v19.0',
    'app_id': 'YOUR_META_APP_ID',
    'app_secret': 'YOUR_META_APP_SECRET'
}
```

**支持功能**:
- OAuth 2.0 授权流程
- 短期/长期 Token 转换
- 广告账户管理
- Campaign/AdSet/Creative/Ad 完整生命周期管理
- 图片/视频素材上传
- 广告数据洞察获取

#### GoogleAdsAdapter (待实现)

Google Ads 平台适配器。

#### TikTokAdsAdapter (待实现)

TikTok Ads 平台适配器。

## 使用示例

### 1. OAuth 授权流程

```python
from app.adapters import MetaAdsAdapter

# 初始化适配器
config = {
    'api_version': 'v19.0',
    'app_id': 'YOUR_APP_ID',
    'app_secret': 'YOUR_APP_SECRET'
}
adapter = MetaAdsAdapter(config)

# 生成授权 URL
auth_url = adapter.get_oauth_url(
    redirect_uri='http://localhost:3010/auth-callback',
    state='random_state_string'
)

# 用户授权后，用 code 换取 token
token_data = await adapter.exchange_code_for_token(
    code='authorization_code',
    redirect_uri='http://localhost:3010/auth-callback'
)

# 获取长期 token（60天有效期）
long_lived_token = await adapter.get_long_lived_token(
    token_data['access_token']
)

# 设置访问令牌
adapter.set_access_token(long_lived_token['access_token'])
```

### 2. 获取广告账户

```python
# 获取用户的广告账户列表
ad_accounts = await adapter.get_ad_accounts()

# 设置当前操作的广告账户
adapter.set_ad_account(ad_accounts[0]['id'])
```

### 3. 创建广告系列

```python
# 创建 Campaign
campaign = await adapter.create_campaign({
    'name': 'Test Campaign',
    'objective': 'OUTCOME_SALES',
    'status': 'PAUSED',
    'daily_budget': 10000  # $100.00 (单位：分)
})

# 创建 AdSet
adset = await adapter.create_adset(campaign['id'], {
    'name': 'Test AdSet',
    'daily_budget': 5000,
    'targeting': {
        'geo_locations': {'countries': ['US']},
        'age_min': 25,
        'age_max': 34,
        'genders': [2]  # 1=male, 2=female, 0=all
    },
    'optimization_goal': 'OFFSITE_CONVERSIONS',
    'billing_event': 'IMPRESSIONS'
})
```

### 4. 上传素材并创建广告

```python
# 上传图片
image = await adapter.upload_image('/path/to/image.jpg')

# 创建 Creative
creative = await adapter.create_creative({
    'name': 'Test Creative',
    'object_story_spec': {
        'page_id': 'YOUR_PAGE_ID',
        'link_data': {
            'image_hash': image['images']['image.jpg']['hash'],
            'link': 'https://example.com',
            'message': 'Check this out!',
            'name': 'Headline',
            'description': 'Description',
            'call_to_action': {
                'type': 'LEARN_MORE'
            }
        }
    }
})

# 创建 Ad
ad = await adapter.create_ad(adset['id'], creative['id'], {
    'name': 'Test Ad',
    'status': 'PAUSED'
})
```

### 5. 获取广告数据

```python
# 获取 Campaign 数据洞察
insights = await adapter.get_campaign_insights(campaign['id'], {
    'since': '2026-04-01',
    'until': '2026-04-06'
})

print(f"Impressions: {insights['data'][0]['impressions']}")
print(f"Clicks: {insights['data'][0]['clicks']}")
print(f"Spend: ${insights['data'][0]['spend']}")
```

### 6. 管理广告状态

```python
# 启动广告系列
await adapter.update_campaign_status(campaign['id'], 'ACTIVE')

# 暂停广告系列
await adapter.update_campaign_status(campaign['id'], 'PAUSED')

# 更新预算
await adapter.update_budget(campaign['id'], 20000, budget_type='daily')
```

## API 路由

### 平台授权路由 (`/api/v1/platform-auth`)

#### POST `/{platform}/connect`
获取 OAuth 授权 URL

**请求**:
- `platform`: 平台类型 (meta/google/tiktok)

**响应**:
```json
{
  "auth_url": "https://www.facebook.com/v19.0/dialog/oauth?...",
  "state": "random_state_string"
}
```

#### POST `/callback`
处理 OAuth 回调，换取 access_token

**请求**:
```json
{
  "platform": "meta",
  "code": "authorization_code",
  "redirect_uri": "http://localhost:3010/auth-callback",
  "state": "random_state_string"
}
```

**响应**:
```json
{
  "access_token": "xxx",
  "token_type": "bearer",
  "expires_in": 5183944,
  "refresh_token": null
}
```

#### GET `/{platform}/accounts`
获取广告账户列表

**请求参数**:
- `platform`: 平台类型
- `access_token`: 访问令牌

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

## 环境配置

在 `.env` 文件中配置平台凭证：

```bash
# Meta (Facebook) Ads
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret

# Google Ads
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# TikTok Ads
TIKTOK_APP_ID=your_tiktok_app_id
TIKTOK_APP_SECRET=your_tiktok_app_secret

# OAuth 回调地址
OAUTH_REDIRECT_URI=http://localhost:3010/auth-callback
```

## 扩展新平台

要添加新的广告平台支持：

1. 创建新的适配器类继承 `BaseAdapter`
2. 实现所有抽象方法
3. 在 `__init__.py` 中导出
4. 在 `platform_auth.py` 的 `get_adapter()` 函数中添加平台支持
5. 在 `settings.py` 中添加平台配置项

示例：

```python
from .base import BaseAdapter

class NewPlatformAdapter(BaseAdapter):
    def __init__(self, config: Dict[str, Any]):
        super().__init__('new_platform', config)
        # 初始化平台特定配置
    
    def get_oauth_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        # 实现 OAuth URL 生成
        pass
    
    # 实现其他抽象方法...
```

## 注意事项

1. **Token 安全**: 所有 access_token 应加密存储在数据库中，不要硬编码或记录在日志中
2. **错误处理**: 所有 API 调用都应包含适当的错误处理和重试逻辑
3. **速率限制**: 注意各平台的 API 速率限制，实现请求节流
4. **Token 刷新**: 实现 token 过期自动刷新机制
5. **日志记录**: 使用 logger 记录关键操作和错误信息

## 依赖

```
aiohttp>=3.9.0  # 异步 HTTP 客户端
```

## 参考文档

- [Meta Marketing API](https://developers.facebook.com/docs/marketing-apis)
- [Google Ads API](https://developers.google.com/google-ads/api/docs/start)
- [TikTok Marketing API](https://ads.tiktok.com/marketing_api/docs)

"""
测试 Meta Ads 适配器
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters import MetaAdsAdapter


async def test_oauth_url():
    """测试 OAuth URL 生成"""
    print("=" * 60)
    print("测试 1: OAuth URL 生成")
    print("=" * 60)
    
    config = {
        'api_version': 'v19.0',
        'app_id': 'TEST_APP_ID',
        'app_secret': 'TEST_APP_SECRET'
    }
    
    adapter = MetaAdsAdapter(config)
    
    auth_url = adapter.get_oauth_url(
        redirect_uri='http://localhost:3010/auth-callback',
        state='test_state_123'
    )
    
    print(f"生成的 OAuth URL:")
    print(auth_url)
    print()
    
    # 验证 URL 包含必要参数
    assert 'client_id=TEST_APP_ID' in auth_url
    assert 'redirect_uri=http://localhost:3010/auth-callback' in auth_url
    assert 'state=test_state_123' in auth_url
    assert 'scope=ads_management,ads_read,business_management' in auth_url
    
    print("✓ OAuth URL 生成成功")
    print()


async def test_adapter_initialization():
    """测试适配器初始化"""
    print("=" * 60)
    print("测试 2: 适配器初始化")
    print("=" * 60)
    
    config = {
        'api_version': 'v19.0',
        'app_id': 'TEST_APP_ID',
        'app_secret': 'TEST_APP_SECRET'
    }
    
    adapter = MetaAdsAdapter(config)
    
    assert adapter.platform_name == 'meta'
    assert adapter.api_version == 'v19.0'
    assert adapter.app_id == 'TEST_APP_ID'
    assert adapter.app_secret == 'TEST_APP_SECRET'
    assert adapter.base_url == 'https://graph.facebook.com/v19.0'
    assert adapter.access_token is None
    assert adapter.ad_account_id is None
    
    print("✓ 适配器初始化成功")
    print(f"  - 平台名称: {adapter.platform_name}")
    print(f"  - API 版本: {adapter.api_version}")
    print(f"  - Base URL: {adapter.base_url}")
    print()


async def test_token_and_account_setting():
    """测试 Token 和账户设置"""
    print("=" * 60)
    print("测试 3: Token 和账户设置")
    print("=" * 60)
    
    config = {
        'api_version': 'v19.0',
        'app_id': 'TEST_APP_ID',
        'app_secret': 'TEST_APP_SECRET'
    }
    
    adapter = MetaAdsAdapter(config)
    
    # 设置 access token
    adapter.set_access_token('test_access_token_123')
    assert adapter.access_token == 'test_access_token_123'
    print("✓ Access Token 设置成功")
    
    # 设置广告账户（不带 act_ 前缀）
    adapter.set_ad_account('123456789')
    assert adapter.ad_account_id == 'act_123456789'
    print("✓ 广告账户设置成功（自动添加 act_ 前缀）")
    
    # 设置广告账户（已有 act_ 前缀）
    adapter.set_ad_account('act_987654321')
    assert adapter.ad_account_id == 'act_987654321'
    print("✓ 广告账户设置成功（保持 act_ 前缀）")
    print()


async def test_config_validation():
    """测试配置验证"""
    print("=" * 60)
    print("测试 4: 配置验证")
    print("=" * 60)
    
    # 缺少必需配置项应该抛出异常
    try:
        config = {
            'api_version': 'v19.0',
            'app_id': 'TEST_APP_ID'
            # 缺少 app_secret
        }
        adapter = MetaAdsAdapter(config)
        print("✗ 应该抛出配置验证异常")
    except ValueError as e:
        print(f"✓ 配置验证成功: {e}")
    print()


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Meta Ads 适配器测试套件")
    print("=" * 60 + "\n")
    
    try:
        await test_adapter_initialization()
        await test_oauth_url()
        await test_token_and_account_setting()
        await test_config_validation()
        
        print("=" * 60)
        print("所有测试通过 ✓")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())

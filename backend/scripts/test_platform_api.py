"""
测试 Google 和 Meta 广告平台 API 对接
运行前需要配置真实的 API 凭证
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.connectors.google_adapter import GoogleAdsAdapter
from app.connectors.meta_adapter import MetaAdsAdapter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_meta_connection():
    """测试 Meta 广告平台连接"""
    print("\n" + "="*60)
    print("测试 Meta (Facebook) 广告平台 API 连接")
    print("="*60)

    # TODO: 替换为你的真实凭证
    config = {
        'api_version': 'v19.0',
        'app_id': 'YOUR_META_APP_ID',  # 替换为真实的 App ID
        'app_secret': 'YOUR_META_APP_SECRET'  # 替换为真实的 App Secret
    }

    adapter = MetaAdsAdapter(config)

    # 测试 1: 生成 OAuth URL
    print("\n[测试 1] 生成 OAuth 授权 URL")
    try:
        oauth_url = adapter.get_oauth_url(
            redirect_uri='http://localhost:3013/auth-callback',
            state='test_state_123'
        )
        print(f"✓ OAuth URL 生成成功:")
        print(f"  {oauth_url}")
        print("\n请在浏览器中打开此 URL 进行授权")
    except Exception as e:
        print(f"✗ 失败: {e}")
        return False

    # 测试 2: 如果有 access_token，测试获取广告账户
    access_token = input("\n请输入你的 Meta Access Token (如果没有请按回车跳过): ").strip()

    if access_token:
        adapter.access_token = access_token

        print("\n[测试 2] 获取广告账户列表")
        try:
            accounts = await adapter.get_ad_accounts()
            print(f"✓ 成功获取 {len(accounts)} 个广告账户:")
            for acc in accounts:
                print(f"  - {acc.get('name')} (ID: {acc.get('id')})")
                print(f"    状态: {acc.get('account_status')}, 货币: {acc.get('currency')}")

            if accounts:
                # 设置第一个账户进行后续测试
                adapter.set_ad_account(accounts[0]['id'])
                print(f"\n✓ 已设置当前账户: {accounts[0]['id']}")
                return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            return False
    else:
        print("\n⚠ 跳过账户测试（需要 Access Token）")
        return None


async def test_google_connection():
    """测试 Google 广告平台连接"""
    print("\n" + "="*60)
    print("测试 Google Ads API 连接")
    print("="*60)

    # TODO: 替换为你的真实凭证
    config = {
        "client_id": "YOUR_GOOGLE_CLIENT_ID",  # 替换
        "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",  # 替换
        "developer_token": "YOUR_DEVELOPER_TOKEN",  # 替换
        "refresh_token": "YOUR_REFRESH_TOKEN",  # 替换（如果有）
        "customer_id": "123-456-7890",  # 替换为你的客户 ID
        "api_version": "v15"
    }

    adapter = GoogleAdsAdapter(config)

    # 测试 1: 生成 OAuth URL
    print("\n[测试 1] Google OAuth 授权流程")
    oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={config['client_id']}&"
        f"redirect_uri=http://localhost:3013/auth-callback&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/adwords&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    print(f"✓ OAuth URL:")
    print(f"  {oauth_url}")
    print("\n请在浏览器中打开此 URL 进行授权")

    # 测试 2: 如果有 refresh_token，测试刷新 access_token
    if config['refresh_token'] != "YOUR_REFRESH_TOKEN":
        print("\n[测试 2] 刷新 Access Token")
        try:
            access_token = await adapter.refresh_access_token()
            print(f"✓ Access Token 刷新成功")
            print(f"  Token: {access_token[:20]}...")
            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            return False
    else:
        print("\n⚠ 跳过 Token 刷新测试（需要配置 refresh_token）")
        return None


async def test_api_endpoints():
    """测试后端 API 端点"""
    print("\n" + "="*60)
    print("测试后端 API 端点")
    print("="*60)

    import aiohttp

    base_url = "http://localhost:8000/api/v1/platform"

    async with aiohttp.ClientSession() as session:
        # 测试 1: 获取 Meta OAuth URL
        print("\n[测试 1] 获取 Meta OAuth URL")
        try:
            async with session.post(f"{base_url}/connect?platform=meta") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ 成功获取 OAuth URL")
                    print(f"  State: {data['state']}")
                    print(f"  URL: {data['auth_url'][:80]}...")
                else:
                    print(f"✗ 失败: HTTP {resp.status}")
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            print("  请确保后端服务已启动: cd backend && uvicorn app.main:app --reload")

        # 测试 2: 获取 Google OAuth URL
        print("\n[测试 2] 获取 Google OAuth URL")
        try:
            async with session.post(f"{base_url}/connect?platform=google") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ 成功获取 OAuth URL")
                    print(f"  State: {data['state']}")
                    print(f"  URL: {data['auth_url'][:80]}...")
                else:
                    print(f"✗ 失败: HTTP {resp.status}")
        except Exception as e:
            print(f"✗ 连接失败: {e}")

        # 测试 3: 添加测试账号
        print("\n[测试 3] 添加测试账号")
        try:
            async with session.post(f"{base_url}/accounts/test?platform=meta") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ 成功添加测试账号")
                    print(f"  ID: {data['id']}")
                    print(f"  平台: {data['platform']}")
                    print(f"  账号名: {data['account_name']}")
                else:
                    print(f"✗ 失败: HTTP {resp.status}")
        except Exception as e:
            print(f"✗ 连接失败: {e}")

        # 测试 4: 获取已连接账号列表
        print("\n[测试 4] 获取已连接账号列表")
        try:
            async with session.get(f"{base_url}/accounts") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✓ 成功获取账号列表 ({len(data)} 个账号)")
                    for acc in data:
                        print(f"  - {acc['account_name']} ({acc['platform']})")
                else:
                    print(f"✗ 失败: HTTP {resp.status}")
        except Exception as e:
            print(f"✗ 连接失败: {e}")


async def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("ANIMAGUS 广告平台 API 对接测试")
    print("="*60)

    print("\n请选择测试模式:")
    print("1. 测试 Meta (Facebook) 广告平台连接")
    print("2. 测试 Google Ads 平台连接")
    print("3. 测试后端 API 端点")
    print("4. 运行所有测试")

    choice = input("\n请输入选项 (1-4): ").strip()

    if choice == "1":
        await test_meta_connection()
    elif choice == "2":
        await test_google_connection()
    elif choice == "3":
        await test_api_endpoints()
    elif choice == "4":
        await test_api_endpoints()
        await test_meta_connection()
        await test_google_connection()
    else:
        print("无效选项")

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

    print("\n📝 下一步操作:")
    print("1. 如果 API 端点测试失败，请确保后端服务已启动:")
    print("   cd /Users/PJlai/Desktop/ANIMAGUS_remote/backend")
    print("   uvicorn app.main:app --reload")
    print("\n2. 如果平台连接测试失败，请检查:")
    print("   - Meta: 在 https://developers.facebook.com/ 创建应用并获取凭证")
    print("   - Google: 在 https://console.cloud.google.com/ 创建项目并启用 Google Ads API")
    print("\n3. 将真实凭证填入此脚本的配置中")


if __name__ == "__main__":
    asyncio.run(main())

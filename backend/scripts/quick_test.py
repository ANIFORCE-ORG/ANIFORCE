"""
快速测试脚本 - 验证广告平台 API 凭证
"""

import asyncio
import aiohttp
import json


async def test_meta_api(access_token: str):
    """测试 Meta API 连接"""
    print("\n🔵 测试 Meta (Facebook) API...")

    url = "https://graph.facebook.com/v19.0/me/adaccounts"
    params = {
        'access_token': access_token,
        'fields': 'id,name,account_status,currency'
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    accounts = data.get('data', [])
                    print(f"✅ Meta API 连接成功！")
                    print(f"   找到 {len(accounts)} 个广告账户:")
                    for acc in accounts:
                        print(f"   - {acc['name']} (ID: {acc['id']})")
                        print(f"     状态: {acc.get('account_status')}, 货币: {acc.get('currency')}")
                    return True
                else:
                    error = await resp.text()
                    print(f"❌ Meta API 失败: {resp.status}")
                    print(f"   错误: {error}")
                    return False
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False


async def test_google_api(access_token: str, customer_id: str, developer_token: str):
    """测试 Google Ads API 连接"""
    print("\n🔴 测试 Google Ads API...")

    # 移除 customer_id 中的连字符
    customer_id = customer_id.replace('-', '')

    url = f"https://googleads.googleapis.com/v15/customers/{customer_id}/googleAds:search"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'developer-token': developer_token,
        'Content-Type': 'application/json'
    }

    # 简单查询：获取客户信息
    query = {
        "query": "SELECT customer.id, customer.descriptive_name FROM customer LIMIT 1"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=query) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Google Ads API 连接成功！")
                    if data.get('results'):
                        customer = data['results'][0]['customer']
                        print(f"   客户 ID: {customer.get('id')}")
                        print(f"   客户名称: {customer.get('descriptiveName')}")
                    return True
                else:
                    error = await resp.text()
                    print(f"❌ Google Ads API 失败: {resp.status}")
                    print(f"   错误: {error}")
                    return False
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False


async def test_backend_api():
    """测试后端 API"""
    print("\n🟢 测试后端 API 端点...")

    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        try:
            # 测试健康检查
            async with session.get(f"{base_url}/health") as resp:
                if resp.status == 200:
                    print(f"✅ 后端服务运行正常")
                else:
                    print(f"⚠️  后端服务响应异常: {resp.status}")
        except Exception as e:
            print(f"❌ 无法连接后端服务: {e}")
            print(f"   请确保后端已启动: uvicorn app.main:app --reload")
            return False

        try:
            # 测试平台连接端点
            async with session.post(f"{base_url}/api/v1/platform/connect?platform=meta") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ 平台连接 API 正常")
                    print(f"   生成的 OAuth URL: {data['auth_url'][:60]}...")
                    return True
                else:
                    print(f"⚠️  平台连接 API 异常: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ 平台连接 API 测试失败: {e}")
            return False


async def main():
    print("="*70)
    print("  ANIMAGUS 广告平台 API 快速测试")
    print("="*70)

    print("\n请选择测试类型:")
    print("1. 测试 Meta (Facebook) API 凭证")
    print("2. 测试 Google Ads API 凭证")
    print("3. 测试后端 API 服务")
    print("4. 测试所有")

    choice = input("\n请输入选项 (1-4): ").strip()

    if choice in ["1", "4"]:
        print("\n" + "-"*70)
        print("Meta API 测试")
        print("-"*70)
        access_token = input("请输入 Meta Access Token: ").strip()
        if access_token:
            await test_meta_api(access_token)
        else:
            print("⚠️  跳过 Meta 测试（未提供 Token）")

    if choice in ["2", "4"]:
        print("\n" + "-"*70)
        print("Google Ads API 测试")
        print("-"*70)
        access_token = input("请输入 Google Access Token: ").strip()
        customer_id = input("请输入 Customer ID (格式: 123-456-7890): ").strip()
        developer_token = input("请输入 Developer Token: ").strip()

        if access_token and customer_id and developer_token:
            await test_google_api(access_token, customer_id, developer_token)
        else:
            print("⚠️  跳过 Google 测试（未提供完整凭证）")

    if choice in ["3", "4"]:
        print("\n" + "-"*70)
        print("后端 API 测试")
        print("-"*70)
        await test_backend_api()

    print("\n" + "="*70)
    print("测试完成")
    print("="*70)

    print("\n📚 获取凭证指南:")
    print("\n【Meta (Facebook)】")
    print("1. 访问: https://developers.facebook.com/apps/")
    print("2. 创建应用 → 选择 'Business' 类型")
    print("3. 添加 'Marketing API' 产品")
    print("4. 在 Tools → Graph API Explorer 中生成 Access Token")
    print("5. 权限需要: ads_management, ads_read, business_management")

    print("\n【Google Ads】")
    print("1. 访问: https://console.cloud.google.com/")
    print("2. 创建项目 → 启用 Google Ads API")
    print("3. 创建 OAuth 2.0 凭证")
    print("4. 申请 Developer Token: https://ads.google.com/aw/apicenter")
    print("5. 使用 OAuth Playground 获取 Access Token")


if __name__ == "__main__":
    asyncio.run(main())

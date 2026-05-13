"""
演示 Meta OAuth 授权流程
注意：这是一个演示脚本，展示如何使用适配器
实际使用时应通过 API 接口调用
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters import MetaAdsAdapter


async def demo_oauth_flow():
    """演示完整的 OAuth 授权流程"""
    
    print("\n" + "=" * 70)
    print("Meta Ads OAuth 授权流程演示")
    print("=" * 70 + "\n")
    
    # 配置（实际使用时从环境变量读取）
    config = {
        'api_version': 'v19.0',
        'app_id': 'YOUR_META_APP_ID',  # 替换为真实的 App ID
        'app_secret': 'YOUR_META_APP_SECRET'  # 替换为真实的 App Secret
    }
    
    adapter = MetaAdsAdapter(config)
    
    # 步骤 1: 生成 OAuth 授权 URL
    print("步骤 1: 生成 OAuth 授权 URL")
    print("-" * 70)
    
    redirect_uri = 'http://localhost:3010/auth-callback'
    state = 'demo_state_12345'
    
    auth_url = adapter.get_oauth_url(redirect_uri, state)
    
    print(f"授权 URL: {auth_url}\n")
    print("请在浏览器中打开此 URL 进行授权")
    print("授权后会跳转到回调页面，从 URL 中获取 code 参数\n")
    
    # 步骤 2: 模拟用户授权（实际流程中这一步由用户在浏览器完成）
    print("步骤 2: 用户在浏览器中授权")
    print("-" * 70)
    print("用户点击授权后，Facebook 会重定向到:")
    print(f"{redirect_uri}?code=AUTHORIZATION_CODE&state={state}\n")
    
    # 步骤 3: 用授权码换取 Token（需要真实的授权码）
    print("步骤 3: 用授权码换取 Access Token")
    print("-" * 70)
    print("注意: 以下步骤需要真实的授权码才能执行\n")
    
    # 提示用户输入授权码（可选）
    print("如果您已经完成授权，可以输入授权码进行测试")
    print("否则请按 Enter 跳过实际 API 调用\n")
    
    code = input("请输入授权码 (或按 Enter 跳过): ").strip()
    
    if code:
        try:
            print("\n正在用授权码换取 Token...")
            token_data = await adapter.exchange_code_for_token(code, redirect_uri)
            
            print("✓ 成功获取 Access Token!")
            print(f"  Token 类型: {token_data.get('token_type', 'bearer')}")
            print(f"  过期时间: {token_data.get('expires_in', 0)} 秒")
            print(f"  Access Token: {token_data['access_token'][:20]}...\n")
            
            # 步骤 4: 获取长期 Token
            print("步骤 4: 将短期 Token 换成长期 Token (60天)")
            print("-" * 70)
            
            long_lived_token = await adapter.get_long_lived_token(token_data['access_token'])
            
            print("✓ 成功获取长期 Token!")
            print(f"  过期时间: {long_lived_token.get('expires_in', 0)} 秒 (约 {long_lived_token.get('expires_in', 0) // 86400} 天)")
            print(f"  Access Token: {long_lived_token['access_token'][:20]}...\n")
            
            # 步骤 5: 获取广告账户列表
            print("步骤 5: 获取广告账户列表")
            print("-" * 70)
            
            adapter.set_access_token(long_lived_token['access_token'])
            ad_accounts = await adapter.get_ad_accounts()
            
            print(f"✓ 找到 {len(ad_accounts)} 个广告账户:\n")
            
            for i, account in enumerate(ad_accounts, 1):
                print(f"{i}. {account['name']}")
                print(f"   ID: {account['id']}")
                print(f"   状态: {account.get('account_status', 'N/A')}")
                print(f"   货币: {account.get('currency', 'N/A')}")
                print(f"   已花费: {account.get('amount_spent', 'N/A')}")
                print()
            
            # 步骤 6: 设置广告账户
            if ad_accounts:
                print("步骤 6: 设置当前操作的广告账户")
                print("-" * 70)
                
                adapter.set_ad_account(ad_accounts[0]['id'])
                print(f"✓ 已设置广告账户: {ad_accounts[0]['name']}\n")
            
            print("=" * 70)
            print("授权流程演示完成！")
            print("=" * 70)
            print("\n现在您可以使用此适配器进行以下操作:")
            print("  - 创建 Campaign")
            print("  - 创建 AdSet")
            print("  - 上传素材")
            print("  - 创建广告")
            print("  - 获取数据洞察")
            
        except Exception as e:
            print(f"\n✗ 错误: {e}")
            print("\n可能的原因:")
            print("  1. 授权码已过期（授权码只能使用一次）")
            print("  2. App ID 或 App Secret 配置错误")
            print("  3. 回调地址不匹配")
            print("  4. 网络连接问题")
    else:
        print("\n跳过实际 API 调用")
        print("\n要完成真实的授权流程，请:")
        print("  1. 在 Facebook Developers 创建应用")
        print("  2. 配置正确的 App ID 和 App Secret")
        print("  3. 在浏览器中打开上面生成的授权 URL")
        print("  4. 授权后从回调 URL 获取 code")
        print("  5. 重新运行此脚本并输入 code")
    
    print("\n" + "=" * 70)
    print("演示结束")
    print("=" * 70 + "\n")


async def demo_api_usage():
    """演示如何通过 API 接口使用"""
    
    print("\n" + "=" * 70)
    print("通过 API 接口使用示例")
    print("=" * 70 + "\n")
    
    print("前端 JavaScript 代码示例:\n")
    
    print("""
// 1. 获取授权 URL
const response = await fetch('http://localhost:8000/api/v1/platform-auth/meta/connect', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' }
});

const { auth_url, state } = await response.json();

// 2. 打开授权窗口
window.open(auth_url, 'oauth_meta', 'width=600,height=700');

// 3. 监听回调
window.addEventListener('message', async (event) => {
  if (event.data.type === 'oauth_callback' && event.data.code) {
    // 4. 用 code 换取 token
    const tokenResponse = await fetch('http://localhost:8000/api/v1/platform-auth/callback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        platform: 'meta',
        code: event.data.code,
        redirect_uri: 'http://localhost:3010/auth-callback'
      })
    });
    
    const tokenData = await tokenResponse.json();
    localStorage.setItem('meta_access_token', tokenData.access_token);
    
    // 5. 获取广告账户
    const accountsResponse = await fetch(
      `http://localhost:8000/api/v1/platform-auth/meta/accounts?access_token=${tokenData.access_token}`
    );
    
    const accounts = await accountsResponse.json();
    console.log('广告账户:', accounts);
  }
});
""")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == '__main__':
    print("\n请选择演示模式:")
    print("1. OAuth 授权流程演示")
    print("2. API 接口使用示例")
    print("3. 两者都显示")
    
    choice = input("\n请输入选项 (1/2/3): ").strip()
    
    if choice == '1':
        asyncio.run(demo_oauth_flow())
    elif choice == '2':
        asyncio.run(demo_api_usage())
    elif choice == '3':
        asyncio.run(demo_oauth_flow())
        asyncio.run(demo_api_usage())
    else:
        print("无效的选项")

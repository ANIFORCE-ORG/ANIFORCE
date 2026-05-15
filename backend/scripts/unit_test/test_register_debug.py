"""调试注册接口的 bcrypt 问题"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
import httpx
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def test_register_debug():
    """调试注册流程"""
    print("=" * 70)
    print("调试注册接口 bcrypt 问题")
    print("=" * 70)
    
    # 测试数据
    test_data = {
        "name": "调试用户",
        "email": "debug_user@example.com",
        "password": "test123"
    }
    
    print(f"\n📋 测试数据:")
    print(f"   姓名: {test_data['name']}")
    print(f"   邮箱: {test_data['email']}")
    print(f"   密码: {test_data['password']}")
    print(f"   密码长度: {len(test_data['password'])}")
    print(f"   密码字节: {len(test_data['password'].encode('utf-8'))}")
    
    # 1. 本地测试 bcrypt
    print(f"\n1️⃣  本地测试 bcrypt...")
    try:
        hash_result = pwd_context.hash(test_data['password'])
        print(f"   ✅ 本地加密成功")
        print(f"   哈希: {hash_result[:50]}...")
    except Exception as e:
        print(f"   ❌ 本地加密失败: {e}")
        return
    
    # 2. 测试后端健康检查
    print(f"\n2️⃣  测试后端服务...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8010/health", timeout=5.0)
            if response.status_code == 200:
                health_data = response.json()
                print(f"   ✅ 后端服务正常")
                print(f"   Demo 模式: {health_data.get('demo_mode')}")
            else:
                print(f"   ❌ 后端服务异常: {response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ 无法连接后端: {e}")
            return
    
    # 3. 调用注册 API
    print(f"\n3️⃣  调用注册 API...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8010/api/v1/auth/register",
                json=test_data,
                timeout=10.0
            )
            
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 201:
                data = response.json()
                print(f"   ✅ 注册成功")
                print(f"   用户 ID: {data.get('data', {}).get('user', {}).get('id')}")
            else:
                print(f"   ❌ 注册失败")
                try:
                    error_data = response.json()
                    print(f"   错误响应: {error_data}")
                except:
                    print(f"   响应文本: {response.text}")
                
                print(f"\n   💡 请查看后端服务终端的 [DEBUG] 日志输出")
                print(f"   应该会显示密码的详细信息和具体错误")
                
        except Exception as e:
            print(f"   ❌ API 调用错误: {e}")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
    print("\n📝 下一步:")
    print("   1. 查看后端服务终端的 [DEBUG] 输出")
    print("   2. 确认密码长度和内容是否正常")
    print("   3. 查看具体的加密失败错误信息")

if __name__ == "__main__":
    asyncio.run(test_register_debug())

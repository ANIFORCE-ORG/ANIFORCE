"""测试注册 API 是否能正确写入数据库"""
import asyncio
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_session_maker
from app.models import User


async def test_register_api():
    """测试注册 API"""
    print("=" * 60)
    print("测试注册 API - 数据库写入验证")
    print("=" * 60)
    
    # 1. 准备测试数据
    test_email = "test_user_001@example.com"
    test_data = {
        "name": "测试用户001",
        "email": test_email,
        "password": "test123456"
    }
    
    print(f"\n1. 准备测试数据:")
    print(f"   姓名: {test_data['name']}")
    print(f"   邮箱: {test_data['email']}")
    print(f"   密码: {test_data['password']}")
    
    # 2. 调用注册 API
    print(f"\n2. 调用注册 API...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/auth/register",
                json=test_data,
                timeout=10.0
            )
            
            print(f"   状态码: {response.status_code}")
            print(f"   响应内容: {response.json()}")
            
            if response.status_code == 201:
                print("   ✅ 注册 API 调用成功")
            else:
                print(f"   ❌ 注册 API 调用失败: {response.json()}")
                return
                
        except Exception as e:
            print(f"   ❌ API 调用错误: {e}")
            print("\n提示: 请确保后端服务已启动 (python -m uvicorn app.main:app --reload)")
            return
    
    # 3. 等待一下，确保数据已写入
    print(f"\n3. 等待数据写入...")
    await asyncio.sleep(1)
    
    # 4. 直接查询数据库验证
    print(f"\n4. 查询数据库验证...")
    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == test_email)
        )
        user = result.scalar_one_or_none()
        
        if user:
            print(f"   ✅ 数据库中找到用户:")
            print(f"      ID: {user.id}")
            print(f"      姓名: {user.name}")
            print(f"      邮箱: {user.email}")
            print(f"      密码哈希: {user.password_hash[:20]}...")
            print(f"      创建时间: {user.created_at}")
        else:
            print(f"   ❌ 数据库中未找到用户")
            print(f"   可能原因:")
            print(f"   1. 事务未提交")
            print(f"   2. 数据库连接配置错误")
            print(f"   3. 表结构未创建")
    
    # 5. 测试重复注册
    print(f"\n5. 测试重复注册（应该失败）...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/auth/register",
                json=test_data,
                timeout=10.0
            )
            
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 400:
                error_detail = response.json().get("detail", "")
                print(f"   ✅ 正确返回错误: {error_detail}")
            else:
                print(f"   ❌ 应该返回 400 错误，但返回了: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ API 调用错误: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_register_api())

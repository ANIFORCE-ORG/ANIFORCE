"""测试完整的注册流程（需要后端服务运行）"""
import sys
import os
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
import httpx
from sqlalchemy import select
from app.config.database import get_session_maker
from app.models import User


async def test_register_flow():
    """测试完整的注册流程"""
    print("=" * 70)
    print("测试完整的注册流程（前后端串联）")
    print("=" * 70)
    
    # 测试数据
    test_email = "flow_test_user@example.com"
    test_data = {
        "name": "流程测试用户",
        "email": test_email,
        "password": "test123456"
    }
    
    print(f"\n📋 测试数据:")
    print(f"   姓名: {test_data['name']}")
    print(f"   邮箱: {test_data['email']}")
    print(f"   密码: {test_data['password']}")
    
    # 1. 清理旧数据
    print(f"\n1️⃣  清理旧测试数据...")
    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == test_email)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            await session.delete(existing_user)
            await session.commit()
            print(f"   ✅ 已删除旧用户")
        else:
            print(f"   ℹ️  无旧数据")
    
    # 2. 测试后端健康检查
    print(f"\n2️⃣  测试后端服务连接...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://localhost:8010/health", timeout=5.0)
            if response.status_code == 200:
                health_data = response.json()
                print(f"   ✅ 后端服务正常")
                print(f"   Demo 模式: {health_data.get('demo_mode', 'unknown')}")
            else:
                print(f"   ❌ 后端服务异常: {response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ 无法连接后端服务: {e}")
            print(f"   💡 请先启动后端服务: python -m uvicorn app.main:app --reload --port 8000")
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
            print(f"   响应头: {dict(response.headers)}")
            
            if response.status_code == 201:
                data = response.json()
                print(f"   ✅ 注册 API 调用成功")
                print(f"   响应结构:")
                print(f"      success: {data.get('success')}")
                print(f"      data: {data.get('data', {}).keys() if data.get('data') else None}")
                print(f"      message: {data.get('message')}")
                
                if data.get('data'):
                    user_data = data['data'].get('user', {})
                    print(f"   用户信息:")
                    print(f"      ID: {user_data.get('id')}")
                    print(f"      姓名: {user_data.get('name')}")
                    print(f"      邮箱: {user_data.get('email')}")
                    print(f"   Token: {data['data'].get('access_token', '')[:30]}...")
            else:
                print(f"   ❌ 注册失败")
                print(f"   响应内容: {response.text}")
                return
                
        except Exception as e:
            print(f"   ❌ API 调用错误: {e}")
            return
    
    # 4. 等待数据写入
    print(f"\n4️⃣  等待数据写入...")
    await asyncio.sleep(1)
    
    # 5. 验证数据库
    print(f"\n5️⃣  验证数据库...")
    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == test_email)
        )
        user = result.scalar_one_or_none()
        
        if user:
            print(f"   ✅ 数据库中找到用户")
            print(f"      ID: {user.id}")
            print(f"      姓名: {user.name}")
            print(f"      邮箱: {user.email}")
            print(f"      创建时间: {user.created_at}")
        else:
            print(f"   ❌ 数据库中未找到用户")
            print(f"   ⚠️  可能原因:")
            print(f"      1. 事务未提交（检查 get_db() 函数）")
            print(f"      2. Demo 模式开启（不写入真实数据库）")
            print(f"      3. 数据库连接配置错误")
    
    # 6. 测试重复注册
    print(f"\n6️⃣  测试重复注册...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8010/api/v1/auth/register",
                json=test_data,
                timeout=10.0
            )
            
            if response.status_code == 400:
                error_data = response.json()
                print(f"   ✅ 正确返回 400 错误")
                print(f"   错误信息: {error_data.get('detail', error_data)}")
            else:
                print(f"   ❌ 应该返回 400，实际返回: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ API 调用错误: {e}")
    
    # 7. 测试登录
    print(f"\n7️⃣  测试使用新账号登录...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8010/api/v1/auth/login",
                json={
                    "email": test_email,
                    "password": test_data["password"]
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                print(f"   ✅ 登录成功")
                data = response.json()
                if data.get('data'):
                    print(f"   Token: {data['data'].get('access_token', '')[:30]}...")
            else:
                print(f"   ❌ 登录失败: {response.status_code}")
                print(f"   响应: {response.text}")
                
        except Exception as e:
            print(f"   ❌ 登录错误: {e}")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
    
    print("\n📊 诊断结论:")
    print("   如果步骤 3 成功但步骤 5 失败 → 事务未提交问题")
    print("   如果步骤 2 失败 → 后端服务未启动")
    print("   如果步骤 3 失败 → API 路由或逻辑问题")
    print("   如果步骤 6 失败 → 重复邮箱检查问题")
    print("   如果步骤 7 失败 → 密码验证问题")


if __name__ == "__main__":
    asyncio.run(test_register_flow())

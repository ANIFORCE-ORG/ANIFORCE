"""直接测试数据库写入（不需要启动后端服务）"""
import asyncio
from passlib.context import CryptContext
from sqlalchemy import select
from app.config.database import get_session_maker, get_engine, Base
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def test_database_write():
    """直接测试数据库写入"""
    print("=" * 60)
    print("直接测试数据库写入（不需要后端服务）")
    print("=" * 60)
    
    # 1. 创建表结构
    print("\n1. 初始化数据库表结构...")
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("   ✅ 表结构创建完成")
    
    # 2. 准备测试数据
    test_email = "direct_test_user@example.com"
    test_name = "直接测试用户"
    test_password = "test123456"
    
    print(f"\n2. 准备测试数据:")
    print(f"   姓名: {test_name}")
    print(f"   邮箱: {test_email}")
    print(f"   密码: {test_password}")
    
    # 3. 测试写入（模拟注册流程）
    print(f"\n3. 测试写入数据库...")
    session_maker = get_session_maker()
    
    async with session_maker() as session:
        try:
            # 检查用户是否已存在
            result = await session.execute(
                select(User).where(User.email == test_email)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print(f"   ⚠️  用户已存在，先删除...")
                await session.delete(existing_user)
                await session.commit()
            
            # 创建新用户
            password_hash = pwd_context.hash(test_password)
            user = User(
                email=test_email,
                password_hash=password_hash,
                name=test_name
            )
            
            session.add(user)
            await session.flush()  # 发送到数据库
            
            print(f"   📝 用户对象已创建:")
            print(f"      ID: {user.id}")
            print(f"      姓名: {user.name}")
            print(f"      邮箱: {user.email}")
            
            # 提交事务
            await session.commit()
            print(f"   ✅ 事务已提交")
            
        except Exception as e:
            await session.rollback()
            print(f"   ❌ 写入失败: {e}")
            return
    
    # 4. 验证数据是否真的写入了
    print(f"\n4. 验证数据是否持久化...")
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
            print(f"      密码哈希: {user.password_hash[:30]}...")
            print(f"      创建时间: {user.created_at}")
            print(f"      更新时间: {user.updated_at}")
        else:
            print(f"   ❌ 数据库中未找到用户")
            print(f"   说明: 数据未持久化，可能是事务未提交")
    
    # 5. 测试密码验证
    print(f"\n5. 测试密码验证...")
    if user:
        is_valid = pwd_context.verify(test_password, user.password_hash)
        if is_valid:
            print(f"   ✅ 密码验证成功")
        else:
            print(f"   ❌ 密码验证失败")
    
    # 6. 测试重复邮箱检查
    print(f"\n6. 测试重复邮箱检查...")
    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.email == test_email)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"   ✅ 能够检测到重复邮箱")
        else:
            print(f"   ❌ 无法检测到重复邮箱")
    
    # 7. 查询所有用户
    print(f"\n7. 查询数据库中所有用户...")
    async with session_maker() as session:
        result = await session.execute(select(User))
        all_users = result.scalars().all()
        
        print(f"   数据库中共有 {len(all_users)} 个用户:")
        for u in all_users:
            print(f"   - {u.name} ({u.email})")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n结论:")
    print("如果步骤 4 能找到用户，说明数据库写入正常")
    print("如果步骤 4 找不到用户，说明事务未提交，需要检查 get_db() 函数")


if __name__ == "__main__":
    asyncio.run(test_database_write())

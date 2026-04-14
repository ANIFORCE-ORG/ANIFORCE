"""测试Platform枚举转换"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.campaign import Platform, CampaignStatus
from app.config.database import get_db
from app.repositories.impl.sqlite_campaign_repo import SqliteCampaignRepository
from sqlalchemy import select
from app.models import Campaign


async def test_platform_enum():
    """测试Platform枚举查询"""
    print("开始测试Platform枚举...")
    
    # 测试枚举值转换
    try:
        google = Platform("Google")
        print(f"✅ Platform('Google') = {google}")
        print(f"   值: {google.value}")
    except Exception as e:
        print(f"❌ Platform('Google') 失败: {e}")
    
    try:
        tiktok = Platform("TikTok")
        print(f"✅ Platform('TikTok') = {tiktok}")
    except Exception as e:
        print(f"❌ Platform('TikTok') 失败: {e}")
    
    try:
        meta = Platform("Meta")
        print(f"✅ Platform('Meta') = {meta}")
    except Exception as e:
        print(f"❌ Platform('Meta') 失败: {e}")
    
    # 测试数据库查询
    print("\n测试数据库查询...")
    async for session in get_db():
        try:
            repo = SqliteCampaignRepository(session)
            
            # 查询第一条campaign记录
            result = await session.execute(
                select(Campaign).limit(1)
            )
            campaign = result.scalar_one_or_none()
            
            if campaign:
                print(f"✅ 查询到campaign: {campaign.id}")
                print(f"   名称: {campaign.name}")
                print(f"   Platform对象: {campaign.platform}")
                print(f"   Platform类型: {type(campaign.platform)}")
                print(f"   Platform值: {campaign.platform.value}")
                print(f"   Status对象: {campaign.status}")
                print(f"   Status值: {campaign.status.value}")
                
                # 测试序列化
                campaign_dict = repo._to_dict(campaign)
                print(f"\n✅ 序列化成功:")
                print(f"   platform: {campaign_dict['platform']}")
                print(f"   status: {campaign_dict['status']}")
            else:
                print("❌ 没有找到campaign记录")
                
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            import traceback
            traceback.print_exc()
        
        break


if __name__ == "__main__":
    asyncio.run(test_platform_enum())

"""填充 Mock 数据到数据库"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_session_maker, Base, get_engine
from app.models import User, Project, Campaign, Material, Metric
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.campaign import Campaign, CampaignStatus
from app.models.material import Material, MaterialType, MaterialStatus
from app.models.metric import Metric
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_tables():
    """创建所有表（如果不存在）"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库表创建完成")


async def seed_data():
    """填充 Mock 数据"""
    async_session = get_session_maker()
    async with async_session() as session:
        # 1. 创建测试用户
        user = User(
            id="user_test_001",
            email="test@animagus.com",
            password_hash=pwd_context.hash("test123"),
            name="测试用户"
        )
        session.add(user)
        await session.flush()
        print(f"✅ 创建用户: {user.email}")
        
        # 2. 创建项目
        projects_data = [
            {
                "id": "proj_001",
                "name": "Candy Blast - 全球推广",
                "game_type": "休闲游戏",
                "target_market": "北美",
                "tags": '["休闲游戏", "三消", "北美"]',
                "total_budget": 80000.0,
                "spent": 52300.0,
                "status": ProjectStatus.ACTIVE,
                "manager": "李明",
                "start_date": datetime.now() - timedelta(days=45),
                "end_date": datetime.now() + timedelta(days=15),
            },
            {
                "id": "proj_002",
                "name": "Dragon Quest - 东南亚市场",
                "game_type": "RPG",
                "target_market": "东南亚",
                "tags": '["RPG", "魔幻", "东南亚"]',
                "total_budget": 120000.0,
                "spent": 85000.0,
                "status": ProjectStatus.ACTIVE,
                "manager": "王芳",
                "start_date": datetime.now() - timedelta(days=60),
                "end_date": datetime.now() + timedelta(days=30),
            },
            {
                "id": "proj_003",
                "name": "短剧《霸总的秘密》- 全球投放",
                "game_type": "短剧",
                "target_market": "全球",
                "tags": '["短剧", "霸总", "全球"]',
                "total_budget": 50000.0,
                "spent": 12000.0,
                "status": ProjectStatus.ACTIVE,
                "manager": "张伟",
                "start_date": datetime.now() - timedelta(days=10),
                "end_date": datetime.now() + timedelta(days=50),
            },
            {
                "id": "proj_game_001",
                "name": "Candy Blast 美加英投放",
                "game_type": "休闲游戏",
                "target_market": "北美+英国",
                "tags": '["休闲游戏", "三消", "欧美"]',
                "total_budget": 70000.0,
                "spent": 52300.0,
                "status": ProjectStatus.ACTIVE,
                "manager": "李明",
                "start_date": datetime.now() - timedelta(days=50),
                "end_date": datetime.now() + timedelta(days=10),
            },
            {
                "id": "proj_game_002",
                "name": "Candy Blast 东南亚测试",
                "game_type": "休闲游戏",
                "target_market": "东南亚",
                "tags": '["休闲游戏", "三消", "东南亚", "测试"]',
                "total_budget": 5000.0,
                "spent": 3200.0,
                "status": ProjectStatus.ACTIVE,
                "manager": "李明",
                "start_date": datetime.now() - timedelta(days=20),
                "end_date": datetime.now() + timedelta(days=10),
            },
            {
                "id": "proj_drama_001",
                "name": "DramaBox 北美推广",
                "game_type": "短剧",
                "target_market": "北美",
                "tags": '["短剧", "霸总", "北美"]',
                "total_budget": 150000.0,
                "spent": 86500.0,
                "status": ProjectStatus.ACTIVE,
                "manager": "张伟",
                "start_date": datetime.now() - timedelta(days=70),
                "end_date": datetime.now() + timedelta(days=20),
            },
            {
                "id": "proj_drama_002",
                "name": "DramaBox 澳洲测试",
                "game_type": "短剧",
                "target_market": "澳洲",
                "tags": '["短剧", "测试", "澳洲"]',
                "total_budget": 20000.0,
                "spent": 15600.0,
                "status": ProjectStatus.ACTIVE,
                "manager": "张伟",
                "start_date": datetime.now() - timedelta(days=50),
                "end_date": datetime.now() + timedelta(days=10),
            },
        ]
        
        projects = []
        for proj_data in projects_data:
            project = Project(user_id=user.id, **proj_data)
            session.add(project)
            projects.append(project)
        
        await session.flush()
        print(f"✅ 创建 {len(projects)} 个项目")
        
        # 3. 创建广告投放
        campaigns_data = [
            # 原有的广告投放
            {
                "id": "camp_g001",
                "project_id": "proj_game_001",
                "name": "CB_US_Android_Install_001",
                "platform": "Google",
                "budget": 30000.0,
                "spent": 22800.0,
                "status": CampaignStatus.RUNNING,
                "start_date": datetime.now() - timedelta(days=50),
                "end_date": datetime.now() + timedelta(days=10),
                "material_ids": '["mat_001", "mat_002"]',
            },
            {
                "id": "camp_g002",
                "project_id": "proj_game_001",
                "name": "CB_US_iOS_Install_001",
                "platform": "TikTok",
                "budget": 25000.0,
                "spent": 18900.0,
                "status": CampaignStatus.RUNNING,
                "start_date": datetime.now() - timedelta(days=45),
                "end_date": datetime.now() + timedelta(days=15),
                "material_ids": '["mat_001", "mat_003"]',
            },
            {
                "id": "camp_g003",
                "project_id": "proj_game_001",
                "name": "CB_UK_Android_Install_001",
                "platform": "Meta",
                "budget": 15000.0,
                "spent": 10600.0,
                "status": CampaignStatus.REVIEW,
                "start_date": datetime.now() - timedelta(days=20),
                "end_date": datetime.now() + timedelta(days=40),
                "material_ids": '["mat_002"]',
            },
            {
                "id": "camp_g004",
                "project_id": "proj_game_002",
                "name": "CB_SEA_Android_Test_001",
                "platform": "Google",
                "budget": 5000.0,
                "spent": 3200.0,
                "status": CampaignStatus.RUNNING,
                "start_date": datetime.now() - timedelta(days=20),
                "end_date": datetime.now() + timedelta(days=10),
                "material_ids": '["mat_001"]',
            },
            {
                "id": "camp_d001",
                "project_id": "proj_drama_001",
                "name": "DB_US_Hook_Install_001",
                "platform": "TikTok",
                "budget": 60000.0,
                "spent": 45200.0,
                "status": CampaignStatus.RUNNING,
                "start_date": datetime.now() - timedelta(days=70),
                "end_date": datetime.now() + timedelta(days=20),
                "material_ids": '["mat_006", "mat_007"]',
            },
            {
                "id": "camp_d002",
                "project_id": "proj_drama_001",
                "name": "DB_US_Romance_Install_001",
                "platform": "Meta",
                "budget": 45000.0,
                "spent": 32800.0,
                "status": CampaignStatus.RUNNING,
                "start_date": datetime.now() - timedelta(days=65),
                "end_date": datetime.now() + timedelta(days=25),
                "material_ids": '["mat_006", "mat_008"]',
            },
            {
                "id": "camp_d003",
                "project_id": "proj_drama_002",
                "name": "DB_AU_Drama_Install_001",
                "platform": "Google",
                "budget": 20000.0,
                "spent": 15600.0,
                "status": CampaignStatus.RUNNING,
                "start_date": datetime.now() - timedelta(days=50),
                "end_date": datetime.now() + timedelta(days=10),
                "material_ids": '["mat_007"]',
            },
            {
                "id": "camp_d004",
                "project_id": "proj_drama_001",
                "name": "DB_US_BossRomance_Install_001",
                "platform": "TikTok",
                "budget": 15000.0,
                "spent": 8500.0,
                "status": CampaignStatus.PAUSED,
                "start_date": datetime.now() - timedelta(days=20),
                "end_date": datetime.now() + timedelta(days=40),
                "material_ids": '["mat_008"]',
            },
        ]
        
        campaigns = []
        for camp_data in campaigns_data:
            campaign = Campaign(**camp_data)
            session.add(campaign)
            campaigns.append(campaign)
        
        await session.flush()
        print(f"✅ 创建 {len(campaigns)} 个广告投放")
        
        # 4. 创建素材（使用本地路径格式）
        materials_data = [
            {
                "id": "mat_001",
                "user_id": "user_test_001",
                "name": "Candy Blast - Boss 战高光",
                "type": MaterialType.FULL_VIDEO,
                "status": MaterialStatus.RUNNING,  # 投放中
                "url": "/images/creative_game_001.jpg",
                "thumbnail_url": "/images/creative_game_001.jpg",
                "ctr_estimate": 3.2,
                "tags": '["Boss挑战", "高奖励", "视觉冲击"]',
                "duration": 15,
                "file_size": 159532,
                "project_ids": '["proj_001"]',
                "campaign_ids": '["camp_g001", "camp_m001"]',
            },
            {
                "id": "mat_002",
                "user_id": "user_test_001",
                "name": "Candy Blast - 装备展示",
                "type": MaterialType.FULL_VIDEO,
                "status": MaterialStatus.RUNNING,  # 投放中
                "url": "/images/creative_game_002.jpg",
                "thumbnail_url": "/images/creative_game_002.jpg",
                "ctr_estimate": 2.8,
                "tags": '["装备展示", "稀有掉落", "收集欲"]',
                "duration": 12,
                "file_size": 174032,
                "project_ids": '["proj_001"]',
                "campaign_ids": '["camp_g001"]',
            },
            {
                "id": "mat_003",
                "user_id": "user_test_001",
                "name": "Candy Blast - PVP 对决",
                "type": MaterialType.FULL_VIDEO,
                "status": MaterialStatus.FATIGUE,  # 已疲劳
                "url": "/images/creative_game_003.jpg",
                "thumbnail_url": "/images/creative_game_003.jpg",
                "ctr_estimate": 3.5,
                "tags": '["PVP对决", "实时竞技", "高光时刻"]',
                "duration": 18,
                "file_size": 226690,
                "project_ids": '["proj_001"]',
                "campaign_ids": '["camp_m001"]',
            },
            {
                "id": "mat_004",
                "user_id": "user_test_001",
                "name": "Candy Blast - 糖果连击",
                "type": MaterialType.FULL_VIDEO,
                "status": MaterialStatus.READY,  # 待投放
                "url": "/images/ai_candy_combo_001.jpg",
                "thumbnail_url": "/images/ai_candy_combo_001.jpg",
                "ctr_estimate": 4.1,
                "tags": '["连击", "特效", "视觉震撼"]',
                "duration": 20,
                "file_size": 150323,
                "project_ids": '["proj_002"]',
                "campaign_ids": '["camp_t001"]',
            },
            {
                "id": "mat_005",
                "user_id": "user_test_001",
                "name": "Candy Blast - 糖果混搭",
                "type": MaterialType.FULL_VIDEO,
                "status": MaterialStatus.READY,  # 待投放
                "url": "/images/ai_candy_mix_001.jpg",
                "thumbnail_url": "/images/ai_candy_mix_001.jpg",
                "ctr_estimate": 3.8,
                "tags": '["混搭", "策略", "成长系统"]',
                "duration": 16,
                "file_size": 218082,
                "project_ids": '["proj_002"]',
                "campaign_ids": '[]',
            },
            {
                "id": "mat_006",
                "user_id": "user_test_001",
                "name": "DramaBox - 霸总钩子",
                "type": MaterialType.FULL_VIDEO,
                "status": MaterialStatus.RUNNING,  # 投放中
                "url": "/images/creative_drama_001.jpg",
                "thumbnail_url": "/images/creative_drama_001.jpg",
                "ctr_estimate": 4.5,
                "tags": '["霸总", "钩子", "反转"]',
                "duration": 15,
                "file_size": 115630,
                "project_ids": '["proj_drama_001"]',
                "campaign_ids": '["camp_d001", "camp_d002"]',
            },
            {
                "id": "mat_007",
                "user_id": "user_test_001",
                "name": "DramaBox - 情感共鸣",
                "type": MaterialType.FULL_VIDEO,
                "status": MaterialStatus.RUNNING,  # 投放中
                "url": "/images/creative_drama_002.jpg",
                "thumbnail_url": "/images/creative_drama_002.jpg",
                "ctr_estimate": 4.2,
                "tags": '["情感", "共鸣", "催泪"]',
                "duration": 18,
                "file_size": 118743,
                "project_ids": '["proj_drama_001", "proj_drama_002"]',
                "campaign_ids": '["camp_d001", "camp_d003"]',
            },
            {
                "id": "mat_008",
                "user_id": "user_test_001",
                "name": "DramaBox - 霸总浪漫",
                "type": MaterialType.FULL_VIDEO,
                "status": MaterialStatus.FATIGUE,  # 已疲劳
                "url": "/images/creative_drama_003.jpg",
                "thumbnail_url": "/images/creative_drama_003.jpg",
                "ctr_estimate": 4.8,
                "tags": '["霸总", "浪漫", "甜宠"]',
                "duration": 20,
                "file_size": 142100,
                "project_ids": '["proj_drama_001"]',
                "campaign_ids": '["camp_d002", "camp_d004"]',
            },
        ]
        
        materials = []
        for mat_data in materials_data:
            material = Material(**mat_data)
            session.add(material)
            materials.append(material)
        
        await session.flush()
        print(f"✅ 创建 {len(materials)} 个素材")
        
        # 5. 创建监控指标
        metrics_data = []
        for campaign in campaigns:
            # 为每个 Campaign 创建最近 7 天的监控数据
            for i in range(7):
                date = datetime.now() - timedelta(days=6-i)
                metric = Metric(
                    campaign_id=campaign.id,
                    timestamp=date,
                    platform=campaign.platform,
                    impressions=50000 + i * 5000,
                    clicks=1500 + i * 150,
                    conversions=120 + i * 12,
                    installs=100 + i * 10,
                    spend=3000.0 + i * 300,
                    revenue=5500.0 + i * 550,
                    ctr=3.0 + i * 0.1,
                    cvr=8.0 + i * 0.2,
                    cpa=25.0 - i * 0.5,
                    cpi=30.0 - i * 0.6,
                    roi=1.83 + i * 0.05,
                )
                metrics_data.append(metric)
                session.add(metric)
        
        await session.flush()
        print(f"✅ 创建 {len(metrics_data)} 条监控指标")
        
        # 提交所有更改
        await session.commit()
        print("\n🎉 Mock 数据填充完成！")
        print(f"   - 用户: 1")
        print(f"   - 项目: {len(projects)}")
        print(f"   - 广告投放: {len(campaigns)}")
        print(f"   - 素材: {len(materials)}")
        print(f"   - 监控指标: {len(metrics_data)}")


async def main():
    """主函数"""
    print("开始填充 Mock 数据...\n")
    
    # 创建表
    await create_tables()
    
    # 填充数据
    await seed_data()
    
    print("\n✅ 完成！")


if __name__ == "__main__":
    asyncio.run(main())

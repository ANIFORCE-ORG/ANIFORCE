"""测试数据库查询功能"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_session_maker
from app.models import User, Project, Campaign, Material, Metric


async def test_queries():
    """测试各种数据库查询"""
    async_session = get_session_maker()
    async with async_session() as session:
        print("=" * 60)
        print("数据库查询测试")
        print("=" * 60)
        
        # 1. 查询用户
        print("\n【1. 查询用户】")
        result = await session.execute(select(User))
        users = result.scalars().all()
        for user in users:
            print(f"  - ID: {user.id}")
            print(f"    Email: {user.email}")
            print(f"    Name: {user.name}")
            print(f"    Created: {user.created_at}")
        
        # 2. 查询项目（带用户关系）
        print("\n【2. 查询项目】")
        result = await session.execute(
            select(Project).order_by(Project.created_at)
        )
        projects = result.scalars().all()
        for project in projects:
            print(f"  - {project.name}")
            print(f"    ID: {project.id}")
            print(f"    游戏类型: {project.game_type}")
            print(f"    目标市场: {project.target_market}")
            print(f"    预算: ${project.total_budget:,.0f} / 已消耗: ${project.spent:,.0f}")
            print(f"    状态: {project.status.value}")
            print(f"    负责人: {project.manager}")
            print(f"    标签: {project.tags}")
        
        # 3. 查询广告投放（带项目关系）
        print("\n【3. 查询广告投放】")
        result = await session.execute(
            select(Campaign).order_by(Campaign.created_at)
        )
        campaigns = result.scalars().all()
        for campaign in campaigns:
            print(f"  - {campaign.name}")
            print(f"    ID: {campaign.id}")
            print(f"    项目ID: {campaign.project_id}")
            print(f"    平台: {campaign.platform}")
            print(f"    预算: ${campaign.budget:,.0f} / 已消耗: ${campaign.spent:,.0f}")
            print(f"    状态: {campaign.status.value}")
            print(f"    素材IDs: {campaign.material_ids}")
            material_ids = campaign.get_material_ids()
            print(f"    素材列表: {material_ids}")
        
        # 4. 查询素材
        print("\n【4. 查询素材】")
        result = await session.execute(
            select(Material).order_by(Material.created_at)
        )
        materials = result.scalars().all()
        for material in materials:
            print(f"  - {material.name}")
            print(f"    ID: {material.id}")
            print(f"    类型: {material.type.value}")
            print(f"    用户ID: {material.user_id}")
            print(f"    项目IDs: {material.project_ids}")
            print(f"    广告计划IDs: {material.campaign_ids}")
            print(f"    CTR预估: {material.ctr_estimate}%")
            print(f"    时长: {material.duration}s / 大小: {material.file_size/1024/1024:.2f}MB")
            print(f"    标签: {material.tags}")
        
        # 5. 查询监控指标（最新的）
        print("\n【5. 查询监控指标（每个Campaign最新数据）】")
        for campaign in campaigns:
            result = await session.execute(
                select(Metric)
                .where(Metric.campaign_id == campaign.id)
                .order_by(Metric.timestamp.desc())
                .limit(1)
            )
            metric = result.scalar_one_or_none()
            if metric:
                print(f"  - Campaign: {campaign.name}")
                print(f"    时间: {metric.timestamp}")
                print(f"    曝光: {metric.impressions:,} / 点击: {metric.clicks:,} / 转化: {metric.conversions:,}")
                print(f"    安装: {metric.installs:,}")
                print(f"    消耗: ${metric.spend:,.2f} / 收入: ${metric.revenue:,.2f}")
                print(f"    CTR: {metric.ctr}% / CVR: {metric.cvr}%")
                print(f"    CPA: ${metric.cpa:.2f} / CPI: ${metric.cpi:.2f}")
                print(f"    ROI: {metric.roi}x")
        
        # 6. 测试关联查询：查询项目及其所有广告投放
        print("\n【6. 关联查询：项目 -> 广告投放】")
        result = await session.execute(
            select(Project).where(Project.id == "proj_001")
        )
        project = result.scalar_one_or_none()
        if project:
            print(f"  项目: {project.name}")
            result = await session.execute(
                select(Campaign).where(Campaign.project_id == project.id)
            )
            project_campaigns = result.scalars().all()
            print(f"  广告投放数量: {len(project_campaigns)}")
            for camp in project_campaigns:
                print(f"    - {camp.name} ({camp.platform})")
        
        # 7. 测试素材多对多关系
        print("\n【7. 素材多对多关系测试】")
        result = await session.execute(
            select(Material).where(Material.id == "mat_001")
        )
        material = result.scalar_one_or_none()
        if material:
            print(f"  素材: {material.name}")
            print(f"  关联的项目IDs: {material.get_project_ids()}")
            print(f"  关联的广告计划IDs: {material.get_campaign_ids()}")
            
            # 查询这些广告计划的详细信息
            campaign_ids = material.get_campaign_ids()
            if campaign_ids:
                result = await session.execute(
                    select(Campaign).where(Campaign.id.in_(campaign_ids))
                )
                related_campaigns = result.scalars().all()
                print(f"  关联的广告计划详情:")
                for camp in related_campaigns:
                    print(f"    - {camp.name} ({camp.platform})")
        
        # 8. 统计数据
        print("\n【8. 数据统计】")
        result = await session.execute(select(User))
        user_count = len(result.scalars().all())
        
        result = await session.execute(select(Project))
        project_count = len(result.scalars().all())
        
        result = await session.execute(select(Campaign))
        campaign_count = len(result.scalars().all())
        
        result = await session.execute(select(Material))
        material_count = len(result.scalars().all())
        
        result = await session.execute(select(Metric))
        metric_count = len(result.scalars().all())
        
        print(f"  用户总数: {user_count}")
        print(f"  项目总数: {project_count}")
        print(f"  广告投放总数: {campaign_count}")
        print(f"  素材总数: {material_count}")
        print(f"  监控指标总数: {metric_count}")
        
        print("\n" + "=" * 60)
        print("✅ 数据库查询测试完成！")
        print("=" * 60)


async def main():
    """主函数"""
    await test_queries()


if __name__ == "__main__":
    asyncio.run(main())

"""测试 Repository 功能"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.database import get_session_maker
from app.repositories.impl.sqlite_user_repo import SqliteUserRepository
from app.repositories.impl.sqlite_project_repo import SqliteProjectRepository
from app.repositories.impl.sqlite_campaign_repo import SqliteCampaignRepository
from app.repositories.impl.sqlite_material_repo import SqliteMaterialRepository
from app.repositories.impl.sqlite_metric_repo import SqliteMetricRepository


async def test_repositories():
    """测试所有 Repository"""
    async_session = get_session_maker()
    async with async_session() as session:
        print("=" * 60)
        print("Repository 功能测试")
        print("=" * 60)
        
        # 初始化 Repository
        user_repo = SqliteUserRepository(session)
        project_repo = SqliteProjectRepository(session)
        campaign_repo = SqliteCampaignRepository(session)
        material_repo = SqliteMaterialRepository(session)
        metric_repo = SqliteMetricRepository(session)
        
        # 1. 测试 UserRepository
        print("\n【1. UserRepository 测试】")
        user = await user_repo.get_by_email("test@animagus.com")
        if user:
            print(f"✅ 查询用户成功: {user['email']}")
            print(f"   ID: {user['id']}")
            print(f"   Name: {user['name']}")
        else:
            print("❌ 用户不存在")
        
        # 2. 测试 ProjectRepository
        print("\n【2. ProjectRepository 测试】")
        
        # 查询单个项目
        project = await project_repo.get_by_id("proj_001")
        if project:
            print(f"✅ 查询项目成功: {project['name']}")
            print(f"   游戏类型: {project['game_type']}")
            print(f"   预算: ${project['total_budget']:,.0f}")
            print(f"   已消耗: ${project['spent']:,.0f}")
            print(f"   状态: {project['status']}")
            print(f"   标签: {project['tags']}")
        
        # 查询用户的所有项目
        if user:
            projects = await project_repo.list_by_user(user['id'])
            print(f"\n✅ 查询用户项目列表: {len(projects)} 个项目")
            for p in projects:
                print(f"   - {p['name']} ({p['status']})")
        
        # 3. 测试 CampaignRepository
        print("\n【3. CampaignRepository 测试】")
        
        # 查询单个广告投放
        campaign = await campaign_repo.get_by_id("camp_g001")
        if campaign:
            print(f"✅ 查询广告投放成功: {campaign['name']}")
            print(f"   平台: {campaign['platform']}")
            print(f"   预算: ${campaign['budget']:,.0f}")
            print(f"   已消耗: ${campaign['spent']:,.0f}")
            print(f"   状态: {campaign['status']}")
            print(f"   素材IDs: {campaign['material_ids']}")
        
        # 查询项目的所有广告投放
        if project:
            campaigns = await campaign_repo.list_by_project(project['id'])
            print(f"\n✅ 查询项目广告投放列表: {len(campaigns)} 个广告投放")
            for c in campaigns:
                print(f"   - {c['name']} ({c['platform']}, {c['status']})")
        
        # 测试获取广告投放的素材
        if campaign:
            materials = await campaign_repo.get_materials(campaign['id'])
            print(f"\n✅ 查询广告投放素材: {len(materials)} 个素材")
            for m in materials:
                print(f"   - {m['name']} ({m['type']})")
        
        # 4. 测试 MaterialRepository
        print("\n【4. MaterialRepository 测试】")
        
        # 查询单个素材
        material = await material_repo.get_by_id("mat_001")
        if material:
            print(f"✅ 查询素材成功: {material['name']}")
            print(f"   类型: {material['type']}")
            print(f"   用户ID: {material['user_id']}")
            print(f"   项目IDs: {material['project_ids']}")
            print(f"   广告计划IDs: {material['campaign_ids']}")
            print(f"   CTR预估: {material['ctr_estimate']}%")
            print(f"   时长: {material['duration']}s")
            print(f"   标签: {material['tags']}")
        
        # 查询用户的所有素材
        if user:
            materials = await material_repo.list_by_user(user['id'])
            print(f"\n✅ 查询用户素材列表: {len(materials)} 个素材")
            for m in materials:
                print(f"   - {m['name']} ({m['type']})")
        
        # 查询项目的素材
        if project:
            materials = await material_repo.list_by_project(project['id'])
            print(f"\n✅ 查询项目素材列表: {len(materials)} 个素材")
            for m in materials:
                print(f"   - {m['name']}")
        
        # 查询广告计划的素材
        if campaign:
            materials = await material_repo.list_by_campaign(campaign['id'])
            print(f"\n✅ 查询广告计划素材列表: {len(materials)} 个素材")
            for m in materials:
                print(f"   - {m['name']}")
        
        # 5. 测试 MetricRepository
        print("\n【5. MetricRepository 测试】")
        
        # 查询最新监控数据
        if campaign:
            metric = await metric_repo.get_latest(campaign['id'])
            if metric:
                print(f"✅ 查询最新监控数据成功:")
                print(f"   时间: {metric['timestamp']}")
                print(f"   曝光: {metric['impressions']:,}")
                print(f"   点击: {metric['clicks']:,}")
                print(f"   转化: {metric['conversions']:,}")
                print(f"   安装: {metric['installs']:,}")
                print(f"   消耗: ${metric['spend']:,.2f}")
                print(f"   收入: ${metric['revenue']:,.2f}")
                print(f"   CTR: {metric['ctr']}%")
                print(f"   CPI: ${metric['cpi']:.2f}")
                print(f"   ROI: {metric['roi']}x")
            
            # 查询时间序列数据
            metrics = await metric_repo.get_timeseries(campaign['id'], hours=168)  # 7天
            print(f"\n✅ 查询时间序列数据: {len(metrics)} 条记录")
            if metrics:
                print(f"   最早: {metrics[0]['timestamp']}")
                print(f"   最新: {metrics[-1]['timestamp']}")
        
        # 6. 测试素材多对多关系管理
        print("\n【6. 素材多对多关系管理测试】")
        
        # 测试添加素材到项目
        test_material = await material_repo.get_by_id("mat_002")
        if test_material and project:
            original_projects = test_material['project_ids'].copy()
            print(f"原始项目IDs: {original_projects}")
            
            # 添加到另一个项目
            await material_repo.add_to_project("mat_002", "proj_002")
            await session.commit()
            
            updated_material = await material_repo.get_by_id("mat_002")
            print(f"添加后项目IDs: {updated_material['project_ids']}")
            
            if "proj_002" in updated_material['project_ids']:
                print("✅ 添加素材到项目成功")
            
            # 移除
            await material_repo.remove_from_project("mat_002", "proj_002")
            await session.commit()
            
            restored_material = await material_repo.get_by_id("mat_002")
            print(f"移除后项目IDs: {restored_material['project_ids']}")
            
            if "proj_002" not in restored_material['project_ids']:
                print("✅ 从项目移除素材成功")
        
        # 7. 测试广告投放素材管理
        print("\n【7. 广告投放素材管理测试】")
        
        if campaign:
            original_materials = campaign['material_ids'].copy()
            print(f"原始素材IDs: {original_materials}")
            
            # 添加素材
            await campaign_repo.add_material(campaign['id'], "mat_004")
            await session.commit()
            
            updated_campaign = await campaign_repo.get_by_id(campaign['id'])
            print(f"添加后素材IDs: {updated_campaign['material_ids']}")
            
            if "mat_004" in updated_campaign['material_ids']:
                print("✅ 添加素材到广告投放成功")
            
            # 移除素材
            await campaign_repo.remove_material(campaign['id'], "mat_004")
            await session.commit()
            
            restored_campaign = await campaign_repo.get_by_id(campaign['id'])
            print(f"移除后素材IDs: {restored_campaign['material_ids']}")
            
            if "mat_004" not in restored_campaign['material_ids']:
                print("✅ 从广告投放移除素材成功")
        
        print("\n" + "=" * 60)
        print("✅ Repository 功能测试完成！")
        print("=" * 60)


async def main():
    """主函数"""
    await test_repositories()


if __name__ == "__main__":
    asyncio.run(main())

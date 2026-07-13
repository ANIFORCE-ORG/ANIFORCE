"""Seed one realistic game-marketing workspace for Agent evaluations.

Run from backend/:
    UV_CACHE_DIR=../uv_cache uv run python scripts/seed_agent_demo_account.py
"""

import asyncio
import json
from datetime import datetime, timedelta

from passlib.context import CryptContext
from sqlalchemy import delete, or_, select

from app.config.database import get_session_maker
from app.models import (
    AdSet,
    AdSetMetric,
    AdSetStatus,
    Campaign,
    CampaignStatus,
    Material,
    MaterialPerformance,
    Metric,
    Project,
    ProjectStatus,
    User,
)
from app.models.campaign import Platform
from app.models.material import MaterialStatus, MaterialType


DEMO_EMAIL = "operator-demo@aniforce.ai"
DEMO_PASSWORD = "demo123456"
DEMO_USER_ID = "demo-operator-260713"
PROJECT_ID = "demo-project-star-voyage-us"
NOW = datetime.utcnow().replace(hour=8, minute=0, second=0, microsecond=0)
PASSWORDS = CryptContext(schemes=["argon2"], deprecated="auto")


def rates(spend: float, roi: float, cpi: float, ctr: float, cpm: float = 12.0) -> dict:
    impressions = max(0, round(spend * 1000 / cpm))
    clicks = max(0, round(impressions * ctr))
    installs = max(0, round(spend / cpi)) if cpi else 0
    conversions = max(0, round(installs * 0.28))
    revenue = round(spend * (1 + roi), 2)
    return {
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "installs": installs,
        "spend": round(spend, 2),
        "revenue": revenue,
        "ctr": clicks / impressions if impressions else 0.0,
        "cvr": conversions / clicks if clicks else 0.0,
        "cpa": spend / conversions if conversions else 0.0,
        "cpi": spend / installs if installs else 0.0,
        "roi": roi,
    }


def aggregate(rows: list[dict]) -> dict:
    total = {
        key: sum(row[key] for row in rows)
        for key in ("impressions", "clicks", "conversions", "installs", "spend", "revenue")
    }
    total.update({
        "ctr": total["clicks"] / total["impressions"] if total["impressions"] else 0.0,
        "cvr": total["conversions"] / total["clicks"] if total["clicks"] else 0.0,
        "cpa": total["spend"] / total["conversions"] if total["conversions"] else 0.0,
        "cpi": total["spend"] / total["installs"] if total["installs"] else 0.0,
        "roi": (total["revenue"] - total["spend"]) / total["spend"] if total["spend"] else 0.0,
    })
    return total


CAMPAIGNS = [
    {
        "id": "demo-campaign-meta-ios-core",
        "name": "Meta｜iOS核心放量",
        "platform": Platform.Meta,
        "status": CampaignStatus.RUNNING,
        "budget": 90000.0,
        "objective": "App promotion",
        "bid_strategy": "Lowest cost",
    },
    {
        "id": "demo-campaign-meta-android-creative",
        "name": "Meta｜Android素材测试",
        "platform": Platform.Meta,
        "status": CampaignStatus.RUNNING,
        "budget": 42000.0,
        "objective": "App promotion",
        "bid_strategy": "Cost cap",
    },
    {
        "id": "demo-campaign-google-android-search",
        "name": "Google｜Android搜索承接",
        "platform": Platform.Google,
        "status": CampaignStatus.RUNNING,
        "budget": 30000.0,
        "objective": "App installs",
        "bid_strategy": "Target CPA",
    },
    {
        "id": "demo-campaign-tiktok-android-explore",
        "name": "TikTok｜Android兴趣探索",
        "platform": Platform.TikTok,
        "status": CampaignStatus.RUNNING,
        "budget": 12000.0,
        "objective": "App promotion",
        "bid_strategy": "Lowest cost",
    },
    {
        "id": "demo-campaign-tiktok-ios-preheat",
        "name": "TikTok｜iOS新品预热",
        "platform": Platform.TikTok,
        "status": CampaignStatus.REVIEW,
        "budget": 7000.0,
        "objective": "App promotion",
        "bid_strategy": "Lowest cost",
    },
]


AD_SETS = [
    ("demo-adset-ios-broad", "demo-campaign-meta-ios-core", "美国iOS｜Broad 25-44", 1400, "美国，iOS，25-44，Broad", "Advantage+ placements", "stable", 0.72, 7.8, 0.029),
    ("demo-adset-ios-lal", "demo-campaign-meta-ios-core", "美国iOS｜付费用户LAL 3%", 950, "美国，iOS，付费用户LAL 3%", "Feed, Reels", "stable", 0.58, 8.5, 0.031),
    ("demo-adset-ios-retarget", "demo-campaign-meta-ios-core", "美国iOS｜7日回流", 420, "美国，iOS，安装未付费7日", "Feed", "stable", 0.91, 6.9, 0.026),
    ("demo-adset-android-broad", "demo-campaign-meta-android-creative", "美国Android｜Broad素材轮测", 720, "美国，Android，Broad", "Feed, Reels", "decline", 0.34, 9.4, 0.028),
    ("demo-adset-android-gamer", "demo-campaign-meta-android-creative", "美国Android｜策略游戏兴趣", 610, "美国，Android，策略/SLG兴趣", "Feed, Reels", "fatigue", 0.48, 8.8, 0.034),
    ("demo-adset-search-brand", "demo-campaign-google-android-search", "美国Android｜品牌词", 680, "美国，Android，品牌词", "Google Search", "stable", 0.44, 7.4, 0.052),
    ("demo-adset-search-generic", "demo-campaign-google-android-search", "美国Android｜策略手游泛词", 470, "美国，Android，策略手游泛词", "Google Search", "stable", 0.24, 10.2, 0.041),
    ("demo-adset-tiktok-interest", "demo-campaign-tiktok-android-explore", "美国Android｜策略兴趣探索", 210, "美国，Android，策略/科幻兴趣", "TikTok Feed", "volatile", 0.95, 8.2, 0.036),
    ("demo-adset-tiktok-lal", "demo-campaign-tiktok-android-explore", "美国Android｜高价值LAL", 170, "美国，Android，高价值LAL 5%", "TikTok Feed", "volatile_low", 0.25, 10.8, 0.030),
    ("demo-adset-preheat-broad", "demo-campaign-tiktok-ios-preheat", "美国iOS｜新品预热Broad", 500, "美国，iOS，18-34，Broad", "TikTok Feed", "no_data", 0.0, 0.0, 0.0),
]


MATERIALS = [
    ("demo-material-boss", "Boss战实录｜15秒", MaterialStatus.RUNNING, 32, 2.1, ["Boss战", "实录", "强反馈"]),
    ("demo-material-upgrade", "基地升级前后对比｜20秒", MaterialStatus.RUNNING, 38, 2.5, ["升级", "前后对比", "养成"]),
    ("demo-material-reversal", "三秒逆袭反转｜12秒", MaterialStatus.FATIGUE, 86, 5.3, ["反转", "强钩子", "疲劳"]),
    ("demo-material-draw", "角色抽卡爽感｜15秒", MaterialStatus.RUNNING, 52, 3.3, ["抽卡", "角色", "爽感"]),
    ("demo-material-alliance", "联盟混战高光｜18秒", MaterialStatus.RUNNING, 44, 2.8, ["联盟", "多人", "高光"]),
    ("demo-material-review", "媒体口碑混剪｜20秒", MaterialStatus.RUNNING, 35, 2.2, ["口碑", "媒体", "混剪"]),
    ("demo-material-new-hook", "新钩子A｜失败后重建", MaterialStatus.READY, 5, 0.0, ["新素材", "失败", "重建"]),
    ("demo-material-preheat", "新品预约悬念版｜10秒", MaterialStatus.READY, 0, 0.0, ["新品", "预约", "悬念"]),
]


MATERIAL_ASSIGNMENTS = [
    ("demo-material-boss", "demo-adset-ios-broad", 0.52, 0.82, 2.1),
    ("demo-material-upgrade", "demo-adset-ios-broad", 0.48, 0.61, 2.5),
    ("demo-material-boss", "demo-adset-ios-lal", 0.45, 0.68, 2.0),
    ("demo-material-draw", "demo-adset-ios-lal", 0.55, 0.49, 3.3),
    ("demo-material-upgrade", "demo-adset-ios-retarget", 1.0, 0.91, 2.4),
    ("demo-material-reversal", "demo-adset-android-broad", 0.62, -0.24, 5.3),
    ("demo-material-new-hook", "demo-adset-android-broad", 0.38, 0.43, 1.4),
    ("demo-material-reversal", "demo-adset-android-gamer", 0.44, -0.12, 5.0),
    ("demo-material-alliance", "demo-adset-android-gamer", 0.56, 0.36, 2.8),
    ("demo-material-review", "demo-adset-search-brand", 1.0, 0.44, 2.2),
    ("demo-material-review", "demo-adset-search-generic", 1.0, 0.24, 2.4),
    ("demo-material-alliance", "demo-adset-tiktok-interest", 1.0, 0.95, 2.1),
    ("demo-material-draw", "demo-adset-tiktok-lal", 1.0, 0.25, 1.7),
]


def daily_profile(kind: str, day: int, base_spend: float, base_roi: float) -> tuple[float, float]:
    if kind == "stable":
        return base_spend * (0.94 + day * 0.009), base_roi + ((day % 3) - 1) * 0.025
    if kind == "decline":
        return base_spend * (1.0 + day * 0.012), base_roi - day * 0.045
    if kind == "fatigue":
        return base_spend * (1.04 - day * 0.012), base_roi - day * 0.065
    if kind == "volatile":
        multipliers = [0.45, 1.1, 0.65, 1.35, 0.55, 1.2, 0.72, 1.4, 0.5, 1.3, 0.8, 1.15, 0.7, 1.25]
        rois = [0.2, 1.3, 0.45, 1.6, 0.1, 1.1, 0.5, 1.45, -0.05, 1.2, 0.4, 1.0, 0.3, 1.35]
        return base_spend * multipliers[day], rois[day]
    if kind == "volatile_low":
        multipliers = [0.2, 0.55, 0.3, 0.75, 0.25, 0.6, 0.18, 0.8, 0.22, 0.65, 0.35, 0.7, 0.28, 0.6]
        rois = [-0.4, 0.8, -0.2, 0.95, -0.5, 0.7, -0.35, 1.0, -0.45, 0.6, -0.1, 0.75, -0.25, 0.7]
        return base_spend * multipliers[day], rois[day]
    return 0.0, 0.0


async def seed() -> None:
    maker = get_session_maker()
    async with maker() as session:
        user = (
            await session.execute(
                select(User).where(or_(User.id == DEMO_USER_ID, User.email == DEMO_EMAIL))
            )
        ).scalar_one_or_none()
        if not user:
            user = User(id=DEMO_USER_ID, email=DEMO_EMAIL, name="Alex｜美国市场投放", password_hash="")
            session.add(user)
        user.email = DEMO_EMAIL
        user.name = "Alex｜美国市场投放"
        user.password_hash = PASSWORDS.hash(DEMO_PASSWORD)
        await session.flush()

        await session.execute(delete(Project).where(Project.user_id == user.id))
        await session.execute(delete(Material).where(Material.user_id == user.id))
        await session.flush()

        project = Project(
            id=PROJECT_ID,
            user_id=user.id,
            name="星际远征：美国增长",
            description="科幻SLG手游美国市场增长项目，处于规模化投放与素材迭代阶段。",
            product="星际远征",
            game_type="SLG",
            target_market="美国",
            tags=json.dumps(["SLG", "美国", "增长期"], ensure_ascii=False),
            total_budget=181000.0,
            spent=0.0,
            status=ProjectStatus.ACTIVE,
            manager="Alex",
            start_date=(NOW - timedelta(days=45)).date(),
            end_date=(NOW + timedelta(days=45)).date(),
        )
        session.add(project)

        material_ids = [item[0] for item in MATERIALS]
        for material_id, name, status, fatigue, frequency, tags in MATERIALS:
            session.add(Material(
                id=material_id,
                user_id=user.id,
                name=name,
                type=MaterialType.FULL_VIDEO,
                status=status,
                url=f"/images/{material_id}.jpg",
                thumbnail_url=f"/images/{material_id}.jpg",
                ctr_estimate=None,
                tags=json.dumps(tags, ensure_ascii=False),
                media_kind="video",
                format="mp4",
                ratio="9:16",
                source="demo_fixture",
                creator="Creative Team",
                platforms=json.dumps(["Meta", "Google", "TikTok"]),
                review_status="approved",
                score=max(0, 100 - fatigue),
                fatigue=fatigue,
                duration=15,
                project_ids=json.dumps([PROJECT_ID]),
                campaign_ids="[]",
            ))

        campaign_by_id = {}
        for item in CAMPAIGNS:
            campaign = Campaign(
                **item,
                project_id=PROJECT_ID,
                description="演示账号真实用户旅程数据",
                countries="美国",
                budget_type="Lifetime budget",
                spent=0.0,
                start_date=(NOW - timedelta(days=30)).date(),
                end_date=(NOW + timedelta(days=30)).date(),
                material_ids="[]",
                config=json.dumps({"fixture": "agent_intelligence_v2"}),
            )
            campaign_by_id[campaign.id] = campaign
            session.add(campaign)

        ad_set_by_id = {}
        for ad_set_id, campaign_id, name, budget, audience, placements, *_ in AD_SETS:
            ad_set = AdSet(
                id=ad_set_id,
                campaign_id=campaign_id,
                name=name,
                audience=audience,
                placements=placements,
                optimization_goal="APP_INSTALLS",
                bid_strategy="Lowest cost",
                daily_budget=budget,
                spent=0.0,
                status=AdSetStatus.RUNNING if "preheat" not in ad_set_id else AdSetStatus.DRAFT,
                start_date=(NOW - timedelta(days=30)).date(),
                end_date=(NOW + timedelta(days=30)).date(),
            )
            ad_set_by_id[ad_set_id] = ad_set
            session.add(ad_set)
        await session.flush()

        daily_campaign_rows: dict[tuple[str, int], list[dict]] = {}
        ad_set_latest: dict[str, dict] = {}
        for ad_set_id, campaign_id, _, _, _, _, kind, base_roi, cpi, ctr in AD_SETS:
            if kind == "no_data":
                continue
            ad_set = ad_set_by_id[ad_set_id]
            for day in range(14):
                timestamp = NOW - timedelta(days=13 - day)
                spend, roi = daily_profile(kind, day, ad_set.daily_budget, base_roi)
                row = rates(spend, roi, cpi, ctr)
                daily_campaign_rows.setdefault((campaign_id, day), []).append(row)
                ad_set_latest[ad_set_id] = row
                session.add(AdSetMetric(
                    id=f"metric-{ad_set_id}-{day:02d}",
                    ad_set_id=ad_set_id,
                    timestamp=timestamp,
                    **row,
                ))
                ad_set.spent += row["spend"]

        for (campaign_id, day), rows in daily_campaign_rows.items():
            row = aggregate(rows)
            campaign = campaign_by_id[campaign_id]
            session.add(Metric(
                id=f"metric-{campaign_id}-{day:02d}",
                campaign_id=campaign_id,
                timestamp=NOW - timedelta(days=13 - day),
                platform=campaign.platform.value,
                **row,
            ))
            campaign.spent += row["spend"]

        for index, (material_id, ad_set_id, share, roi, frequency) in enumerate(MATERIAL_ASSIGNMENTS):
            ad_row = ad_set_latest[ad_set_id]
            spend = ad_row["spend"] * share
            row = rates(spend, roi, max(5.5, ad_row["cpi"] * (1.0 + (0.5 - share) * 0.15)), max(0.018, ad_row["ctr"] * (0.85 + share * 0.25)))
            session.add(MaterialPerformance(
                id=f"material-performance-{index:02d}",
                material_id=material_id,
                ad_set_id=ad_set_id,
                timestamp=NOW,
                frequency=frequency,
                **{key: row[key] for key in ("impressions", "clicks", "conversions", "installs", "spend", "revenue", "ctr", "cvr", "cpi", "roi")},
            ))

        campaign_materials: dict[str, set[str]] = {item["id"]: set() for item in CAMPAIGNS}
        material_campaigns: dict[str, set[str]] = {item[0]: set() for item in MATERIALS}
        for material_id, ad_set_id, *_ in MATERIAL_ASSIGNMENTS:
            campaign_id = ad_set_by_id[ad_set_id].campaign_id
            campaign_materials[campaign_id].add(material_id)
            material_campaigns[material_id].add(campaign_id)
        for campaign_id, ids in campaign_materials.items():
            campaign_by_id[campaign_id].material_ids = json.dumps(sorted(ids))
        materials = (await session.execute(select(Material).where(Material.user_id == user.id))).scalars().all()
        for material in materials:
            material.campaign_ids = json.dumps(sorted(material_campaigns[material.id]))

        project.spent = sum(campaign.spent for campaign in campaign_by_id.values())
        await session.commit()

    print("Agent demo account seeded")
    print(f"email={DEMO_EMAIL}")
    print(f"password={DEMO_PASSWORD}")
    print("projects=1 campaigns=5 ad_sets=10 materials=8 metric_days=14")


if __name__ == "__main__":
    asyncio.run(seed())

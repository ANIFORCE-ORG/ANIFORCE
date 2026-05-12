"""Reset v0.1 customer preview data.

This script keeps imported Meta account/config rows, removes dirty demo rows,
and writes a consistent Project -> Account -> Campaign -> Material chain for
customer preview validation.
"""
import asyncio
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.database import get_session_maker
from app.models import Campaign, Material, Metric, Project, User
from app.models.campaign import CampaignStatus, Platform
from app.models.material import MaterialStatus, MaterialType
from app.models.platform_account import AgentAction, PlatformAccount, ProjectPlatformAccount
from app.models.project import ProjectStatus


USER_ID = "user_test_001"
PROJECT_ID = "preview_drama_global_001"
META_ACCOUNT_PK = "9924b13d-c6f2-4a77-bf61-2a07a4cc5f11"


def dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


async def ensure_user(session) -> None:
    user = await session.get(User, USER_ID)
    if user:
        return
    session.add(
        User(
            id=USER_ID,
            email="preview@animagus.ai",
            password_hash="demo-preview-password",
            name="ANIFORCE Preview",
        )
    )


async def ensure_meta_account(session) -> str:
    account = await session.get(PlatformAccount, META_ACCOUNT_PK)
    if account:
        account.status = "active"
        account.account_name = account.account_name or "Meta Sandbox Ad Account"
        return account.id

    account = PlatformAccount(
        id=META_ACCOUNT_PK,
        user_id=USER_ID,
        platform="meta",
        account_id="act_1943996592887453",
        account_name="Meta Sandbox Ad Account",
        status="active",
        source_type="customer-preview",
        remark="Stable preview account for v0.1 customer demo",
        currency="USD",
        timezone="America/Los_Angeles",
        access_token="demo-preview-token",
    )
    session.add(account)
    return account.id


async def clear_preview_rows(session) -> None:
    await session.execute(delete(AgentAction))
    await session.execute(delete(Metric))
    await session.execute(delete(Material))
    await session.execute(delete(Campaign))
    await session.execute(delete(ProjectPlatformAccount))
    await session.execute(delete(Project))


async def seed_preview_rows(session, account_pk: str) -> None:
    today = date.today()

    project = Project(
        id=PROJECT_ID,
        user_id=USER_ID,
        name="DramaBox 北美增长客户预览",
        description="v0.1 Customer Preview 演示项目：账户、素材、Campaign、报表和 Agent 建议使用同一组数据。",
        game_type="短剧",
        product_type="短剧",
        target_market="北美",
        region=dumps(["US", "CA"]),
        tags=dumps(["客户预览", "短剧", "Meta", "北美"]),
        total_budget=150000.0,
        spent=86500.0,
        target_roi=2.2,
        status=ProjectStatus.ACTIVE,
        manager="ANIFORCE Ops",
        start_date=today - timedelta(days=28),
        end_date=today + timedelta(days=32),
    )
    session.add(project)

    session.add(
        ProjectPlatformAccount(
            id="preview_link_meta_account",
            project_id=PROJECT_ID,
            platform_account_id=account_pk,
            role="primary",
            status="active",
            spend_cap=150000.0,
            daily_cap=6000.0,
            note="客户预览主 Meta 沙盒账户",
        )
    )

    materials = [
        Material(
            id="preview_creative_hook_001",
            user_id=USER_ID,
            project_ids=dumps([PROJECT_ID]),
            campaign_ids=dumps(["preview_meta_campaign_001"]),
            name="DB_Preview_OpeningHook",
            type=MaterialType.FULL_VIDEO,
            media_type="image",
            status=MaterialStatus.RUNNING,
            url="/images/creatives/creative_drama_001.jpg",
            thumbnail_url="/images/creatives/creative_drama_001.jpg",
            ctr_estimate=6.2,
            roi=2.68,
            spend=12500.0,
            campaign_id="preview_meta_campaign_001",
            fatigue=4.5,
            is_hero=True,
            tags=dumps(["hook", "drama", "meta"]),
            duration=15,
        ),
        Material(
            id="preview_creative_emotion_001",
            user_id=USER_ID,
            project_ids=dumps([PROJECT_ID]),
            campaign_ids=dumps(["preview_meta_campaign_001"]),
            name="DB_Preview_EmotionCut",
            type=MaterialType.FULL_VIDEO,
            media_type="image",
            status=MaterialStatus.RUNNING,
            url="/images/creatives/creative_drama_002.jpg",
            thumbnail_url="/images/creatives/creative_drama_002.jpg",
            ctr_estimate=4.9,
            roi=2.18,
            spend=9800.0,
            campaign_id="preview_meta_campaign_001",
            fatigue=5.8,
            is_hero=False,
            tags=dumps(["emotion", "cut"]),
            duration=18,
        ),
        Material(
            id="preview_creative_ai_001",
            user_id=USER_ID,
            project_ids=dumps([PROJECT_ID]),
            campaign_ids=dumps([]),
            name="DB_Preview_AI_NewScene",
            type=MaterialType.FULL_VIDEO,
            media_type="image",
            status=MaterialStatus.READY,
            url="/images/creatives/ai_candy_mix_001.jpg",
            thumbnail_url="/images/creatives/ai_candy_mix_001.jpg",
            ctr_estimate=5.4,
            roi=0.0,
            spend=0.0,
            fatigue=0.0,
            is_hero=False,
            tags=dumps(["ai_gen", "ready"]),
            duration=12,
        ),
    ]
    session.add_all(materials)

    campaign = Campaign(
        id="preview_meta_campaign_001",
        project_id=PROJECT_ID,
        name="DB_US_Meta_Install_Preview_001",
        description="客户预览主 Campaign，已关联 Meta 沙盒账户与两条素材。",
        platform=Platform.Meta,
        budget=90000.0,
        spent=62300.0,
        target_cpa=28.0,
        status=CampaignStatus.RUNNING,
        pipeline_step="created_on_platform",
        platform_account_id=account_pk,
        external_campaign_id="6948950991292",
        external_status="ACTIVE",
        objective="OUTCOME_TRAFFIC",
        budget_type="daily",
        daily_budget=3000.0,
        learning_phase="limited",
        auto_optimize_enabled=True,
        optimization_rules=dumps(["cpi_guardrail", "creative_fatigue_watch"]),
        material_ids=dumps(["preview_creative_hook_001", "preview_creative_emotion_001"]),
        start_date=today - timedelta(days=21),
        end_date=today + timedelta(days=25),
        config=dumps(
            {
                "platform_account_id": account_pk,
                "remote_campaign_id": "6948950991292",
                "remote_platform": "meta",
                "objective": "OUTCOME_TRAFFIC",
                "budget_type": "daily",
            }
        ),
    )
    session.add(campaign)

    for index in range(7):
        session.add(
            Metric(
                campaign_id=campaign.id,
                timestamp=datetime.utcnow() - timedelta(days=6 - index),
                platform="Meta",
                impressions=82000 + index * 5400,
                clicks=3600 + index * 220,
                conversions=230 + index * 16,
                installs=190 + index * 14,
                spend=7600.0 + index * 380,
                revenue=14200.0 + index * 720,
                ctr=4.4 + index * 0.08,
                cvr=6.3 + index * 0.12,
                cpa=31.5 - index * 0.35,
                cpi=40.0 - index * 0.5,
                roi=1.86 + index * 0.04,
            )
        )


async def main() -> None:
    session_maker = get_session_maker()
    async with session_maker() as session:
        await ensure_user(session)
        account_pk = await ensure_meta_account(session)
        await clear_preview_rows(session)
        await seed_preview_rows(session, account_pk)
        await session.commit()

    print("Customer preview data reset complete.")
    print(f"Project: {PROJECT_ID}")
    print(f"Meta account: {META_ACCOUNT_PK}")
    print("Campaign: preview_meta_campaign_001")
    print("Materials: preview_creative_hook_001, preview_creative_emotion_001, preview_creative_ai_001")


if __name__ == "__main__":
    asyncio.run(main())

"""Seed legacy ANIMAGUS creative materials into the current SQLite database.

This script is intentionally idempotent: it updates existing legacy creative
records and leaves unrelated rows untouched.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.dialects.sqlite import insert

from app.config.database import Base, get_engine, get_session_maker
from app.models import User
from app.models.material import Material, MaterialStatus, MaterialType


LEGACY_CREATIVES = [
    {"id": "cre_001", "campaign_id": "camp_g001", "name": "CB_Gameplay_Level15", "duration": 15, "tags": ["gameplay", "level"], "ctr": 0.043, "cvr": 0.185, "roi": 1.88, "spend": 8200, "status": "running", "fatigue": 2.1, "is_hero": True, "thumb": "creative_game_001.jpg", "project_ids": ["proj_game_001"]},
    {"id": "cre_002", "campaign_id": "camp_g002", "name": "CB_UGC_FailMoment", "duration": 12, "tags": ["ugc", "humor"], "ctr": 0.051, "cvr": 0.210, "roi": 2.35, "spend": 6800, "status": "running", "fatigue": 3.8, "is_hero": True, "thumb": "creative_game_002.jpg", "project_ids": ["proj_game_001"]},
    {"id": "cre_003", "campaign_id": "camp_g003", "name": "CB_Character_CandyQueen", "duration": 18, "tags": ["character", "story"], "ctr": 0.038, "cvr": 0.165, "roi": 1.65, "spend": 5100, "status": "running", "fatigue": 5.2, "is_hero": False, "thumb": "creative_game_003.jpg", "project_ids": ["proj_game_001"]},
    {"id": "cre_004", "campaign_id": "camp_g001", "name": "CB_Combo_Explosion", "duration": 10, "tags": ["gameplay", "highlight"], "ctr": 0.046, "cvr": 0.195, "roi": 2.10, "spend": 4500, "status": "running", "fatigue": 1.5, "is_hero": False, "thumb": "creative_game_004.jpg", "project_ids": ["proj_game_001"]},
    {"id": "cre_005", "campaign_id": "camp_g004", "name": "CB_JP_Kawaii_Hook", "duration": 8, "tags": ["hook", "localized"], "ctr": 0.055, "cvr": 0.230, "roi": 2.50, "spend": 3200, "status": "running", "fatigue": 0.8, "is_hero": True, "thumb": "ai_candy_hook_001.jpg", "project_ids": ["proj_game_001"]},
    {"id": "cre_006", "campaign_id": "camp_g004", "name": "CB_SEA_UGC_React", "duration": 15, "tags": ["ugc", "reaction"], "ctr": 0.048, "cvr": 0.205, "roi": 2.35, "spend": 2100, "status": "running", "fatigue": 0.5, "is_hero": False, "thumb": "ai_candy_reaction_001.jpg", "project_ids": ["proj_game_002"]},
    {"id": "cre_007", "campaign_id": "camp_g002", "name": "CB_Story_V3_Hook", "duration": 15, "tags": ["story", "hook"], "ctr": 0.043, "cvr": 0.180, "roi": 1.92, "spend": 3800, "status": "running", "fatigue": 4.2, "is_hero": False, "thumb": "1-1.png", "project_ids": ["proj_game_001"]},
    {"id": "cre_008", "campaign_id": "camp_g003", "name": "CB_Intro_V1", "duration": 10, "tags": ["intro", "brand"], "ctr": 0.035, "cvr": 0.155, "roi": 1.55, "spend": 2900, "status": "running", "fatigue": 5.5, "is_hero": False, "thumb": "1-2.png", "project_ids": ["proj_game_001"]},
    {"id": "cre_009", "campaign_id": "camp_g004", "name": "CB_SEA_LocalFlavor", "duration": 12, "tags": ["localized", "ugc"], "ctr": 0.050, "cvr": 0.215, "roi": 2.28, "spend": 1800, "status": "running", "fatigue": 1.2, "is_hero": False, "thumb": "ai_candy_reaction_001.jpg", "project_ids": ["proj_game_002"]},
    {"id": "cre_010", "campaign_id": "camp_g003", "name": "CB_KR_Idol_Collab", "duration": 20, "tags": ["collab", "brand"], "ctr": 0.032, "cvr": 0.140, "roi": 1.25, "spend": 1500, "status": "running", "fatigue": 3.0, "is_hero": False, "thumb": "ai_candy_trend_001.jpg", "project_ids": ["proj_game_001"]},
    {"id": "cre_011", "campaign_id": None, "name": "CB_Victory_Dance", "duration": 12, "tags": ["celebration", "hook"], "ctr": 0.058, "cvr": 0.245, "roi": 2.80, "spend": 0, "status": "ready", "fatigue": 0, "is_hero": True, "thumb": "ai_candy_victory_001.jpg", "project_ids": ["proj_game_001"]},
    {"id": "cre_012", "campaign_id": None, "name": "CB_AI_ComboPlay", "duration": 15, "tags": ["ai_gen", "gameplay"], "ctr": 0.042, "cvr": 0.190, "roi": 0, "spend": 0, "status": "ready", "fatigue": 0, "is_hero": False, "thumb": "ai_candy_combo_001.jpg", "project_ids": ["proj_game_001"]},
    {"id": "cre_013", "campaign_id": "camp_d001", "name": "DB_UGC_Reaction", "duration": 15, "tags": ["ugc", "reaction"], "ctr": 0.062, "cvr": 0.280, "roi": 2.68, "spend": 12500, "status": "running", "fatigue": 4.5, "is_hero": True, "thumb": "creative_drama_001.jpg", "project_ids": ["proj_drama_001"]},
    {"id": "cre_014", "campaign_id": "camp_d001", "name": "DB_Lifestyle_BingeWatch", "duration": 20, "tags": ["lifestyle", "binge"], "ctr": 0.045, "cvr": 0.195, "roi": 2.15, "spend": 9800, "status": "running", "fatigue": 5.8, "is_hero": False, "thumb": "creative_drama_002.jpg", "project_ids": ["proj_drama_001"]},
    {"id": "cre_015", "campaign_id": "camp_d002", "name": "DB_BossRomance_FirstMeet", "duration": 25, "tags": ["drama", "romance"], "ctr": 0.071, "cvr": 0.320, "roi": 3.15, "spend": 8600, "status": "running", "fatigue": 3.2, "is_hero": True, "thumb": "creative_drama_003.jpg", "project_ids": ["proj_drama_001"]},
    {"id": "cre_016", "campaign_id": "camp_d002", "name": "DB_BossRomance_Confession", "duration": 18, "tags": ["drama", "emotion"], "ctr": 0.065, "cvr": 0.290, "roi": 2.85, "spend": 7200, "status": "fatigue", "fatigue": 6.5, "is_hero": False, "thumb": "creative_drama_004.jpg", "project_ids": ["proj_drama_001"]},
    {"id": "cre_017", "campaign_id": "camp_d003", "name": "DB_CA_Hook_Cliffhanger", "duration": 10, "tags": ["hook", "suspense"], "ctr": 0.068, "cvr": 0.305, "roi": 2.45, "spend": 5800, "status": "running", "fatigue": 2.8, "is_hero": True, "thumb": "ai_candy_ugc_001.jpg", "project_ids": ["proj_drama_002"]},
    {"id": "cre_018", "campaign_id": "camp_d003", "name": "DB_Brand_Story", "duration": 30, "tags": ["brand", "story"], "ctr": 0.028, "cvr": 0.125, "roi": 1.42, "spend": 3500, "status": "running", "fatigue": 7.1, "is_hero": False, "thumb": "ai_candy_trend_001.jpg", "project_ids": ["proj_drama_002"]},
    {"id": "cre_019", "campaign_id": "camp_d001", "name": "DB_Teaser_EP1", "duration": 15, "tags": ["teaser", "drama"], "ctr": 0.058, "cvr": 0.260, "roi": 2.52, "spend": 6200, "status": "running", "fatigue": 4.8, "is_hero": False, "thumb": "creative_drama_002.jpg", "project_ids": ["proj_drama_001"]},
    {"id": "cre_020", "campaign_id": "camp_d001", "name": "DB_BTS_Interview", "duration": 25, "tags": ["bts", "interview"], "ctr": 0.040, "cvr": 0.175, "roi": 1.85, "spend": 4500, "status": "running", "fatigue": 6.2, "is_hero": False, "thumb": "1-6.png", "project_ids": ["proj_drama_001"]},
    {"id": "cre_021", "campaign_id": "camp_d003", "name": "DB_CA_Countdown", "duration": 8, "tags": ["countdown", "urgency"], "ctr": 0.055, "cvr": 0.235, "roi": 2.10, "spend": 3100, "status": "running", "fatigue": 2.5, "is_hero": False, "thumb": "ai_candy_ugc_001.jpg", "project_ids": ["proj_drama_002"]},
    {"id": "cre_022", "campaign_id": "camp_d003", "name": "DB_US_Emotional_Cut", "duration": 18, "tags": ["emotion", "cut"], "ctr": 0.047, "cvr": 0.200, "roi": 1.78, "spend": 2800, "status": "running", "fatigue": 3.5, "is_hero": False, "thumb": "1-8.png", "project_ids": ["proj_drama_002"]},
    {"id": "cre_023", "campaign_id": None, "name": "DB_AI_NewScene", "duration": 15, "tags": ["ai_gen", "drama"], "ctr": 0.052, "cvr": 0.240, "roi": 0, "spend": 0, "status": "ready", "fatigue": 0, "is_hero": False, "thumb": "ai_candy_mix_001.jpg", "project_ids": ["proj_drama_001"]},
    {"id": "cre_024", "campaign_id": None, "name": "DB_AI_EmotionHook", "duration": 8, "tags": ["ai_gen", "hook"], "ctr": 0.060, "cvr": 0.270, "roi": 0, "spend": 0, "status": "ready", "fatigue": 0, "is_hero": True, "thumb": "creative_drama_001.jpg", "project_ids": ["proj_drama_001"]},
]


async def ensure_schema(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        columns = {
            row[1]
            for row in (await conn.execute(text("PRAGMA table_info(materials)"))).fetchall()
        }
        additions = {
            "roi": "ALTER TABLE materials ADD COLUMN roi FLOAT",
            "spend": "ALTER TABLE materials ADD COLUMN spend FLOAT",
            "campaign_id": "ALTER TABLE materials ADD COLUMN campaign_id VARCHAR(36)",
        }
        for column, statement in additions.items():
            if column not in columns:
                await conn.execute(text(statement))


async def seed():
    engine = get_engine()
    await ensure_schema(engine)
    async_session = get_session_maker()

    async with async_session() as session:
        await session.merge(
            User(
                id="user_test_001",
                email="legacy-seed@aniforce.local",
                password_hash="demo-mode-unused",
                name="测试用户",
            )
        )

        rows = []
        for item in LEGACY_CREATIVES:
            campaign_ids = [item["campaign_id"]] if item["campaign_id"] else []
            image_url = f"/images/creatives/{item['thumb']}"
            rows.append({
                "id": item["id"],
                "user_id": "user_test_001",
                "project_ids": json.dumps(item["project_ids"]),
                "campaign_ids": json.dumps(campaign_ids),
                "name": item["name"],
                "type": MaterialType.FULL_VIDEO,
                "media_type": "image",
                "status": MaterialStatus(item["status"]),
                "url": image_url,
                "thumbnail_url": image_url,
                "ctr_estimate": round(item["ctr"] * 100, 2),
                "roi": item["roi"],
                "spend": item["spend"],
                "campaign_id": item["campaign_id"],
                "fatigue": item["fatigue"],
                "is_hero": item["is_hero"],
                "tags": json.dumps(item["tags"]),
                "duration": item["duration"],
            })

        stmt = insert(Material).values(rows)
        update_columns = {
            column.name: getattr(stmt.excluded, column.name)
            for column in Material.__table__.columns
            if column.name not in {"id", "created_at"}
        }
        await session.execute(stmt.on_conflict_do_update(
            index_elements=["id"],
            set_=update_columns,
        ))

        for item in LEGACY_CREATIVES:
            if item["campaign_id"]:
                await session.execute(
                    text(
                        """
                        UPDATE campaigns
                        SET material_ids = CASE
                            WHEN material_ids IS NULL OR material_ids = '' THEN :new_ids
                            WHEN material_ids NOT LIKE :needle THEN json_insert(material_ids, '$[#]', :material_id)
                            ELSE material_ids
                        END
                        WHERE id = :campaign_id
                        """
                    ),
                    {
                        "new_ids": json.dumps([item["id"]]),
                        "needle": f'%"{item["id"]}"%',
                        "material_id": item["id"],
                        "campaign_id": item["campaign_id"],
                    },
                )

        await session.commit()

    print(f"Seeded {len(LEGACY_CREATIVES)} legacy creative materials.")


if __name__ == "__main__":
    asyncio.run(seed())

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config


BACKEND_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
REVISION = "260713_02_ad_set_evidence"
PARENT = "260713_01_session_task_state"


def config_for(db_path: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def tables(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        return {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }


def columns(db_path: Path, table: str) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_ad_set_evidence_migration_roundtrip() -> None:
    db_path = PROJECT_ROOT / "drafts" / "260713" / "260713_16_ad_set_evidence_migration.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    try:
        with sqlite3.connect(db_path) as connection:
            connection.executescript(
                "CREATE TABLE campaigns (id VARCHAR(36) PRIMARY KEY);"
                "CREATE TABLE materials (id VARCHAR(36) PRIMARY KEY);"
            )
        config = config_for(db_path)
        command.stamp(config, PARENT)
        command.upgrade(config, REVISION)

        assert {"ad_sets", "ad_set_metrics", "material_performance"} <= tables(db_path)
        assert {"campaign_id", "audience", "placements", "daily_budget", "status"} <= columns(
            db_path, "ad_sets"
        )
        assert {"material_id", "ad_set_id", "roi", "frequency"} <= columns(
            db_path, "material_performance"
        )

        command.downgrade(config, PARENT)
        assert not {"ad_sets", "ad_set_metrics", "material_performance"} & tables(db_path)
    finally:
        db_path.unlink(missing_ok=True)

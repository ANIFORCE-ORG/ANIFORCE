import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config


BACKEND_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
REVISION = "260728_01_material_sync"
PARENT = "260713_02_ad_set_evidence"


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


def test_material_sync_migration_roundtrip() -> None:
    db_path = PROJECT_ROOT / "drafts" / "260728" / "260728_01_material_sync_migration.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    try:
        with sqlite3.connect(db_path) as connection:
            connection.executescript(
                "CREATE TABLE users (id VARCHAR(36) PRIMARY KEY);"
                "CREATE TABLE platform_connections (id VARCHAR(36) PRIMARY KEY);"
                "CREATE TABLE materials (id VARCHAR(36) PRIMARY KEY);"
            )
        config = config_for(db_path)
        command.stamp(config, PARENT)
        command.upgrade(config, REVISION)

        assert {"material_platform_assets", "material_sync_runs"} <= tables(db_path)
        assert {
            "material_id",
            "connection_id",
            "ad_account_id",
            "external_asset_id",
            "image_hash",
            "last_seen_at",
        } <= columns(db_path, "material_platform_assets")
        assert {
            "status",
            "discovered_count",
            "created_count",
            "failed_count",
            "error_summary",
        } <= columns(db_path, "material_sync_runs")

        command.downgrade(config, PARENT)
        assert not {"material_platform_assets", "material_sync_runs"} & tables(db_path)
    finally:
        db_path.unlink(missing_ok=True)

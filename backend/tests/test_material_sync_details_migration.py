import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config


BACKEND_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
REVISION = "260728_02_sync_details"
PARENT = "260713_02_ad_set_evidence"


def config_for(db_path: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def columns(db_path: Path, table: str) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def tables(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        return {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }


def test_material_sync_details_migration_roundtrip() -> None:
    db_path = (
        PROJECT_ROOT
        / "drafts"
        / "260728"
        / "260728_02_material_sync_details_migration.db"
    )
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    try:
        with sqlite3.connect(db_path) as connection:
            connection.executescript(
                "CREATE TABLE users (id VARCHAR(36) PRIMARY KEY);"
                "CREATE TABLE platform_connections (id VARCHAR(36) PRIMARY KEY);"
                "CREATE TABLE materials ("
                "id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL"
                ");"
            )
        config = config_for(db_path)
        command.stamp(config, PARENT)
        command.upgrade(config, REVISION)

        assert "material_sync_run_items" in tables(db_path)
        assert {"storage_object_key", "mime_type", "checksum_sha256"} <= columns(
            db_path, "materials"
        )
        assert {"asset_types", "reused_count"} <= columns(
            db_path, "material_sync_runs"
        )
        assert {
            "run_id",
            "external_asset_id",
            "action",
            "material_id",
            "platform_asset_id",
            "error_message",
        } <= columns(db_path, "material_sync_run_items")

        command.downgrade(config, PARENT)
        assert "material_sync_run_items" not in tables(db_path)
        assert "storage_object_key" not in columns(db_path, "materials")
    finally:
        db_path.unlink(missing_ok=True)

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config


BACKEND_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
REVISION = "260728_03_material_workspace_states"
PARENT = "260713_02_ad_set_evidence"


def config_for(db_path: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def columns(db_path: Path, table: str) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def indexes(db_path: Path, table: str) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        return {row[1] for row in connection.execute(f"PRAGMA index_list({table})")}


def test_material_workspace_states_migration_roundtrip() -> None:
    db_path = PROJECT_ROOT / "drafts" / "260728" / "260728_03_material_workspace_states_migration.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    try:
        with sqlite3.connect(db_path) as connection:
            connection.executescript(
                "CREATE TABLE users (id VARCHAR(36) PRIMARY KEY);"
                "CREATE TABLE platform_connections (id VARCHAR(36) PRIMARY KEY);"
                "CREATE TABLE materials (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL);"
            )
        config = config_for(db_path)
        command.stamp(config, PARENT)
        command.upgrade(config, REVISION)

        assert {"original_filename", "lifecycle_status", "processing_status", "archived_at", "updated_at"} <= columns(db_path, "materials")
        assert {"created_via", "normalized_status", "last_verified_at", "last_error"} <= columns(db_path, "material_platform_assets")
        assert {"direction", "platform", "processing_count"} <= columns(db_path, "material_sync_runs")
        assert {"status", "error_code", "started_at", "updated_at"} <= columns(db_path, "material_sync_run_items")

        command.downgrade(config, PARENT)
        assert "lifecycle_status" not in columns(db_path, "materials")
        assert "normalized_status" not in columns(db_path, "material_platform_assets")
    finally:
        db_path.unlink(missing_ok=True)


def test_detached_platform_assets_migration_is_current_head() -> None:
    db_path = PROJECT_ROOT / "drafts" / "260728" / "260728_04_material_asset_identity.db"
    db_path.unlink(missing_ok=True)
    try:
        with sqlite3.connect(db_path) as connection:
            connection.executescript(
                "CREATE TABLE users (id VARCHAR(36) PRIMARY KEY);"
                "CREATE TABLE platform_connections (id VARCHAR(36) PRIMARY KEY);"
                "CREATE TABLE materials (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36) NOT NULL);"
            )
        config = config_for(db_path)
        command.stamp(config, PARENT)
        command.upgrade(config, "head")

        assert {
            "uq_material_platform_asset_target",
            "uq_material_platform_asset_remote_identity",
        } <= indexes(db_path, "material_platform_assets")
        with sqlite3.connect(db_path) as connection:
            asset_columns = list(connection.execute("PRAGMA table_info(material_platform_assets)"))
            asset_connection = next(row for row in asset_columns if row[1] == "connection_id")
            asset_material = next(row for row in asset_columns if row[1] == "material_id")
            run_connection = next(row for row in connection.execute("PRAGMA table_info(material_sync_runs)") if row[1] == "connection_id")
            material_fk = next(
                row for row in connection.execute("PRAGMA foreign_key_list(material_platform_assets)")
                if row[3] == "material_id"
            )
        assert asset_connection[3] == 0
        assert asset_material[3] == 0
        assert run_connection[3] == 0
        assert material_fk[6] == "SET NULL"
    finally:
        db_path.unlink(missing_ok=True)

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config


BACKEND_ROOT = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
REVISION = "260713_01_session_task_state"
PARENT = "260711_01_campaign_connection"


def config_for(db_path: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def columns(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        return {row[1] for row in connection.execute("PRAGMA table_info(session_states)")}


def test_session_task_state_migration_round_trip():
    db_path = PROJECT_ROOT / "drafts" / "260713" / "260713_03_session_task_state_migration.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    try:
        with sqlite3.connect(db_path) as connection:
            connection.execute(
                "CREATE TABLE session_states ("
                "session_id VARCHAR(128) PRIMARY KEY, user_id VARCHAR(128) NOT NULL, "
                "mode VARCHAR(32) NOT NULL, linked_entities_json TEXT NOT NULL, "
                "summary TEXT NOT NULL, pending_actions_json TEXT NOT NULL, "
                "changelog_json TEXT NOT NULL, ui_snapshot_json TEXT, version INTEGER NOT NULL, "
                "status VARCHAR(32) NOT NULL, last_error_json TEXT, "
                "created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"
            )
        config = config_for(db_path)
        command.stamp(config, PARENT)
        assert "task_state_json" not in columns(db_path)
        command.upgrade(config, REVISION)
        assert "task_state_json" in columns(db_path)
        command.downgrade(config, PARENT)
        assert "task_state_json" not in columns(db_path)
    finally:
        db_path.unlink(missing_ok=True)

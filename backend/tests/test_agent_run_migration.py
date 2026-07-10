from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

backend_root = Path(__file__).parent.parent
project_root = backend_root.parent
sys.path.insert(0, str(backend_root))

PARENT_REVISION = "260629_01_idempotency_records"
CHECKPOINT_REVISION = "260710_01_run_checkpoint"
RUN_EVENTS_REVISION = "260710_02_run_events"
APPROVALS_REVISION = "260710_03_approvals"
FACTS_REVISION = "260710_04_agent_facts"
HEAD_REVISION = "260710_05_execution_fencing"


def _config(db_path: Path) -> Config:
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def _columns(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as connection:
        return {row[1] for row in connection.execute("PRAGMA table_info(agent_runs)").fetchall()}


def _prepare_parent_schema(db_path: Path, *, checkpoint_ref_exists: bool) -> Config:
    with sqlite3.connect(db_path) as connection:
        checkpoint_column = ", checkpoint_ref VARCHAR(128)" if checkpoint_ref_exists else ""
        connection.execute(
            "CREATE TABLE agent_runs ("
            "run_id VARCHAR(128) PRIMARY KEY, session_id VARCHAR(128) NOT NULL, "
            "user_id VARCHAR(128) NOT NULL, status VARCHAR(32) NOT NULL, "
            f"input_text TEXT NOT NULL{checkpoint_column})"
        )
    config = _config(db_path)
    command.stamp(config, PARENT_REVISION)
    return config


def test_checkpoint_ref_migration_upgrades_and_downgrades() -> None:
    db_path = project_root / "drafts" / "260710" / "260710_06_backend_migration_test.db"
    db_path.unlink(missing_ok=True)
    try:
        config = _prepare_parent_schema(db_path, checkpoint_ref_exists=False)
        command.upgrade(config, CHECKPOINT_REVISION)
        assert "checkpoint_ref" in _columns(db_path)
        command.downgrade(config, PARENT_REVISION)
        assert "checkpoint_ref" not in _columns(db_path)
    finally:
        db_path.unlink(missing_ok=True)


def test_checkpoint_ref_migration_accepts_legacy_dynamic_column() -> None:
    db_path = project_root / "drafts" / "260710" / "260710_07_backend_legacy_migration_test.db"
    db_path.unlink(missing_ok=True)
    try:
        config = _prepare_parent_schema(db_path, checkpoint_ref_exists=True)
        command.upgrade(config, CHECKPOINT_REVISION)
        assert "checkpoint_ref" in _columns(db_path)
    finally:
        db_path.unlink(missing_ok=True)


def test_approvals_migration_upgrades_and_downgrades() -> None:
    db_path = project_root / "drafts" / "260710" / "260710_09_approvals_migration_test.db"
    db_path.unlink(missing_ok=True)
    try:
        config = _prepare_parent_schema(db_path, checkpoint_ref_exists=False)
        command.upgrade(config, APPROVALS_REVISION)
        with sqlite3.connect(db_path) as connection:
            table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_approvals'"
            ).fetchone()
            indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list(agent_approvals)").fetchall()
            }
        assert table == ("agent_approvals",)
        assert "idx_agent_approvals_user_status_expiry" in indexes
        assert "idx_agent_approvals_run_status" in indexes

        command.downgrade(config, RUN_EVENTS_REVISION)
        with sqlite3.connect(db_path) as connection:
            table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_approvals'"
            ).fetchone()
        assert table is None
    finally:
        db_path.unlink(missing_ok=True)


def test_agent_facts_migration_upgrades_and_downgrades() -> None:
    db_path = project_root / "drafts" / "260710" / "260710_10_agent_facts_migration_test.db"
    db_path.unlink(missing_ok=True)
    try:
        config = _prepare_parent_schema(db_path, checkpoint_ref_exists=False)
        command.upgrade(config, APPROVALS_REVISION)
        with sqlite3.connect(db_path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS agent_sessions ("
                "session_id VARCHAR(128) PRIMARY KEY, user_id VARCHAR(128) NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS agent_messages ("
                "message_id VARCHAR(128) PRIMARY KEY, session_id VARCHAR(128) NOT NULL, "
                "user_id VARCHAR(128) NOT NULL, role VARCHAR(32) NOT NULL, content_json TEXT NOT NULL, "
                "run_id VARCHAR(128), sequence INTEGER NOT NULL, created_at DATETIME NOT NULL)"
            )
        command.upgrade(config, FACTS_REVISION)
        with sqlite3.connect(db_path) as connection:
            run_columns = {row[1] for row in connection.execute("PRAGMA table_info(agent_runs)")}
            message_columns = {row[1] for row in connection.execute("PRAGMA table_info(agent_messages)")}
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert {"version", "lease_owner", "lease_expires_at", "heartbeat_at"}.issubset(run_columns)
        assert {"status", "error_code", "completed_at"}.issubset(message_columns)
        assert {"agent_tool_calls", "agent_artifacts"}.issubset(tables)

        command.downgrade(config, APPROVALS_REVISION)
        with sqlite3.connect(db_path) as connection:
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
        assert "agent_tool_calls" not in tables
        assert "agent_artifacts" not in tables
    finally:
        db_path.unlink(missing_ok=True)


def test_execution_fencing_migration_upgrades_and_downgrades() -> None:
    db_path = project_root / "drafts" / "260710" / "260710_13_execution_fencing_migration_test.db"
    db_path.unlink(missing_ok=True)
    try:
        config = _prepare_parent_schema(db_path, checkpoint_ref_exists=False)
        command.upgrade(config, APPROVALS_REVISION)
        with sqlite3.connect(db_path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS agent_sessions ("
                "session_id VARCHAR(128) PRIMARY KEY, user_id VARCHAR(128) NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS agent_messages ("
                "message_id VARCHAR(128) PRIMARY KEY, session_id VARCHAR(128) NOT NULL, "
                "user_id VARCHAR(128) NOT NULL, role VARCHAR(32) NOT NULL, content_json TEXT NOT NULL, "
                "run_id VARCHAR(128), sequence INTEGER NOT NULL, created_at DATETIME NOT NULL)"
            )
        command.upgrade(config, HEAD_REVISION)
        with sqlite3.connect(db_path) as connection:
            run_columns = {row[1] for row in connection.execute("PRAGMA table_info(agent_runs)")}
            approval_columns = {row[1] for row in connection.execute("PRAGMA table_info(agent_approvals)")}
            lease_table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_session_leases'"
            ).fetchone()
        assert {"execution_kind", "resume_payload_json", "error_code"}.issubset(run_columns)
        assert {"preconditions_json", "claimed_by", "resolved_by"}.issubset(approval_columns)
        assert lease_table == ("agent_session_leases",)

        command.downgrade(config, FACTS_REVISION)
        with sqlite3.connect(db_path) as connection:
            lease_table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_session_leases'"
            ).fetchone()
        assert lease_table is None
    finally:
        db_path.unlink(missing_ok=True)


def test_run_events_migration_upgrades_and_downgrades() -> None:
    db_path = project_root / "drafts" / "260710" / "260710_08_run_events_migration_test.db"
    db_path.unlink(missing_ok=True)
    try:
        config = _prepare_parent_schema(db_path, checkpoint_ref_exists=False)
        command.upgrade(config, RUN_EVENTS_REVISION)
        columns = _columns(db_path)
        assert {"checkpoint_ref", "last_event_sequence", "terminal_event_id"}.issubset(columns)
        with sqlite3.connect(db_path) as connection:
            table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_run_events'"
            ).fetchone()
        assert table == ("agent_run_events",)

        command.downgrade(config, CHECKPOINT_REVISION)
        columns = _columns(db_path)
        assert "last_event_sequence" not in columns
        assert "terminal_event_id" not in columns
        with sqlite3.connect(db_path) as connection:
            table = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_run_events'"
            ).fetchone()
        assert table is None
    finally:
        db_path.unlink(missing_ok=True)

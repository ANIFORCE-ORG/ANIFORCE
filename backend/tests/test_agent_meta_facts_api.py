from datetime import date

import pytest
from pydantic import ValidationError

from app.api.v1.meta_facts import (
    MetaFactsSyncRequest,
    normalize_requested_accounts,
    validate_sync_window,
    classify_meta_sync_error,
)


def test_sync_request_supports_all_active_accounts_with_a_hard_safety_limit():
    MetaFactsSyncRequest(
        connection_id="c1",
        account_ids=[str(index) for index in range(200)],
        since=date(2026, 8, 1),
        until=date(2026, 8, 30),
    )
    with pytest.raises(ValidationError):
        MetaFactsSyncRequest(
            connection_id="c1",
            account_ids=[str(index) for index in range(201)],
            since=date(2026, 8, 1),
            until=date(2026, 8, 30),
        )


def test_sync_window_is_bounded_and_ordered():
    validate_sync_window(date(2026, 8, 1), date(2026, 8, 31))
    with pytest.raises(ValueError, match="31 days"):
        validate_sync_window(date(2026, 8, 1), date(2026, 9, 1))
    with pytest.raises(ValueError, match="since"):
        validate_sync_window(date(2026, 8, 2), date(2026, 8, 1))


def test_requested_accounts_are_normalized_and_deduplicated():
    assert normalize_requested_accounts(["act_123", "123", "act_456"]) == ["123", "456"]


def test_meta_sync_error_classification_preserves_actionable_categories():
    assert classify_meta_sync_error(TimeoutError())[0] == "META_INSIGHTS_TIMEOUT"
    assert classify_meta_sync_error(Exception("sqlite3.OperationalError: database is locked"))[0] == "META_INSIGHTS_DATABASE_LOCKED"
    assert classify_meta_sync_error(Exception("unexpected Meta response"))[0] == "META_INSIGHTS_API_ERROR"


def test_sync_request_is_adset_only():
    request = MetaFactsSyncRequest(
        connection_id="c1",
        account_ids=["123"],
        since=date(2026, 8, 1),
        until=date(2026, 8, 7),
    )
    assert request.level == "adset"
    with pytest.raises(ValidationError):
        MetaFactsSyncRequest(
            connection_id="c1",
            account_ids=["123"],
            since=date(2026, 8, 1),
            until=date(2026, 8, 7),
            level="ad",
        )

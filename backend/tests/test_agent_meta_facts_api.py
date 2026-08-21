from datetime import date

import pytest
from pydantic import ValidationError

from app.api.v1.meta_facts import (
    MetaFactsSyncRequest,
    normalize_requested_accounts,
    validate_sync_window,
)


def test_sync_request_limits_account_count_without_network_access():
    MetaFactsSyncRequest(
        connection_id="c1",
        account_ids=["1", "2", "3", "4", "5"],
        since=date(2026, 8, 1),
        until=date(2026, 8, 2),
    )
    with pytest.raises(ValidationError):
        MetaFactsSyncRequest(
            connection_id="c1",
            account_ids=["1", "2", "3", "4", "5", "6"],
            since=date(2026, 8, 1),
            until=date(2026, 8, 2),
        )


def test_sync_window_is_bounded_and_ordered():
    validate_sync_window(date(2026, 8, 1), date(2026, 8, 31))
    with pytest.raises(ValueError, match="31 days"):
        validate_sync_window(date(2026, 8, 1), date(2026, 9, 1))
    with pytest.raises(ValueError, match="since"):
        validate_sync_window(date(2026, 8, 2), date(2026, 8, 1))


def test_requested_accounts_are_normalized_and_deduplicated():
    assert normalize_requested_accounts(["act_123", "123", "act_456"]) == ["123", "456"]


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

import asyncio

import pytest

from app.services.meta_insights_collector import MetaInsightsCollector


class FakeAdapter:
    def __init__(self):
        self.calls = []

    async def get_account_daily_insights(self, account_id, date_range, level, *, max_pages):
        self.calls.append((account_id, date_range, level, max_pages))
        id_fields = {
            "campaign": {"campaign_id": "c1", "campaign_name": "Campaign"},
            "adset": {"campaign_id": "c1", "adset_id": "s1", "adset_name": "Ad Set"},
            "ad": {"adset_id": "s1", "ad_id": "a1", "ad_name": "Ad"},
        }
        return [{"account_id": account_id, "date_start": "2026-08-10", **id_fields[level]}]


class FakeRepository:
    def __init__(self):
        self.rows = []

    async def upsert_many(self, rows):
        self.rows.extend(rows)
        return len(rows)


def test_collector_is_whitelist_bound_and_collects_three_levels_serially():
    adapter = FakeAdapter()
    repository = FakeRepository()
    collector = MetaInsightsCollector(adapter, repository, ["act_123"])

    result = asyncio.run(collector.collect_account(
        connection_id="connection-1",
        account_id="123",
        since="2026-08-10",
        until="2026-08-16",
        max_pages=3,
    ))

    assert result == {"campaign": 1, "adset": 1, "ad": 1}
    assert [call[2] for call in adapter.calls] == ["campaign", "adset", "ad"]
    assert all(call[3] == 3 for call in adapter.calls)
    assert [row["level"] for row in repository.rows] == ["campaign", "adset", "ad"]


def test_collector_rejects_accounts_outside_whitelist_before_network_call():
    adapter = FakeAdapter()
    collector = MetaInsightsCollector(adapter, FakeRepository(), ["123"])

    with pytest.raises(PermissionError):
        asyncio.run(collector.collect_account(
            connection_id="connection-1",
            account_id="999",
            since="2026-08-10",
            until="2026-08-16",
        ))
    assert adapter.calls == []
